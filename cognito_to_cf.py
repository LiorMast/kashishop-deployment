import json
import yaml
import re
import argparse
from collections import OrderedDict

def sanitize_name(name):
    """
    Cleans up a string to be a valid CloudFormation Logical ID.
    Splits by non-alphanumeric characters and joins as CamelCase.
    """
    if not name:
        return "UnnamedResource"
    parts = re.split(r'[^0-9a-zA-Z]+', name)
    return ''.join(p.capitalize() for p in parts if p)


def ordered_to_plain(obj):
    """
    Recursively converts OrderedDicts within a nested structure to plain dicts.
    This is useful for clean YAML output.
    """
    if isinstance(obj, OrderedDict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ordered_to_plain(v) for v in obj]
    return obj


def flatten(nested):
    """
    Flattens one level of nesting for lists.
    Useful for Cognito API responses that sometimes return a list of lists.
    """
    out = []
    for item in nested or []:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out


def convert_cognito_to_cfn(cognito_json):
    """
    Main conversion function. Takes the JSON export from get-cognito.sh
    and transforms it into a CloudFormation template structure.
    """
    template = OrderedDict(
        AWSTemplateFormatVersion='2010-09-09',
        Description='CloudFormation template for AWS Cognito environment',
        Parameters=OrderedDict({
            'EnvPrefix': {
                'Type': 'String',
                'Description': 'Prefix for naming resources (e.g., dev, test, prod)',
                'MinLength': 1
            }
        })
    )
    resources = OrderedDict()

    # --- User Pools and related resources ---
    for pool in cognito_json.get('userPools', []):
        details = pool.get('details', {}) or {}
        pool_name = details.get('Name') or pool.get('poolName')
        pool_logical = sanitize_name(pool_name) + 'UserPool'

        # 1) User Pool
        up_props = OrderedDict({
            'UserPoolName': {'Fn::Sub': '${EnvPrefix}-' + pool_name}
        })
        # Password policy
        pp = details.get('Policies', {}).get('PasswordPolicy')
        if pp:
            pp.pop('UnusedAccountValidityDays', None)
            up_props['Policies'] = {'PasswordPolicy': pp}
        # Misc configs
        for key in ('LambdaConfig', 'AutoVerifiedAttributes', 'AliasAttributes',
                    'MfaConfiguration', 'VerificationMessageTemplate', 'UsernameConfiguration'):
            val = details.get(key)
            if val is not None:
                up_props[key] = val
        # Schema attributes
        schema = details.get('SchemaAttributes')
        if isinstance(schema, list):
            filtered = [a for a in schema if len(a.get('Name', '')) <= 20]
            if filtered:
                up_props['Schema'] = filtered
        # Admin create config
        acu = details.get('AdminCreateUserConfig')
        if acu:
            acu2 = OrderedDict(acu)
            acu2.pop('UnusedAccountValidityDays', None)
            up_props['AdminCreateUserConfig'] = acu2

        resources[pool_logical] = {
            'Type': 'AWS::Cognito::UserPool',
            'Properties': up_props
        }

        # --- Create a map of physical Client IDs to their logical CloudFormation IDs ---
        client_id_map = {}

        # 2) App Clients
        for client in flatten(pool.get('clients')):
            if not isinstance(client, dict):
                continue
            c_det = client.get('details', {}) or {}
            
            physical_client_id = c_det.get('ClientId')
            if not physical_client_id:
                continue

            name = c_det.get('ClientName') or physical_client_id
            clog = sanitize_name(name) + 'UserPoolClient'
            
            # Store the mapping from the original physical ID to the new logical ID
            client_id_map[physical_client_id] = clog

            cp = OrderedDict(c_det)
            # Drop attributes not allowed or managed by CloudFormation
            for drop in ('LastModifiedDate', 'CreationDate', 'UserPoolId', 'ClientId', 'ClientSecret'):
                cp.pop(drop, None)
            cp['UserPoolId'] = {'Ref': pool_logical}
            
            # --- FIX: Ensure the UserPoolClient is enabled for OAuth flows ---
            # If the source client has AllowedOAuthFlowsUserPoolClient set to true,
            # this must be carried over to the template for the hosted UI to be available.
            if c_det.get('AllowedOAuthFlowsUserPoolClient'):
                cp['AllowedOAuthFlowsUserPoolClient'] = True
                
            resources[clog] = {
                'Type': 'AWS::Cognito::UserPoolClient',
                'Properties': cp
            }

        # 3) Groups
        for group in flatten(pool.get('groups')):
            if not isinstance(group, dict):
                continue
            g_det = group.get('details', {}) or {}
            gl = sanitize_name(g_det.get('GroupName', '')) + 'UserPoolGroup'
            gp = OrderedDict(g_det)
            # Remove extraneous keys
            for drop in ('RoleArn', 'LastModifiedDate', 'CreationDate'):
                gp.pop(drop, None)
            gp['UserPoolId'] = {'Ref': pool_logical}
            resources[gl] = {
                'Type': 'AWS::Cognito::UserPoolGroup',
                'Properties': gp
            }

        # 4) Identity Providers
        for idp in flatten(pool.get('identityProviders')):
            if not isinstance(idp, dict):
                continue
            pname = idp.get('ProviderName', '')
            il = sanitize_name(pname) + 'IdP'
            ip = OrderedDict(idp)
            # ProviderDetails must be handled carefully, as they often contain secrets.
            # Here we just copy it, but in a real scenario, this should be parameterized.
            ip.pop('LastModifiedDate', None)
            ip.pop('CreationDate', None)
            ip['UserPoolId'] = {'Ref': pool_logical}
            resources[il] = {
                'Type': 'AWS::Cognito::UserPoolIdentityProvider',
                'Properties': ip
            }

        # 5) Managed Login Branding
        for b in flatten(pool.get('managedLoginBranding')):
            if not isinstance(b, dict):
                continue
            
            physical_client_id = b.get('clientId')
            if not physical_client_id or physical_client_id not in client_id_map:
                print(f"Warning: Skipping branding for unknown client ID: {physical_client_id}")
                continue

            # Use the map to get the client's logical CloudFormation ID
            client_logical_id = client_id_map[physical_client_id]

            # Generate a more stable logical ID for the branding resource
            branding_logical_id = client_logical_id.replace('UserPoolClient', '') + 'ManagedLoginBranding'

            bp = OrderedDict(b.get('managedLoginBranding', {}))
            bp['UserPoolId'] = {'Ref': pool_logical}
            
            # --- FIX: Use a CloudFormation 'Ref' to the UserPoolClient ---
            bp['ClientId'] = {'Ref': client_logical_id}

            # Clean up read-only properties from the branding payload
            for drop in ('ManagedLoginBrandingId', 'LastModifiedDate', 'CreationDate'):
                bp.pop(drop, None)
            
            # --- FIX: Filter out IDP_BUTTON_ICON assets ---
            # Cognito automatically adds buttons for configured IDPs on the App Client.
            # Explicitly providing them in the template can cause "Resource Id not found"
            # errors if the IDP doesn't exist yet in the target stack.
            if 'Assets' in bp and isinstance(bp['Assets'], list):
                filtered_assets = [
                    asset for asset in bp['Assets']
                    if asset.get('Category') != 'IDP_BUTTON_ICON'
                ]
                bp['Assets'] = filtered_assets

            resources[branding_logical_id] = {
                'Type': 'AWS::Cognito::ManagedLoginBranding',
                'Properties': bp
            }

        # 6) Resource Servers
        for rs in flatten(pool.get('resourceServers')):
            if not isinstance(rs, dict):
                continue
            name = rs.get('Name')
            rl = sanitize_name(name) + 'ResourceServer'
            rp = OrderedDict(rs)
            rp.pop('UserPoolId', None) # Will be set with Ref
            rp['UserPoolId'] = {'Ref': pool_logical}
            resources[rl] = {
                'Type': 'AWS::Cognito::UserPoolResourceServer',
                'Properties': rp
            }

        # 7) User Pool Domain
        domain = pool.get('hostedUIDomain', {})
        if domain and domain.get('Domain'):
            dl = sanitize_name(domain.get('Domain')) + 'UserPoolDomain'
            dp = OrderedDict()
            dp['UserPoolId'] = {'Ref': pool_logical}

            # --- FIX: Make the domain name unique by prepending the EnvPrefix ---
            # Cognito domain prefixes must be globally unique within a region.
            # Hardcoding the domain from the source environment will cause a
            # collision when trying to deploy to the same region.
            dp['Domain'] = {'Fn::Sub': '${EnvPrefix}-' + domain.get('Domain')}
            
            resources[dl] = {
                'Type': 'AWS::Cognito::UserPoolDomain',
                'Properties': dp
            }

        # 8) UI Customization (classic UI)
        ui_cust = pool.get('uiCustomization', {})
        if ui_cust and (ui_cust.get('CSS') or ui_cust.get('ImageUrl')):
            uil = sanitize_name(pool_name) + 'UICustomization'
            uip = OrderedDict(ui_cust)
            uip.pop('LastModifiedDate', None)
            uip.pop('CreationDate', None)
            uip.pop('ClientId', None) # Not applicable for general UI customization
            uip['UserPoolId'] = {'Ref': pool_logical}
            resources[uil] = {
                'Type': 'AWS::Cognito::UserPoolUICustomizationAttachment',
                'Properties': uip
            }
            
    # --- Identity Pools + related resources ---
    for id_pool in cognito_json.get('identityPools', []):
        details = id_pool.get('details', {}) or {}
        pool_name = details.get('IdentityPoolName') or id_pool.get('identityPoolName')
        pool_logical = sanitize_name(pool_name) + 'IdentityPool'
        
        # 1) Identity Pool
        ipp = OrderedDict(details)
        for drop in ('IdentityPoolId',):
            ipp.pop(drop, None)
        resources[pool_logical] = {
            'Type': 'AWS::Cognito::IdentityPool',
            'Properties': ipp
        }

        # 2) Role Attachment
        roles = id_pool.get('roles', {})
        if roles and roles.get('Roles'):
            att_logical = pool_logical + 'RoleAttachment'
            att = OrderedDict()
            att['IdentityPoolId'] = {'Ref': pool_logical}
            att['Roles'] = roles.get('Roles')
            if 'RoleMappings' in roles and roles['RoleMappings']:
                att['RoleMappings'] = roles['RoleMappings']
            resources[att_logical] = {
                'Type': 'AWS::Cognito::IdentityPoolRoleAttachment',
                'Properties': att
            }

    template['Resources'] = resources

    # Outputs
    outs = OrderedDict()
    for key in resources:
        outs[key + 'Id'] = {'Description': f"ID of {key}", 'Value': {'Ref': key}}
    template['Outputs'] = outs

    return template


