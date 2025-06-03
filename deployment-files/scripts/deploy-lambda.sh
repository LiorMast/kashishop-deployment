#!/usr/bin/env bash
#
# This script zips each Python file in the ./lambda/ directory
# and either creates or updates the corresponding AWS Lambda function
# named "${EnvPrefix}-${FUNCTION_NAME}" using the IAM role
# arn:aws:iam::<ACCOUNT_ID>:role/LabRole.
#
# Usage:
#   chmod +x deploy-lambdas.sh
#   ./deploy-lambdas.sh <EnvPrefix>
#
# Example:
#   ./deploy-lambdas.sh dev
#
# Assumptions:
# - All Lambda Python files sit directly in ./lambda/
#   e.g. lambda/user_isactive_switch.py
# - Handler for every function is lambda_function.lambda_handler.
# - Runtime is python3.13 and Architecture x86_64.
# - IAM role is arn:aws:iam::<ACCOUNT_ID>:role/LabRole.
#
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <EnvPrefix>"
  exit 1
fi

EnvPrefix="$1"
LambdaDir="$(pwd)/lambda"

if [ ! -d "$LambdaDir" ]; then
  echo "❌ Directory '$LambdaDir' not found. Run this script from the repo root."
  exit 1
fi

# Determine AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
RoleArn="arn:aws:iam::${ACCOUNT_ID}:role/LabRole"

echo "Using IAM role: $RoleArn" >&2
echo "Deploying Lambda functions with prefix '$EnvPrefix'..." >&2

for file_path in "$LambdaDir"/*.py; do
  [ -f "$file_path" ] || continue
  filename="$(basename "$file_path")"
  fn_name="${filename%.py}"
  zip_path="/tmp/${fn_name}.zip"

  echo "----------------------------------------" >&2
  echo "Packaging function: $fn_name" >&2

  # Create a temporary directory and copy the .py file as lambda_function.py
  tmpdir="$(mktemp -d)"
  cp "$file_path" "$tmpdir/lambda_function.py"
  (cd "$tmpdir" && zip -qr "$zip_path" lambda_function.py)
  rm -rf "$tmpdir"
  echo "  • Zipped $fn_name → $zip_path" >&2

  full_fn_name="${EnvPrefix}-${fn_name}"
  echo "  • Checking if Lambda '$full_fn_name' exists..." >&2

  if aws lambda get-function --function-name "$full_fn_name" >/dev/null 2>&1; then
    echo "  • Lambda exists. Updating code..." >&2
    aws lambda update-function-code \
      --function-name "$full_fn_name" \
      --zip-file "fileb://$zip_path" \
      >/dev/null
    echo "  ✓ Updated code for $full_fn_name" >&2
  else
    echo "  • Lambda does not exist. Creating with default settings..." >&2
    aws lambda create-function \
      --function-name "$full_fn_name" \
      --runtime python3.13 \
      --role "$RoleArn" \
      --handler lambda_function.lambda_handler \
      --zip-file "fileb://$zip_path" \
      --timeout 15 \
      --memory-size 128 \
      --architecture x86_64 \
      --publish \
      >/dev/null
    echo "  ✓ Created $full_fn_name" >&2
  fi

  rm -f "$zip_path"
  echo >&2
done

echo "✅ All Lambda functions deployed." >&2
