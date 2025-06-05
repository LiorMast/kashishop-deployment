#!/usr/bin/env python3
import os
import re
import sys
import zipfile
import subprocess
import tempfile
from pathlib import Path
import argparse
import yaml

# This script deploys Lambdas but first updates code to prefix DynamoDB table names
# based on the entries in ../templates/dynamodb-template.yaml
# 1. Reads table names from the DynamoDB CFN template
# 2. Rewrites each .py file in ./lambda/ to replace any literal 'TableName' with '<EnvPrefix>-TableName'
# 3. Zips and deploys via AWS CLI
# Usage: python3 deploy-lambda.py <EnvPrefix>


def load_table_names():
    # Locate the DynamoDB template relative to this script
    script_dir = Path(__file__).parent
    template_path = (script_dir / '..' / 'templates' / 'dynamodb-template.yaml').resolve()
    if not template_path.is_file():
        print(f"❌ DynamoDB template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    with open(template_path, 'r') as f:
        doc = yaml.safe_load(f)

    table_names = []
    resources = doc.get('Resources', {})
    for logical_id, resource in resources.items():
        if resource.get('Type') == 'AWS::DynamoDB::Table':
            props = resource.get('Properties', {})
            name_prop = props.get('TableName')
            # If TableName uses Fn::Sub, extract literal
            if isinstance(name_prop, dict) and 'Fn::Sub' in name_prop:
                # Expect pattern "${EnvPrefix}-BaseName"
                sub_str = name_prop['Fn::Sub']
                # Extract after hyphen: everything after '}-'
                m = re.match(r"\$\{EnvPrefix\}-(?P<base>.+)", sub_str)
                if m:
                    table_names.append(m.group('base'))
            elif isinstance(name_prop, str):
                table_names.append(name_prop)
    return table_names


def modify_lambda_code(original_path, env_prefix, temp_dir, table_names):
    content = original_path.read_text()
    # Replace any occurrence of 'TableName' literal with prefix
    # Match both single and double quoted
    for tbl in table_names:
        # regex to match 'tbl' or "tbl"
        pattern = re.compile(rf"(?P<quote>['\"])({re.escape(tbl)})(?P=quote)")
        content = pattern.sub(lambda m: f"{m.group('quote')}{env_prefix}-{tbl}{m.group('quote')}", content)

    # Also adjust dynamodb.Table('Name') patterns (redundant if above caught)
    dt_pattern = re.compile(r"dynamodb\.Table\(\s*['\"](?P<name>[^'\"]+)['\"]\s*\)")
    content = dt_pattern.sub(lambda m: f"dynamodb.Table('{env_prefix}-{m.group('name')}')", content)

    modified_path = temp_dir / 'lambda_function.py'
    modified_path.write_text(content)
    return modified_path


def zip_lambda_code(modified_path, fn_name):
    zip_path = Path(tempfile.gettempdir()) / f"{fn_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(modified_path, 'lambda_function.py')
    return zip_path


def aws_cli_exists(function_name):
    try:
        subprocess.run(['aws', 'lambda', 'get-function', '--function-name', function_name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def deploy_lambda(zip_path, full_fn_name, role_arn):
    if aws_cli_exists(full_fn_name):
        print(f"  • Lambda exists. Updating code for {full_fn_name}", file=sys.stderr)
        subprocess.run([
            'aws', 'lambda', 'update-function-code',
            '--function-name', full_fn_name,
            '--zip-file', f"fileb://{zip_path}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  ✓ Updated code for {full_fn_name}", file=sys.stderr)
    else:
        print(f"  • Lambda does not exist. Creating {full_fn_name}", file=sys.stderr)
        subprocess.run([
            'aws', 'lambda', 'create-function',
            '--function-name', full_fn_name,
            '--runtime', 'python3.13',
            '--role', role_arn,
            '--handler', 'lambda_function.lambda_handler',
            '--zip-file', f"fileb://{zip_path}",
            '--timeout', '15',
            '--memory-size', '128',
            '--architecture', 'x86_64',
            '--publish'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  ✓ Created {full_fn_name}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Deploy Lambdas with EnvPrefix-aware DynamoDB table names')
    parser.add_argument('EnvPrefix', help='Prefix to apply to function names and DynamoDB tables')
    args = parser.parse_args()
    env_prefix = args.EnvPrefix

    table_names = load_table_names()
    if not table_names:
        print("❌ No DynamoDB table names found in template.", file=sys.stderr)
        sys.exit(1)

    lambda_dir = Path.cwd() / 'lambda'
    if not lambda_dir.is_dir():
        print(f"❌ Directory '{lambda_dir}' not found. Run from repo root.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
                             capture_output=True, text=True, check=True)
    account_id = result.stdout.strip()
    role_arn = f"arn:aws:iam::{account_id}:role/LabRole"

    print(f"Using IAM role: {role_arn}", file=sys.stderr)
    print(f"Deploying Lambda functions with prefix '{env_prefix}'...", file=sys.stderr)
    print(file=sys.stderr)

    for file_path in lambda_dir.glob('*.py'):
        fn_name = file_path.stem
        full_fn_name = f"{env_prefix}-{fn_name}"
        print("----------------------------------------", file=sys.stderr)
        print(f"Packaging function: {fn_name}", file=sys.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            modified_path = modify_lambda_code(file_path, env_prefix, temp_dir, table_names)
            zip_path = zip_lambda_code(modified_path, fn_name)
            print(f"  • Zipped {fn_name} → {zip_path}", file=sys.stderr)

            print(f"  • Checking if Lambda '{full_fn_name}' exists...", file=sys.stderr)
            deploy_lambda(zip_path, full_fn_name, role_arn)

            zip_path.unlink(missing_ok=True)
        print(file=sys.stderr)

    print("✅ All Lambda functions deployed.", file=sys.stderr)

if __name__ == '__main__':
    main()