def main():
    """
    Parses command-line arguments, runs the conversion, and writes the output file.
    """
    parser = argparse.ArgumentParser(description='Convert Cognito JSON to CloudFormation YAML')
    parser.add_argument('--input', required=True, help='Input JSON file exported from get-cognito.sh')
    parser.add_argument('--output', required=True, help='Destination CloudFormation YAML file')
    args = parser.parse_args()

    with open(args.input) as f:
        cognito_data = json.load(f)
    
    template = convert_cognito_to_cfn(cognito_data)
    plain_template = ordered_to_plain(template)

    # Use a custom representer to handle multiline strings for description
    def str_presenter(dumper, data):
        if len(data.splitlines()) > 1:  # check for multiline
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    yaml.add_representer(str, str_presenter)
    
    yaml_str = yaml.dump(plain_template, sort_keys=False, width=120)
    
    # Add comments for better readability
    lines = yaml_str.splitlines()
    out_lines = []
    for line in lines:
        if line.startswith('AWSTemplateFormatVersion'):
            out_lines.append('# ----- Template Header -----')
        elif line.startswith('Description:'):
            out_lines.append('') # extra space
        elif line.startswith('Parameters:'):
            out_lines.append('\n# ----- Parameters -----')
        elif line.startswith('Resources:'):
            out_lines.append('\n# ----- Resources -----')
        elif line.startswith('Outputs:'):
            out_lines.append('\n# ----- Outputs -----')
        out_lines.append(line)

    with open(args.output, 'w') as f:
        f.write('\n'.join(out_lines))
    
    print(f"CloudFormation template successfully written to {args.output}")

if __name__ == '__main__':
    main()
