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

# Main conversion function for DynamoDB

def convert_dynamodb_to_cfn(tables_json):
    template = OrderedDict()
    # Template header
    template['AWSTemplateFormatVersion'] = '2010-09-09'
    template['Description'] = 'CloudFormation template for DynamoDB tables'

    # Parameters
    template['Parameters'] = OrderedDict({
        'EnvPrefix': {
            'Type': 'String',
            'Description': 'Prefix for naming DynamoDB tables (e.g., dev, test, prod)',
            'MinLength': 1
        }
    })

    resources_section = OrderedDict()

    # For each table in JSON, create a DynamoDB::Table resource
    for table_obj in tables_json:
        table_name = table_obj.get('tableName')
        desc = table_obj.get('description', {})
        logical_id = sanitize_name(table_name + 'Table')

        # Build properties
        props = OrderedDict()
        # TableName with prefix
        props['TableName'] = {'Fn::Sub': f"${{EnvPrefix}}-{table_name}"}

        # AttributeDefinitions
        attr_defs = desc.get('AttributeDefinitions', [])
        if attr_defs:
            props['AttributeDefinitions'] = [{
                'AttributeName': ad['AttributeName'],
                'AttributeType': ad['AttributeType']
            } for ad in attr_defs]

        # KeySchema
        key_schema = desc.get('KeySchema', [])
        if key_schema:
            props['KeySchema'] = [{
                'AttributeName': ks['AttributeName'],
                'KeyType': ks['KeyType']
            } for ks in key_schema]

        # Determine BillingMode: PAY_PER_REQUEST or PROVISIONED
        billing = desc.get('BillingModeSummary', {})
        billing_mode = billing.get('BillingMode')
        if billing_mode == 'PAY_PER_REQUEST':
            props['BillingMode'] = 'PAY_PER_REQUEST'
        else:
            # ProvisionedMode: use ProvisionedThroughput
            throughput = desc.get('ProvisionedThroughput', {})
            read_units = throughput.get('ReadCapacityUnits', 5)
            write_units = throughput.get('WriteCapacityUnits', 5)
            props['ProvisionedThroughput'] = {
                'ReadCapacityUnits': read_units,
                'WriteCapacityUnits': write_units
            }

        # Global Secondary Indexes
        gsis = desc.get('GlobalSecondaryIndexes', [])
        if gsis:
            gsi_list = []
            for gsi in gsis:
                gsi_entry = OrderedDict()
                gsi_entry['IndexName'] = gsi['IndexName']
                # GSI KeySchema
                gsi_entry['KeySchema'] = [{
                    'AttributeName': ks['AttributeName'],
                    'KeyType': ks['KeyType']
                } for ks in gsi.get('KeySchema', [])]
                # GSI Projection
                proj = gsi.get('Projection', {})
                proj_entry = {'ProjectionType': proj.get('ProjectionType', 'ALL')}
                if proj.get('NonKeyAttributes'):
                    proj_entry['NonKeyAttributes'] = proj['NonKeyAttributes']
                gsi_entry['Projection'] = proj_entry

                # GSI ProvisionedThroughput if not PAY_PER_REQUEST
                gsi_throughput = gsi.get('ProvisionedThroughput')
                if gsi_throughput:
                    gsi_entry['ProvisionedThroughput'] = {
                        'ReadCapacityUnits': gsi_throughput.get('ReadCapacityUnits', 5),
                        'WriteCapacityUnits': gsi_throughput.get('WriteCapacityUnits', 5)
                    }
                gsi_list.append(gsi_entry)
            props['GlobalSecondaryIndexes'] = gsi_list

        # Time to Live
        ttl_desc = table_obj.get('timeToLive', {})
        if ttl_desc.get('TimeToLiveStatus') == 'ENABLED':
            props['TimeToLiveSpecification'] = {
                'AttributeName': ttl_desc.get('AttributeName'),
                'Enabled': True
            }

        # Tags
        tags = table_obj.get('tags', [])
        if tags:
            props['Tags'] = [{'Key': t.get('Key'), 'Value': t.get('Value')} for t in tags]

        # Assemble resource
        resources_section[logical_id] = {
            'Type': 'AWS::DynamoDB::Table',
            'Properties': props
        }

    template['Resources'] = resources_section

    # Outputs: provide each table ARN
    outputs_section = OrderedDict()
    for table_obj in tables_json:
        table_name = table_obj.get('tableName')
        logical_id = sanitize_name(table_name + 'Table')
        output_key = sanitize_name(table_name + 'Arn')
        outputs_section[output_key] = {
            'Description': f"ARN of {table_name} table",
            'Value': {'Fn::GetAtt': [logical_id, 'Arn']}
        }
    template['Outputs'] = outputs_section

    return template

# Script entry point

def main():
    parser = argparse.ArgumentParser(description='Convert DynamoDB JSON to CloudFormation template')
    parser.add_argument('--input', required=True, help='Input JSON file from get-dynamodb.sh')
    parser.add_argument('--output', required=True, help='Output CloudFormation YAML file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        tables_json = json.load(f)

    template = convert_dynamodb_to_cfn(tables_json)
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
