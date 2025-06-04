#!/usr/bin/env python3
import os
import re
import sys
import json
import shutil
import zipfile
import subprocess
import tempfile
from pathlib import Path
import argparse

# This script mirrors deploy-lambda.sh but in Python. It:
# 1. Reads each .py file in ./lambda/
# 2. Prefixes all DynamoDB table references like Table('Name') to Table('<EnvPrefix>-Name')
# 3. Zips the modified code and deploys (create/update) the Lambda via AWS CLI
# Usage: python3 deploy_lambda.py <EnvPrefix>


def modify_lambda_code(original_path, env_prefix, temp_dir):
    # Read the original lambda file
    content = original_path.read_text()
    # Pattern to find dynamodb.Table('TableName') or TableName = 'Items' usage in code
    # We focus on dynamodb.Table(...) calls
    pattern = re.compile(r"dynamodb\.Table\(\s*['\"](?P<name>[^'\"]+)['\"]\s*\)")

    def repl(match):
        name = match.group('name')
        new_name = f"{env_prefix}-{name}"
        return f"dynamodb.Table('{new_name}')"

    new_content = pattern.sub(repl, content)

    # Write modified content as lambda_function.py in temp_dir
    modified_path = temp_dir / 'lambda_function.py'
    modified_path.write_text(new_content)
    return modified_path


def zip_lambda_code(modified_path, fn_name):
    zip_path = Path(tempfile.gettempdir()) / f"{fn_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # The handler expects lambda_function.py at root
        z.write(modified_path, 'lambda_function.py')
    return zip_path


def aws_cli_exists(function_name):
    # Return True if Lambda function exists
    try:
        subprocess.run(['aws', 'lambda', 'get-function', '--function-name', function_name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def deploy_lambda(zip_path, full_fn_name, role_arn):
    if aws_cli_exists(full_fn_name):
        print(f"  • Updating code for {full_fn_name}")
        subprocess.run([
            'aws', 'lambda', 'update-function-code',
            '--function-name', full_fn_name,
            '--zip-file', f"fileb://{zip_path}"], check=True)
    else:
        print(f"  • Creating Lambda {full_fn_name}")
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
            '--publish'], check=True)


def main():
    parser = argparse.ArgumentParser(description='Deploy Lambdas with EnvPrefix-aware DynamoDB table names')
    parser.add_argument('EnvPrefix', help='Prefix to apply to function names and DynamoDB tables')
    args = parser.parse_args()
    env_prefix = args.EnvPrefix

    # Lambda source directory
    lambda_dir = Path.cwd() / 'lambda'
    if not lambda_dir.is_dir():
        print(f"❌ Directory '{lambda_dir}' not found. Run from repo root.")
        sys.exit(1)

    # Determine AWS account ID
    result = subprocess.run(['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
                             capture_output=True, text=True, check=True)
    account_id = result.stdout.strip()
    role_arn = f"arn:aws:iam::{account_id}:role/LabRole"

    print(f"Using IAM role: {role_arn}")
    print(f"Deploying Lambda functions with prefix '{env_prefix}'...\n")

    for file_path in lambda_dir.glob('*.py'):
        if not file_path.is_file():
            continue
        fn_name = file_path.stem
        full_fn_name = f"{env_prefix}-{fn_name}"
        print("----------------------------------------")
        print(f"Packaging function: {fn_name}")

        # Create temp directory
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            modified_path = modify_lambda_code(file_path, env_prefix, temp_dir)
            zip_path = zip_lambda_code(modified_path, fn_name)

            # Deploy via AWS CLI
            deploy_lambda(zip_path, full_fn_name, role_arn)

            # Clean up zip
            zip_path.unlink(missing_ok=True)
        print()

    print("✅ All Lambda functions deployed.")

if __name__ == '__main__':
    main()
