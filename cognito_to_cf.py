import json
import yaml
import re
import argparse
from collections import OrderedDict

# Helper to sanitize names for CloudFormation logical IDs
# Removes non-alphanumeric characters and capitalizes each part
def sanitize_name(name):
    parts = re.split(r'[^0-9a-zA-Z]+', name)
    return ''.join([part.capitalize() for part in parts if part])

# Recursively convert OrderedDict to plain dicts for YAML serialization
def ordered_to_plain(obj):
    if isinstance(obj, OrderedDict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ordered_to_plain(v) for v in obj]
    return obj

# Main conversion function for Cognito JSON
def convert_cognito_to_cfn(cognito_json):
    template = OrderedDict()
    # Template header
    template['AWSTemplateFormatVersion'] = '2010-09-09'
    template['Description'] = 'CloudFormation template for AWS Cognito environment'

    # Parameters
    template['Parameters'] = OrderedDict({
        'EnvPrefix': {
            'Type': 'String',
            'Description': 'Prefix for naming resources (e.g., dev, test, prod)',
            'MinLength': 1
        }
    })

    resources = OrderedDict()

    # User Pools
    for pool in cognito_json.get('userPools', []):
        details = pool.get('details', {})
        pool_name = details.get('Name') or pool.get('poolName')
        logical_id = sanitize_name(pool_name) + 'UserPool'

        # Build UserPool properties
        props = OrderedDict({'UserPoolName': {'Fn::Sub': '${EnvPrefix}-' + pool_name}})
        # Policies (PasswordPolicy)
        pwd = details.get('Policies', {}).get('PasswordPolicy')
        if pwd:
            # Ensure only TemporaryPasswordValidityDays is used
            pwd.pop('UnusedAccountValidityDays', None)
            props['Policies'] = {'PasswordPolicy': pwd}
        # Lambda triggers
        lambda_cfg = details.get('LambdaConfig')
        if lambda_cfg:
            props['LambdaConfig'] = lambda_cfg
        # Schema attributes (filter out names >20 chars)
        schema = details.get('SchemaAttributes')
        if schema:
            filtered = []
            for attr in schema:
                name = attr.get('Name', '')
                if len(name) <= 20:
                    filtered.append(attr)
                else:
                    print(f"Warning: Skipping schema attribute '{name}' (length {len(name)})")
            if filtered:
                props['Schema'] = filtered
        # Auto-verified attributes
        auto = details.get('AutoVerifiedAttributes')
        if auto:
            props['AutoVerifiedAttributes'] = auto
        # Alias attributes
        alias = details.get('AliasAttributes')
        if alias:
            props['AliasAttributes'] = alias
        # MFA configuration
        mfa = details.get('MfaConfiguration')
        if mfa:
            props['MfaConfiguration'] = mfa
        # Verification message template
        vmt = details.get('VerificationMessageTemplate')
        if vmt:
            props['VerificationMessageTemplate'] = vmt
        # AdminCreateUserConfig: drop UnusedAccountValidityDays
        acu = details.get('AdminCreateUserConfig')
        if acu:
            acu_filtered = OrderedDict(acu)
            acu_filtered.pop('UnusedAccountValidityDays', None)
            props['AdminCreateUserConfig'] = acu_filtered
        # UsernameConfiguration
        uc = details.get('UsernameConfiguration')
        if uc:
            props['UsernameConfiguration'] = uc

        resources[logical_id] = {'Type': 'AWS::Cognito::UserPool', 'Properties': props}

        # User Pool Clients
        for client in pool.get('clients', []):
            cdet = client.get('details', {})
            client_name = cdet.get('ClientName') or client.get('clientId')
            clogical = sanitize_name(client_name) + 'UserPoolClient'
            client_props = OrderedDict(cdet)
            for f in ['LastModifiedDate', 'CreationDate', 'UserPoolId', 'ClientId', 'ClientSecret']:
                client_props.pop(f, None)
            client_props['UserPoolId'] = {'Ref': logical_id}
            resources[clogical] = {'Type': 'AWS::Cognito::UserPoolClient', 'Properties': client_props}

        # Groups
        for group in pool.get('groups', []):
            gdet = group.get('details', {})
            group_name = gdet.get('GroupName')
            glogical = sanitize_name(group_name) + 'UserPoolGroup'
            group_props = OrderedDict(gdet)
            for f in ['CreationDate', 'LastModifiedDate', 'RoleArn']:
                group_props.pop(f, None)
            group_props['UserPoolId'] = {'Ref': logical_id}
            resources[glogical] = {'Type': 'AWS::Cognito::UserPoolGroup', 'Properties': group_props}

        # Identity Providers
        for idp in pool.get('identityProviders', []):
            pname = idp.get('ProviderName')
            idp_logical = sanitize_name(pname) + 'IdP'
            idp_props = OrderedDict(idp)
            idp_props.pop('ProviderDetails', None)
            idp_props['UserPoolId'] = {'Ref': logical_id}
            resources[idp_logical] = {'Type': 'AWS::Cognito::UserPoolIdentityProvider', 'Properties': idp_props}

        # Resource Servers
        for server in pool.get('resourceServers', []):
            sid = server.get('Identifier')
            slogical = sanitize_name(sid) + 'ResourceServer'
            srv_props = OrderedDict({'Identifier': sid, 'Name': server.get('Name'), 'Scopes': server.get('Scopes', []), 'UserPoolId': {'Ref': logical_id}})
            resources[slogical] = {'Type': 'AWS::Cognito::UserPoolResourceServer', 'Properties': srv_props}

    # Identity Pools
    for ip in cognito_json.get('identityPools', []):
        idet = ip.get('details', {})
        ip_name = idet.get('IdentityPoolName')
        ip_logical = sanitize_name(ip_name) + 'IdentityPool'
        ip_props = OrderedDict({'IdentityPoolName': {'Fn::Sub': '${EnvPrefix}-' + ip_name}, 'AllowUnauthenticatedIdentities': idet.get('AllowUnauthenticatedIdentities', False)})
        logins = idet.get('SupportedLoginProviders')
        if logins:
            ip_props['SupportedLoginProviders'] = logins
        resources[ip_logical] = {'Type': 'AWS::Cognito::IdentityPool', 'Properties': ip_props}

        # Attach default role via IdentityPoolRoleAttachment
        att_logical = ip_logical + 'RoleAttachment'
        att_props = OrderedDict({'IdentityPoolId': {'Ref': ip_logical}, 'Roles': {'authenticated': {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}, 'unauthenticated': {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}}})
        resources[att_logical] = {'Type': 'AWS::Cognito::IdentityPoolRoleAttachment', 'Properties': att_props}

    template['Resources'] = resources

    # Outputs
    outputs = OrderedDict()
    for key in resources:
        outputs[key + 'Id'] = {'Description': f"ID of {key}", 'Value': {'Ref': key}}
    template['Outputs'] = outputs

    return template

