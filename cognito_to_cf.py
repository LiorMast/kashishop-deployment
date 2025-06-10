import json
import yaml
import re
import argparse
from collections import OrderedDict

def sanitize_name(name):
    parts = re.split(r'[^0-9a-zA-Z]+', name)
    return ''.join(p.capitalize() for p in parts if p)


def ordered_to_plain(obj):
    if isinstance(obj, OrderedDict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ordered_to_plain(v) for v in obj]
    return obj


def unwrap(item):
    # Flatten export lists of single elements
    if isinstance(item, list):
        return item[0] if item else None
    return item


def convert_cognito_to_cfn(cognito_json):
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

    # --- User Pools + related resources ---
    for pool in cognito_json.get('userPools', []):
        details = pool.get('details', {})
        pool_name = details.get('Name') or pool.get('poolName')
        pool_logical = sanitize_name(pool_name) + 'UserPool'

        # 1) Cognito User Pool
        up_props = OrderedDict({
            'UserPoolName': {'Fn::Sub': '${EnvPrefix}-' + pool_name}
        })
        if pp := details.get('Policies', {}).get('PasswordPolicy'):
            pp.pop('UnusedAccountValidityDays', None)
            up_props['Policies'] = {'PasswordPolicy': pp}
        for key in ('LambdaConfig','AutoVerifiedAttributes','AliasAttributes',
                    'MfaConfiguration','VerificationMessageTemplate',
                    'UsernameConfiguration'):
            if val := details.get(key):
                up_props[key] = val
        if schema := details.get('SchemaAttributes'):
            filtered = [a for a in schema if len(a.get('Name',''))<=20]
            if filtered: up_props['Schema'] = filtered
        if acu := details.get('AdminCreateUserConfig'):
            acu2 = OrderedDict(acu); acu2.pop('UnusedAccountValidityDays',None)
            up_props['AdminCreateUserConfig'] = acu2

        resources[pool_logical] = {
            'Type': 'AWS::Cognito::UserPool',
            'Properties': up_props
        }

        # 2) App Clients
        for client_entry in pool.get('clients', []):
            client = unwrap(client_entry)
            if not client: continue
            c = client.get('details', {})
            name = c.get('ClientName') or client.get('clientId')
            clog = sanitize_name(name) + 'UserPoolClient'
            cp = OrderedDict(c)
            for drop in ('LastModifiedDate','CreationDate','UserPoolId','ClientId','ClientSecret'):
                cp.pop(drop, None)
            cp['UserPoolId'] = {'Ref': pool_logical}
            resources[clog] = {
                'Type': 'AWS::Cognito::UserPoolClient',
                'Properties': cp
            }

        # 3) Groups
        for group_entry in pool.get('groups', []):
            group = unwrap(group_entry)
            if not group: continue
            g = group.get('details', {})
            gl = sanitize_name(g['GroupName']) + 'UserPoolGroup'
            gp = OrderedDict(g)
            # Remove extraneous keys
            for drop in ('RoleArn', 'LastModifiedDate', 'CreationDate'):
                gp.pop(drop, None)
            gp['UserPoolId'] = {'Ref': pool_logical}
            resources[gl] = {
                'Type': 'AWS::Cognito::UserPoolGroup',
                'Properties': gp
            }

        # 4) Identity Providers
        for idp_entry in pool.get('identityProviders', []):
            idp0 = unwrap(idp_entry)
            if not idp0: continue
            pname = idp0['ProviderName']; il = sanitize_name(pname) + 'IdP'
            ip = OrderedDict(idp0); ip.pop('ProviderDetails', None)
            ip['UserPoolId'] = {'Ref': pool_logical}
            resources[il] = {
                'Type': 'AWS::Cognito::UserPoolIdentityProvider',
                'Properties': ip
            }

        # 5) Resource Servers
        for srv_entry in pool.get('resourceServers', []):
            srv0 = unwrap(srv_entry)
            if not srv0: continue
            sid = srv0['Identifier']; sl = sanitize_name(sid) + 'ResourceServer'
            sp = OrderedDict({
                'Identifier': sid,
                'Name': srv0.get('Name'),
                'Scopes': srv0.get('Scopes', []),
                'UserPoolId': {'Ref': pool_logical}
            })
            resources[sl] = {
                'Type': 'AWS::Cognito::UserPoolResourceServer',
                'Properties': sp
            }

        # 6) Managed Login Branding
        for ml_entry in pool.get('managedLoginBranding', []):
            entry = unwrap(ml_entry)
            if not entry: continue
            cid = entry.get('clientId')
            m = entry.get('managedLoginBranding', {})
            mlog = sanitize_name(pool_name + cid) + 'ManagedLoginBranding'
            ml_props = OrderedDict({
                'UserPoolId': {'Ref': pool_logical},
                'ClientId': cid,
                'UseCognitoProvidedValues': m.get('UseCognitoProvidedValues', False),
                'Settings': m.get('Settings', {}),
                'Assets': m.get('Assets', []),
                'ReturnMergedResources': False
            })
            resources[mlog] = {
                'Type': 'AWS::Cognito::ManagedLoginBranding',
                'Properties': ml_props
            }

    # --- Identity Pools & Attachments ---
    for ip in cognito_json.get('identityPools', []):
        d = ip['details']; name = d['IdentityPoolName']
        ilog = sanitize_name(name) + 'IdentityPool'
        iprops = OrderedDict({
            'IdentityPoolName': {'Fn::Sub': '${EnvPrefix}-' + name},
            'AllowUnauthenticatedIdentities': d.get('AllowUnauthenticatedIdentities', False)
        })
        if lp := d.get('SupportedLoginProviders'):
            iprops['SupportedLoginProviders'] = lp
        resources[ilog] = {'Type':'AWS::Cognito::IdentityPool','Properties': iprops}

        att = OrderedDict({
            'IdentityPoolId': {'Ref': ilog},
            'Roles': {
                'authenticated': {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'},
                'unauthenticated': {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}
            }
        })
        resources[ilog + 'RoleAttachment'] = {
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
    p = argparse.ArgumentParser(description='Convert Cognito JSON to CFN')
    p.add_argument('--input', required=True, help='export JSON from get-cognito.sh')
    p.add_argument('--output', required=True, help='destination CFN YAML file')
    args = p.parse_args()

    with open(args.input) as f:
        cj = json.load(f)
    tpl = convert_cognito_to_cfn(cj)
    plain = ordered_to_plain(tpl)

    # emit YAML with comments
    y = yaml.safe_dump(plain, sort_keys=False)
    lines, out = y.splitlines(), []
    for L in lines:
        if L.startswith('AWSTemplateFormatVersion'):
            out += ['# ----- Template Header -----', L]
        elif L.startswith('Parameters:'):
            out += ['# ----- Parameters -----', L]
        elif L.startswith('Resources:'):
            out += ['# ----- Resources -----', L]
        elif L.startswith('Outputs:'):
            out += ['# ----- Outputs -----', L]
        else:
            out.append(L)

    with open(args.output, 'w') as w:
        w.write(''.join(out) + '')
    print(f"⛅ CloudFormation template written to {args.output}")

if __name__ == '__main__':
    main()
