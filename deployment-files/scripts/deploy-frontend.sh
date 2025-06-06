#!/usr/bin/env bash
#
# deploy-frontend.sh (updated)
#
# Usage: ./deploy-frontend.sh <EnvPrefix>
#
# This script reads the S3 CloudFormation stack (named <EnvPrefix>-kashishop-s3),
# finds the first S3 bucket created by that stack, and syncs the contents of ./frontend/
# into that bucket.
# It also creates placeholder objects for any empty directories under ./frontend/.
#
# Requirements:
#  • AWS CLI v2 (configured with credentials & region)
#  • The CFN stack "<EnvPrefix>-kashishop-s3" must exist and contain at least one S3 bucket.
#
# Example:
#   chmod +x deploy-frontend.sh
#   ./deploy-frontend.sh dev
#
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <EnvPrefix>"
  exit 1
fi

EnvPrefix="$1"
FrontendDir="$(pwd)/frontend"

if [ ! -d "$FrontendDir" ]; then
  echo "❌ Directory '$FrontendDir' not found. Ensure you run from repo root and have a 'frontend/' folder."
  exit 1
fi

# Derive the S3 stack name
S3_STACK_NAME="${EnvPrefix}-kashishop-s3"

echo "Looking up bucket from CloudFormation stack: $S3_STACK_NAME" >&2
# Retrieve the physical resource ID of the first S3 bucket in the stack
BUCKET_NAME=$(aws cloudformation list-stack-resources \
  --stack-name "$S3_STACK_NAME" \
  --query "StackResourceSummaries[?ResourceType=='AWS::S3::Bucket'] | [0].PhysicalResourceId" \
  --output text)

if [ -z "$BUCKET_NAME" ] || [ "$BUCKET_NAME" == "None" ]; then
  echo "❌ No S3 bucket found in stack '$S3_STACK_NAME'."
  exit 1
fi

echo "Deploying 'frontend/' contents into S3 bucket: $BUCKET_NAME" >&2

# 1) Verify bucket exists
if ! aws s3api head-bucket --bucket "$BUCKET_NAME" >/dev/null 2>&1; then
  echo "❌ Bucket '$BUCKET_NAME' does not exist or you lack permissions." >&2
  exit 1
fi

# 2) Sync all non-empty files via aws s3 sync
#    This command preserves directory structure and uploads files.
aws s3 sync "$FrontendDir" "s3://$BUCKET_NAME/"

echo "Creating placeholders for empty directories (if any)..." >&2

# 3) Create zero-byte objects for directories that contain no files
while IFS= read -r dir; do
  # Skip the top-level frontend directory
  relpath="${dir#$FrontendDir/}"
  if [ "$relpath" == "" ]; then
    continue
  fi

  # Check if directory contains any files or non-empty subdirectories
  if find "$dir" -mindepth 1 | grep -q .; then
    # Directory is not empty; skip
    continue
  fi
  # Append trailing slash for S3 “folder”
  s3key="${relpath%/}/"

  echo "  • Creating empty folder object: $s3key" >&2
  aws s3api put-object \
    --bucket "$BUCKET_NAME" \
    --key "$s3key" \
    >/dev/null

done < <(find "$FrontendDir" -type d)

echo "✅ Frontend deployment to s3://$BUCKET_NAME/ complete." >&2