# Script entry point
def main():
    parser = argparse.ArgumentParser(description='Convert Cognito JSON to CloudFormation template')
    parser.add_argument('--input', required=True, help='Input JSON file from get-cognito.sh')
    parser.add_argument('--output', required=True, help='Output CloudFormation YAML file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        cognito_json = json.load(f)

    template = convert_cognito_to_cfn(cognito_json)
    plain = ordered_to_plain(template)

    # Dump to YAML and insert comments
    yaml_str = yaml.safe_dump(plain, sort_keys=False)
    lines = yaml_str.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith('AWSTemplateFormatVersion'):
            new_lines.append('# ---------------------- Template Header ----------------------')
            new_lines.append(line)
        elif line.startswith('Description'):
            new_lines.append(line)
        elif line.startswith('Parameters:'):
            new_lines.append('\n# ---------------------- Parameters ----------------------')
            new_lines.append(line)
        elif line.startswith('Resources:'):
            new_lines.append('\n# ---------------------- Resources ----------------------')
            new_lines.append(line)
        elif line.startswith('Outputs:'):
            new_lines.append('\n# ---------------------- Outputs ----------------------')
            new_lines.append(line)
        else:
            new_lines.append(line)

    with open(args.output, 'w') as out_f:
        out_f.write('\n'.join(new_lines) + '\n')

    print(f"CloudFormation template written to {args.output}")

if __name__ == '__main__':
    main()
