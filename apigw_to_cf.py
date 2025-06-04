import json
import yaml
import re
import argparse
from collections import OrderedDict
from datetime import datetime, timezone

# Helper to sanitize names for CloudFormation logical IDs
# Removes non-alphanumeric characters and capitalizes each part

def sanitize_name(name):
    parts = re.split(r'[^0-9a-zA-Z]+', name)
    return ''.join([part.capitalize() for part in parts if part])

# Recursively convert OrderedDict to regular dicts for YAML serialization

def ordered_to_plain(obj):
    if isinstance(obj, OrderedDict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ordered_to_plain(v) for v in obj]
    return obj

# Main conversion function

def convert_api_to_cfn(api_json):
    # Generate a timestamp for stage suffix
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')  # include microseconds for uniqueness

    template = OrderedDict()
    # Template header
    template['AWSTemplateFormatVersion'] = '2010-09-09'
    template['Description'] = f"CloudFormation template for API Gateway API: {api_json.get('name')}"

    # Parameters section
    template['Parameters'] = OrderedDict({
        'EnvPrefix': {
            'Type': 'String',
            'Description': 'Prefix for naming resources (e.g., dev, test, prod)',
            'MinLength': 1
        }
    })

    # Resources section
    resources_section = OrderedDict()

    # Create RestApi resource with EnvPrefix to avoid name conflicts
    api_logical_id = sanitize_name(api_json['name'] + 'RestApi')
    resources_section[api_logical_id] = {
        'Type': 'AWS::ApiGateway::RestApi',
        'Properties': {
            'Name': {'Fn::Sub': f"${{EnvPrefix}}{api_json['name']}"}
        }
    }

    # Prepare mapping of resource IDs to logical IDs
    resource_id_to_logical = {}
    for res in api_json['resources']:
        if res.get('path') == '/':
            resource_id_to_logical[res['id']] = None
        else:
            resource_id_to_logical[res['id']] = sanitize_name(api_json['name'] + res['path'].replace('/', '_') + 'Resource')

    method_logical_ids = []  # Collect all method logical IDs for deployment DependsOn

    # Create API Gateway Resource objects (skip root)
    for res in api_json['resources']:
        if res.get('path') == '/':
            continue
        logical_id = resource_id_to_logical[res['id']]
        parent_id = res.get('parentId')
        parent_logical = resource_id_to_logical.get(parent_id)
        parent_reference = {'Fn::GetAtt': [api_logical_id, 'RootResourceId']} if parent_logical is None else {'Ref': parent_logical}
        resources_section[logical_id] = {
            'Type': 'AWS::ApiGateway::Resource',
            'Properties': {
                'RestApiId': {'Ref': api_logical_id},
                'ParentId': parent_reference,
                'PathPart': res['pathPart']
            }
        }

    # Add methods and their integrations
    for res in api_json['resources']:
        res_logical = resource_id_to_logical.get(res['id'])
        methods = res.get('resourceMethods', {})
        for http_method, method_def in methods.items():
            method_logical = sanitize_name(api_json['name'] + res['path'].replace('/', '_') + http_method + 'Method')
            method_logical_ids.append(method_logical)
            resource_ref = {'Fn::GetAtt': [api_logical_id, 'RootResourceId']} if res['path'] == '/' else {'Ref': res_logical}
            method_props = {
                'RestApiId': {'Ref': api_logical_id},
                'ResourceId': resource_ref,
                'HttpMethod': http_method,
                'AuthorizationType': method_def.get('authorizationType', 'NONE'),
                'ApiKeyRequired': method_def.get('apiKeyRequired', False),
                'Integration': {},
                'MethodResponses': []
            }
            # Request parameters
            req_params = method_def.get('requestParameters', {})
            if req_params:
                method_props['RequestParameters'] = {param: req_params[param] for param in req_params}

            # Method responses
            for status, resp in method_def.get('methodResponses', {}).items():
                resp_obj = {'StatusCode': status, 'ResponseModels': {}}
                resp_params = resp.get('responseParameters', {})
                if resp_params:
                    resp_obj['ResponseParameters'] = {k: v for k, v in resp_params.items()}
                resp_models = resp.get('responseModels', {})
                if resp_models:
                    resp_obj['ResponseModels'] = resp_models
                method_props['MethodResponses'].append(resp_obj)

            # Integration configuration
            integration = method_def.get('methodIntegration', {})
            if integration:
                integ_obj = {'Type': integration['type']}
                if integration.get('type') in ['AWS', 'AWS_PROXY', 'HTTP', 'HTTP_PROXY']:
                    # Rewrite URI to use EnvPrefix-functionName
                    raw_uri = integration.get('uri')
                    match = re.search(r'/functions/arn:aws:lambda:[^:]+:[0-9]+:function:([^/]+)/', raw_uri or '')
                    if match:
                        orig_fn = match.group(1)
                        # Construct new URI using Fn::Sub
                        new_uri = {'Fn::Sub': f"arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/arn:aws:lambda:${{AWS::Region}}:${{AWS::AccountId}}:function:${{EnvPrefix}}-{orig_fn}/invocations"}
                        integ_obj['Uri'] = new_uri
                    else:
                        integ_obj['Uri'] = raw_uri
                    integ_obj['IntegrationHttpMethod'] = integration.get('httpMethod')
                # Always use same-account LabRole
                integ_obj['Credentials'] = {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}
                req_integ_params = integration.get('requestParameters', {})
                if req_integ_params:
                    integ_obj['RequestParameters'] = req_integ_params
                req_templates = integration.get('requestTemplates', {})
                if req_templates:
                    integ_obj['RequestTemplates'] = req_templates
                if integration.get('passthroughBehavior'):
                    integ_obj['PassthroughBehavior'] = integration['passthroughBehavior']
                if integration.get('contentHandling'):
                    integ_obj['ContentHandling'] = integration['contentHandling']
                if integration.get('timeoutInMillis'):
                    integ_obj['TimeoutInMillis'] = integration['timeoutInMillis']
                if integration.get('cacheNamespace'):
                    integ_obj['CacheNamespace'] = integration['cacheNamespace']
                if integration.get('cacheKeyParameters') is not None:
                    integ_obj['CacheKeyParameters'] = integration['cacheKeyParameters']
                integ_responses = []
                for status_code, integ_resp in integration.get('integrationResponses', {}).items():
                    ir = {'StatusCode': status_code}
                    if integ_resp.get('responseParameters'):
                        ir['ResponseParameters'] = integ_resp['responseParameters']
                    if integ_resp.get('responseTemplates'):
                        filtered_templates = {k: v for k, v in integ_resp['responseTemplates'].items() if v is not None}
                        if filtered_templates:
                            ir['ResponseTemplates'] = filtered_templates
                    integ_responses.append(ir)
                if integ_responses:
                    integ_obj['IntegrationResponses'] = integ_responses
                method_props['Integration'] = integ_obj

            resources_section[method_logical] = {
                'Type': 'AWS::ApiGateway::Method',
                'Properties': method_props
            }

    # Deployment resource (creates the stage inline)
    deployment_logical = sanitize_name(api_json['name'] + 'Deployment')
    resources_section[deployment_logical] = {
        'Type': 'AWS::ApiGateway::Deployment',
        'DependsOn': method_logical_ids,
        'Properties': {
            'RestApiId': {'Ref': api_logical_id},
            'StageName': {'Fn::Sub': f"${{EnvPrefix}}-{timestamp}"}
        }
    }

    # Models
    for model in api_json.get('models', []):
        model_logical = sanitize_name(api_json['name'] + model['name'] + 'Model')
        schema_obj = json.loads(model['schema']) if isinstance(model['schema'], str) else model['schema']
        resources_section[model_logical] = {
            'Type': 'AWS::ApiGateway::Model',
            'Properties': {
                'RestApiId': {'Ref': api_logical_id},
                'Name': {'Fn::Sub': f"${{EnvPrefix}}{model['name']}"},
                'ContentType': model['contentType'],
                'Schema': schema_obj
            }
        }

    # Authorizers
    for auth in api_json.get('authorizers', []):
        auth_logical = sanitize_name(api_json['name'] + auth['name'] + 'Authorizer')
        auth_props = {
            'RestApiId': {'Ref': api_logical_id},
            'Name': auth['name'],
            'Type': auth['type'],
            'IdentitySource': auth.get('identitySource'),
            'AuthorizerCredentials': {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}
        }
        if auth.get('providerARNs'):
            auth_props['ProviderARNs'] = auth['providerARNs']
        if auth.get('authorizerUri'):
            auth_props['AuthorizerUri'] = auth['authorizerUri']
        if auth.get('identityValidationExpression'):
            auth_props['IdentityValidationExpression'] = auth['identityValidationExpression']
        resources_section[auth_logical] = {
            'Type': 'AWS::ApiGateway::Authorizer',
            'Properties': auth_props
        }

    template['Resources'] = resources_section

    # Outputs
    template['Outputs'] = OrderedDict({
        'ApiEndpoint': {
            'Description': 'Invoke URL for the deployed API',
            'Value': {
                'Fn::Sub': f"https://${{{api_logical_id}}}.execute-api.${{AWS::Region}}.amazonaws.com/{timestamp}"}
        }
    })

    return template

