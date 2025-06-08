#!/usr/bin/env bash
#
# update-cognito-callback.sh (silenced AWS CLI output)
#
# Usage: ./update-cognito-callback.sh <ENV>
#
# After deploying frontend and Cognito, updates the Cognito User Pool Client
# to point its callback URL at the newly synced S3 bucket's callback.html.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "❌ Usage: $0 <ENV>"
  exit 1
fi

ENV="$1"
# Silently get AWS region, default to us-east-1
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
S3_STACK_NAME="${ENV}-kashishop-s3"
COGNITO_STACK_NAME="${ENV}-kashishop-cognito"

# Fetch the Kashishop2BucketName output via DescribeStacks (silent)
SITE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='Kashishop2BucketName'].OutputValue | [0]" \
  --output text --region "${REGION}" 2>/dev/null)

SITE_URL="https://${SITE_BUCKET}.s3.${REGION}.amazonaws.com/main/callback.html"
echo "🔗 Setting Cognito callback URL to: ${SITE_URL}"

# Retrieve User Pool ID (silent)
UP_ID=$(aws cloudformation describe-stacks \
  --stack-name "${COGNITO_STACK_NAME}" \
  --query "Stacks[0].Outputs[?contains(OutputKey,'UserPoolId')].OutputValue | [0]" \
  --output text --region "${REGION}" 2>/dev/null)
if [[ -z "${UP_ID}" || "${UP_ID}" == "None" ]]; then
  echo "❌ Could not find UserPoolId in stack ${COGNITO_STACK_NAME}."
  exit 1
fi

# Retrieve the first User Pool Client ID (silent)
CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
  --user-pool-id "${UP_ID}" \
  --max-results 1 \
  --query "UserPoolClients[0].ClientId" \
  --output text --region "${REGION}" 2>/dev/null)
if [[ -z "${CLIENT_ID}" || "${CLIENT_ID}" == "None" ]]; then
  echo "❌ No User Pool Clients found for UserPool ${UP_ID}."
  exit 1
fi

# Update the callback URL on the user pool client (silent)
aws cognito-idp update-user-pool-client \
  --user-pool-id "${UP_ID}" \
  --client-id "${CLIENT_ID}" \
  --callback-urls "${SITE_URL}" \
  --region "${REGION}" >/dev/null 2>&1

echo "✅ Cognito callback URL updated successfully."
