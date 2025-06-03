#!/usr/bin/env bash
#
# deploy-frontend.sh
#
# This script syncs everything under ./frontend/ into the S3 bucket
# created by the CloudFormation template: <EnvPrefix>-kashishop-frontend.
# It will also explicitly create any “empty” folders that exist in ./frontend/.
#
# Usage:
#   chmod +x deploy-frontend.sh
#   ./deploy-frontend.sh <EnvPrefix>
#
# Example:
#   ./deploy-frontend.sh dev
#
# Requirements:
#  • AWS CLI v2 (configured with credentials & region)
#  • The CFN stack for core infrastructure (including S3 bucket) must be CREATE_COMPLETE.
#
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <EnvPrefix>"
  exit 1
fi

EnvPrefix="$1"
BucketName="${EnvPrefix}-kashishop-frontend"
FrontendDir="$(pwd)/frontend"

if [ ! -d "$FrontendDir" ]; then
  echo "❌ Directory '$FrontendDir' not found. Ensure you run from repo root and have a 'frontend/' folder."
  exit 1
fi

echo "Deploying 'frontend/' contents into S3 bucket: $BucketName" >&2

# 1) Verify bucket exists
if ! aws s3api head-bucket --bucket "$BucketName" >/dev/null 2>&1; then
  echo "❌ Bucket '$BucketName' does not exist or you lack permissions." >&2
  exit 1
fi

# 2) Upload all non-empty files via aws s3 sync
#    This command preserves directory structure and uploads files.
#
aws s3 sync "$FrontendDir" "s3://$BucketName/" --acl public-read

# 3) Explicitly create “folders” for any directories in ./frontend that are empty.
#    AWS S3 has a flat namespace, so we create a zero-byte object with trailing slash.
#
echo "Creating placeholders for empty directories (if any)..." >&2

# Find all directories under ./frontend
while IFS= read -r dir; do
  # Check if directory contains any files
  if find "$dir" -maxdepth 1 -type f | read -r _; then
    # Directory has at least one file; skip
    continue
  fi

  # Compute the relative path from frontend/
  relpath="${dir#$FrontendDir/}"
  # Append a trailing slash for S3 “folder”
  s3key="${relpath%/}/"

  echo "  • Creating empty folder: $s3key" >&2
  aws s3api put-object \
    --bucket "$BucketName" \
    --key "$s3key" \
    --acl public-read \
    --body /dev/null >/dev/null

done < <(find "$FrontendDir" -type d)

echo "✅ Frontend deployment to s3://$BucketName/ complete." >&2