# Script entry point

def main():
    parser = argparse.ArgumentParser(description='Convert API Gateway JSON to CloudFormation template')
    parser.add_argument('--input', required=True, help='Input JSON file from get-apigw.sh')
    parser.add_argument('--output', required=True, help='Output CloudFormation YAML file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        apis = json.load(f)

    if isinstance(apis, list) and len(apis) >= 1:
        api_json = apis[0]
    else:
        api_json = apis

    template = convert_api_to_cfn(api_json)
    plain_template = ordered_to_plain(template)

    # Dump to YAML string, then insert comments for readability
    yaml_str = yaml.safe_dump(plain_template, sort_keys=False)
    yaml_lines = yaml_str.splitlines()
    new_lines = []
    for line in yaml_lines:
        if line.startswith('AWSTemplateFormatVersion'):
            new_lines.append('# ---------------------- Template Header ----------------------')
            new_lines.append(line)
        elif line.startswith('Description'):
            new_lines.append(line)
        elif line.startswith('Parameters:'):
            new_lines.append("\n# ---------------------- Parameters ----------------------")
            new_lines.append(line)
        elif line.startswith('Resources:'):
            new_lines.append("\n# ---------------------- Resources ----------------------")
            new_lines.append(line)
        elif line.startswith('Outputs:'):
            new_lines.append("\n# ---------------------- Outputs ----------------------")
            new_lines.append(line)
        else:
            new_lines.append(line)

    with open(args.output, 'w') as out_f:
        out_f.write('\n'.join(new_lines) + '\n')

    print(f"CloudFormation template written to {args.output}")

if __name__ == '__main__':
    main()
