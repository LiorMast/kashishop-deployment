#!/usr/bin/env bash
#
# update-cognito-callback.sh
#
# Usage: ./update-cognito-callback.sh <ENV>
#
# After deploying frontend and Cognito, update the Cognito User Pool Client
# to point its callback URL at the newly synced S3 bucket's callback.html.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "❌ Usage: $0 <ENV>"
  exit 1
fi

ENV="$1"
REGION=$(aws configure get region || echo "us-east-1")
S3_STACK_NAME="${ENV}-kashishop-s3"
COGNITO_STACK_NAME="${ENV}-kashishop-cognito"

# Fetch WebsiteBucket output from S3 stack
SITE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucket'].OutputValue" \
  --output text --region "${REGION}")
if [[ -z "${SITE_BUCKET}" ]]; then
  echo "❌ Could not find WebsiteBucket in stack ${S3_STACK_NAME}."
  exit 1
fi

SITE_URL="https://${SITE_BUCKET}.s3.${REGION}.amazonaws.com/main/callback.html"
echo "🔗 Setting Cognito callback URL to: ${SITE_URL}"

# Retrieve User Pool ID
UP_ID=$(aws cloudformation describe-stacks \
  --stack-name "${COGNITO_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text --region "${REGION}")
if [[ -z "${UP_ID}" ]]; then
  echo "❌ Could not find UserPoolId in stack ${COGNITO_STACK_NAME}."
  exit 1
fi

echo "🆔 User Pool ID: ${UP_ID}"

# Retrieve first User Pool Client ID
CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
  --user-pool-id "${UP_ID}" \
  --max-results 1 \
  --query "UserPoolClients[0].ClientId" \
  --output text --region "${REGION}")
if [[ -z "${CLIENT_ID}" || "${CLIENT_ID}" == "None" ]]; then
  echo "❌ No User Pool Clients found for UserPool ${UP_ID}."
  exit 1
fi

echo "🔑 Updating Client ID: ${CLIENT_ID}"
# Update the callback URL on the user pool client
aws cognito-idp update-user-pool-client \
  --user-pool-id "${UP_ID}" \
  --client-id "${CLIENT_ID}" \
  --callback-urls "${SITE_URL}" \
  --region "${REGION}"

echo "✅ Cognito callback URL updated successfully."
