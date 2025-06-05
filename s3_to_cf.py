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

# Main function to convert S3 JSON dump to CloudFormation template
def convert_s3_to_cfn(buckets_json):
    template = OrderedDict()
    # Template header
    template['AWSTemplateFormatVersion'] = '2010-09-09'
    template['Description'] = 'CloudFormation template for S3 buckets and policies'

    # Parameters section
    template['Parameters'] = OrderedDict({
        'EnvPrefix': {
            'Type': 'String',
            'Description': 'Prefix for naming buckets (e.g., dev, test, prod)',
            'MinLength': 1
        }
    })

    resources = OrderedDict()

    for bucket_obj in buckets_json:
        base_name = bucket_obj.get('bucketName')
        logical_base = sanitize_name(base_name)

        # Define the S3 Bucket resource
        bucket_logical = f"{logical_base}Bucket"
        bucket_props = OrderedDict()
        # Prefix the bucket name
        bucket_props['BucketName'] = {'Fn::Sub': f"${{EnvPrefix}}-{base_name}"}

        # Versioning
        versioning = bucket_obj.get('versioning', {})
        if 'Status' in versioning:
            bucket_props['VersioningConfiguration'] = {'Status': versioning['Status']}

        # Encryption
        encryption = bucket_obj.get('encryption', {}).get('ServerSideEncryptionConfiguration')
        if encryption and 'Rules' in encryption and encryption['Rules']:
            rules = []
            for rule in encryption['Rules']:
                default = rule.get('ApplyServerSideEncryptionByDefault', {})
                sse_alg = default.get('SSEAlgorithm')
                if sse_alg:
                    rules.append({
                        'ServerSideEncryptionByDefault': {
                            'SSEAlgorithm': sse_alg
                        }
                    })
            if rules:
                bucket_props['BucketEncryption'] = {
                    'ServerSideEncryptionConfiguration': rules
                }

        # Lifecycle
        lifecycle = bucket_obj.get('lifecycleConfiguration', {}).get('Rules')
        if lifecycle:
            bucket_props['LifecycleConfiguration'] = {'Rules': lifecycle}

        # Tags
        tags = bucket_obj.get('tags', {}).get('TagSet', [])
        if tags:
            bucket_props['Tags'] = [{'Key': t['Key'], 'Value': t['Value']} for t in tags]

        # CORS
        cors = bucket_obj.get('corsConfiguration', {}).get('CORSRules', [])
        if cors:
            bucket_props['CorsConfiguration'] = {'CorsRules': cors}

        # Website configuration
        website = bucket_obj.get('websiteConfiguration', {})
        if 'IndexDocument' in website or 'ErrorDocument' in website:
            wc = {}
            if 'IndexDocument' in website:
                wc['IndexDocument'] = website['IndexDocument']['Suffix']
            if 'ErrorDocument' in website:
                wc['ErrorDocument'] = website['ErrorDocument']['Key']
            bucket_props['WebsiteConfiguration'] = wc

        # Logging configuration
        logging = bucket_obj.get('loggingConfiguration', {})
        if logging.get('LoggingEnabled'):
            bucket_props['LoggingConfiguration'] = logging['LoggingEnabled']

        # Add the bucket resource
        resources[bucket_logical] = {
            'Type': 'AWS::S3::Bucket',
            'Properties': bucket_props
        }

        # Bucket Policy (if exists, adjust resource ARNs to include EnvPrefix)
        policy_str = bucket_obj.get('policy', {}).get('Policy')
        if policy_str and policy_str != 'null':
            try:
                policy_doc = json.loads(policy_str)
            except json.JSONDecodeError:
                policy_doc = None
            if policy_doc:
                # Rewrite all resource ARNs to include the EnvPrefix in bucket names
                new_statements = []
                for stmt in policy_doc.get('Statement', []):
                    new_stmt = stmt.copy()
                    if 'Resource' in stmt:
                        res = stmt['Resource']
                        if isinstance(res, str):
                            new_stmt['Resource'] = {'Fn::Sub': res.replace('arn:aws:s3:::', '${EnvPrefix}-')}
                        elif isinstance(res, list):
                            new_stmt['Resource'] = [{ 'Fn::Sub': r.replace('arn:aws:s3:::', '${EnvPrefix}-')} for r in res]
                    new_statements.append(new_stmt)
                policy_doc['Statement'] = new_statements
                policy_logical = f"{logical_base}BucketPolicy"
                resources[policy_logical] = {
                    'Type': 'AWS::S3::BucketPolicy',
                    'Properties': {
                        'Bucket': {'Ref': bucket_logical},
                        'PolicyDocument': policy_doc
                    }
                }
        policy_str = bucket_obj.get('policy', {}).get('Policy')
        if policy_str and policy_str != 'null':
            try:
                policy_doc = json.loads(policy_str)
            except json.JSONDecodeError:
                policy_doc = None
            if policy_doc:
                policy_logical = f"{logical_base}BucketPolicy"
                resources[policy_logical] = {
                    'Type': 'AWS::S3::BucketPolicy',
                    'Properties': {
                        'Bucket': {'Ref': bucket_logical},
                        'PolicyDocument': policy_doc
                    }
                }

    template['Resources'] = resources

    # Outputs: expose each bucket's name and ARN
    outputs = OrderedDict()
    for bucket_obj in buckets_json:
        base_name = bucket_obj.get('bucketName')
        logical_base = sanitize_name(base_name)
        bucket_logical = f"{logical_base}Bucket"
        outputs[f"{logical_base}BucketName"] = {
            'Description': f"Name of bucket {base_name}",
            'Value': {'Ref': bucket_logical}
        }
        outputs[f"{logical_base}BucketArn"] = {
            'Description': f"ARN of bucket {base_name}",
            'Value': {'Fn::GetAtt': [bucket_logical, 'Arn']}
        }
    template['Outputs'] = outputs

    return template


def main():
    parser = argparse.ArgumentParser(description='Convert S3 JSON to CloudFormation template')
    parser.add_argument('--input', required=True, help='Input JSON file from get-s3.sh')
    parser.add_argument('--output', required=True, help='Output CloudFormation YAML file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        buckets_json = json.load(f)

    template = convert_s3_to_cfn(buckets_json)
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
