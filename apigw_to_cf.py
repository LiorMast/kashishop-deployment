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

# Recursively convert OrderedDict to plain dicts for YAML serialization
def ordered_to_plain(obj):
    if isinstance(obj, OrderedDict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ordered_to_plain(v) for v in obj]
    return obj

# Main conversion function with full CORS support (including wildcard methods and GatewayResponses)
def convert_api_to_cfn(api_json):
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')

    template = OrderedDict()
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

    resources_section = OrderedDict()

    # 1) Create RestApi
    api_logical_id = sanitize_name(api_json['name'] + 'RestApi')
    resources_section[api_logical_id] = {
        'Type': 'AWS::ApiGateway::RestApi',
        'Properties': {
            'Name': {'Fn::Sub': f"${{EnvPrefix}}{api_json['name']}"},
            'EndpointConfiguration': {'Types': ['REGIONAL']}
        }
    }

    # 2) Map each resource ID to a logical name (root path is None)
    resource_id_to_logical = {}
    for res in api_json['resources']:
        if res.get('path') == '/':
            resource_id_to_logical[res['id']] = None
        else:
            resource_id_to_logical[res['id']] = sanitize_name(
                api_json['name'] + res['path'].replace('/', '_') + 'Resource'
            )

    method_logical_ids = []

    # 3) Create AWS::ApiGateway::Resource objects
    for res in api_json['resources']:
        if res.get('path') == '/':
            continue
        logical_id = resource_id_to_logical[res['id']]
        parent_id = res.get('parentId')
        parent_logical = resource_id_to_logical.get(parent_id)
        parent_reference = (
            {'Fn::GetAtt': [api_logical_id, 'RootResourceId']} 
            if parent_logical is None 
            else {'Ref': parent_logical}
        )
        resources_section[logical_id] = {
            'Type': 'AWS::ApiGateway::Resource',
            'Properties': {
                'RestApiId': {'Ref': api_logical_id},
                'ParentId': parent_reference,
                'PathPart': res['pathPart']
            }
        }

    # 4) Add Methods and CORS OPTIONS for each resource
    for res in api_json['resources']:
        res_logical = resource_id_to_logical.get(res['id'])
        resource_ref = (
            {'Fn::GetAtt': [api_logical_id, 'RootResourceId']} 
            if res.get('path') == '/' 
            else {'Ref': res_logical}
        )
        methods = res.get('resourceMethods', {})

        for http_method, method_def in methods.items():
            # a) Main Method (GET/POST/PUT/... whichever is defined)
            method_logical = sanitize_name(
                api_json['name'] + res['path'].replace('/', '_') + http_method + 'Method'
            )
            method_logical_ids.append(method_logical)

            # Build MethodResponses (always include CORS wildcard header)
            method_responses = [{
                'StatusCode': '200',
                'ResponseModels': {'application/json': 'Empty'},
                'ResponseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': False
                }
            }]

            # Build Method properties
            method_props = {
                'RestApiId': {'Ref': api_logical_id},
                'ResourceId': resource_ref,
                'HttpMethod': http_method,
                'AuthorizationType': method_def.get('authorizationType', 'NONE'),
                'ApiKeyRequired': method_def.get('apiKeyRequired', False),
                'Integration': {},
                'MethodResponses': method_responses
            }

            # If there are request parameters to pass through, include them
            req_params = method_def.get('requestParameters', {})
            if req_params:
                method_props['RequestParameters'] = {
                    param: req_params[param] for param in req_params
                }

            # b) Integration setup
            integration = method_def.get('methodIntegration', {})
            if integration:
                integ_obj = {'Type': integration['type']}
                raw_uri = integration.get('uri')

                # If this is a Lambda or HTTP integration, rewrite the function ARN to include EnvPrefix
                if integration.get('type') in ['AWS', 'AWS_PROXY', 'HTTP', 'HTTP_PROXY'] and raw_uri:
                    match = re.search(r'/functions/arn:aws:lambda:[^:]+:[0-9]+:function:([^/]+)/', raw_uri)
                    if match:
                        orig_fn = match.group(1)
                        new_uri = {
                            'Fn::Sub': (
                                f"arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/arn:aws:lambda:${{AWS::Region}}:"
                                f"${{AWS::AccountId}}:function:${{EnvPrefix}}-{orig_fn}/invocations"
                            )
                        }
                        integ_obj['Uri'] = new_uri
                    else:
                        integ_obj['Uri'] = raw_uri
                    integ_obj['IntegrationHttpMethod'] = integration.get('httpMethod')

                # Always use the “LabRole” for Lambda
                integ_obj['Credentials'] = {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}

                # Pass through any request parameters or templates
                if integration.get('requestParameters'):
                    integ_obj['RequestParameters'] = integration['requestParameters']
                if integration.get('requestTemplates'):
                    integ_obj['RequestTemplates'] = integration['requestTemplates']

                # Preserve passthroughBehavior, contentHandling, timeout, and caching if present
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

                # Always inject a wildcard CORS header into every IntegrationResponse
                integ_obj['IntegrationResponses'] = [{
                    'StatusCode': '200',
                    'ResponseParameters': {
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                }]

                method_props['Integration'] = integ_obj

            resources_section[method_logical] = {
                'Type': 'AWS::ApiGateway::Method',
                'Properties': method_props
            }

            # c) Add a CORS OPTIONS method on this same resource
            options_logical = sanitize_name(
                api_json['name'] + res['path'].replace('/', '_') + 'OptionsMethod'
            )
            options_props = {
                'RestApiId': {'Ref': api_logical_id},
                'ResourceId': resource_ref,
                'HttpMethod': 'OPTIONS',
                'AuthorizationType': 'NONE',
                'ApiKeyRequired': False,
                'Integration': {
                    'Type': 'MOCK',
                    'RequestTemplates': {'application/json': '{"statusCode": 200}'},
                    'IntegrationResponses': [{
                        'StatusCode': '200',
                        'ResponseParameters': {
                            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,X-Api-Key,X-Amz-Date,X-Amz-Security-Token'",
                            'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                            'method.response.header.Access-Control-Allow-Origin': "'*'"
                        }
                    }]
                },
                'MethodResponses': [{
                    'StatusCode': '200',
                    'ResponseModels': {'application/json': 'Empty'},
                    'ResponseParameters': {
                        'method.response.header.Access-Control-Allow-Headers': False,
                        'method.response.header.Access-Control-Allow-Methods': False,
                        'method.response.header.Access-Control-Allow-Origin': False
                    }
                }]
            }
            resources_section[options_logical] = {
                'Type': 'AWS::ApiGateway::Method',
                'Properties': options_props
            }
            method_logical_ids.append(options_logical)

    # 5) Deployment resource, with MethodSettings (no extraneous keys)
    deployment_logical = sanitize_name(api_json['name'] + 'Deployment')
    resources_section[deployment_logical] = {
        'Type': 'AWS::ApiGateway::Deployment',
        'DependsOn': method_logical_ids,
        'Properties': {
            'RestApiId': {'Ref': api_logical_id},
            'StageName': {'Fn::Sub': f"${{EnvPrefix}}-{timestamp}"}
        }
    }

    # 6) Models
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

    # 7) Authorizers
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
        resources_section[auth_logical] = {'Type': 'AWS::ApiGateway::Authorizer', 'Properties': auth_props}

    # 8) Add GatewayResponses (only ResponseParameters allowed)
    for response_type in ['DEFAULT_4XX', 'DEFAULT_5XX']:
        gateway_logical = sanitize_name(api_json['name'] + response_type + 'GatewayResponse')
        resources_section[gateway_logical] = {
            'Type': 'AWS::ApiGateway::GatewayResponse',
            'Properties': {
                'ResponseType': response_type,
                'RestApiId': {'Ref': api_logical_id},
                'ResponseParameters': {
                    'gatewayresponse.header.Access-Control-Allow-Origin': "'*'",
                    'gatewayresponse.header.Access-Control-Allow-Headers': "'*'",
                    'gatewayresponse.header.Access-Control-Allow-Methods': "'*'"
                },
                'StatusCode': '200'
            }
        }

    template['Resources'] = resources_section

    # 9) Outputs
    template['Outputs'] = OrderedDict({
        'ApiEndpoint': {
            'Description': 'Invoke URL for the deployed API',
            'Value': {'Fn::Sub': f"https://${{{api_logical_id}}}.execute-api.${{AWS::Region}}.amazonaws.com/{timestamp}"}
        }
    })

    return template

# Script entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert API Gateway JSON to CloudFormation template with CORS')
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
