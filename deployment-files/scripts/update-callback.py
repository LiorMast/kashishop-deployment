#!/usr/bin/env python3
"""
Script to update callback.js with environment-specific Cognito and API endpoint values.
Ensures `const clientId`, `clientSecret`, `redirectUri`, `tokenEndpoint`, and `API` are correctly set without escaped quotes.
"""
import argparse
import subprocess
import sys
import re
import os

def aws_cli(cmd):
    """Run an AWS CLI command and return stdout, exit on error."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(f"Error running {' '.join(cmd)}: {proc.stderr}", file=sys.stderr)
        sys.exit(1)
    return proc.stdout.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Update callback.js variables from AWS environment"
    )
    parser.add_argument("--file", default="./frontend/script/callback.js",
                        help="Path to callback.js to update")
    parser.add_argument("--env", required=True,
                        help="Environment prefix, e.g. 'dev' or 'kash9'")
    parser.add_argument("--region", default=None,
                        help="AWS region (defaults to aws configure get region)")
    args = parser.parse_args()

    # Determine AWS region
    region = args.region or aws_cli(["aws", "configure", "get", "region"]).strip() or "us-east-1"
    env = args.env

    # Stack names
    cognito_stack = f"{env}-kashishop-cognito"
    s3_stack      = f"{env}-kashishop-s3"
    api_name      = f"{env}Kashishop2API"

    # Fetch values via AWS CLI
    user_pool_id = aws_cli([
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", cognito_stack,
        "--region", region,
        "--query", "Stacks[0].Outputs[?OutputKey=='KashishopUserPoolId'].OutputValue",
        "--output", "text"
    ])
    client_id = aws_cli([
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", cognito_stack,
        "--region", region,
        "--query", "Stacks[0].Outputs[?OutputKey=='Kashishop2UserPoolClientId'].OutputValue",
        "--output", "text"
    ])
    client_secret = aws_cli([
        "aws", "cognito-idp", "describe-user-pool-client",
        "--user-pool-id", user_pool_id,
        "--client-id", client_id,
        "--region", region,
        "--query", "UserPoolClient.ClientSecret",
        "--output", "text"
    ])
    domain_prefix = aws_cli([
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", cognito_stack,
        "--region", region,
        "--query", "Stacks[0].Outputs[?ends_with(OutputKey,'UserPoolDomainId')].OutputValue | [0]",
        "--output", "text"
    ])
    token_endpoint = f"https://{domain_prefix}.auth.{region}.amazoncognito.com/oauth2/token"
    bucket_name = aws_cli([
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", s3_stack,
        "--region", region,
        "--query", "Stacks[0].Outputs[?OutputKey=='Kashishop2BucketName'].OutputValue",
        "--output", "text"
    ])
    redirect_uri = f"https://{bucket_name}.s3.{region}.amazonaws.com/main/callback.html"
    api_id = aws_cli([
        "aws", "apigateway", "get-rest-apis",
        "--query", f"items[?name=='{api_name}'].id | [0]",
        "--output", "text",
        "--region", region
    ])
    api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/{env}"

    # Read callback.js
    try:
        content = open(args.file, 'r', encoding='utf-8').read()
    except Exception as e:
        print(f"Failed to read {args.file}: {e}", file=sys.stderr)
        sys.exit(1)

    # Simple replacements for existing constants
    simple_repls = {
        r'const\s+clientId\s*=\s*".*?";': f'const clientId = "{client_id}";',
        r'const\s+clientSecret\s*=\s*".*?";': f'const clientSecret = "{client_secret}";',
        r'const\s+redirectUri\s*=\s*".*?";': f'const redirectUri = "{redirect_uri}";'
    }
    for pat, rep in simple_repls.items():
        content = re.sub(pat, rep, content)

    # tokenEndpoint replacement or insertion
    token_pattern = r'const\s+tokenEndpoint\s*=\s*".*?";'
    token_repl = f'const tokenEndpoint = "{token_endpoint}";'
    if re.search(token_pattern, content):
        content = re.sub(token_pattern, token_repl, content)
    else:
        # Insert after redirectUri using a lambda to avoid raw-string pitfalls
        content = re.sub(
            r'(const\s+redirectUri\s*=\s*".*?";)',
            lambda m: f"{m.group(1)}\n{token_repl}",
            content
        )

    # API URL replacement or insertion
    api_pattern = r'const\s+API\s*=\s*".*?";'
    api_repl = f'const API = "{api_url}";'
    if re.search(api_pattern, content):
        content = re.sub(api_pattern, api_repl, content)
    else:
        content = re.sub(
            r'(const\s+tokenEndpoint\s*=\s*".*?";)',
            lambda m: f"{m.group(1)}\n{api_repl}",
            content
        )

    # Write back
    try:
        with open(args.file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully updated {args.file}.")
    except Exception as e:
        print(f"Failed to write {args.file}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
