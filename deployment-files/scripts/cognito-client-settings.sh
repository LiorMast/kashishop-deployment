#!/usr/bin/env bash
#
# configure-cognito-app-client.sh
# Enhanced to ensure the App Client has a secret and uses Basic Auth for token exchange
# Robustly finds client even if CF outputs stale, suppresses extraneous output.
#
# Usage: ./configure-cognito-app-client.sh <ENV> [REGION]

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "❌ Usage: $0 <ENV> [REGION]"
  exit 1
fi

ENV="$1"
REGION="${2:-us-east-1}"
export AWS_PAGER=""

COGNITO_STACK_NAME="${ENV}-kashishop-cognito"
S3_STACK_NAME="${ENV}-kashishop-s3"
CLIENT_NAME="${ENV}-kashishop-client"

# 1️⃣ Fetch User Pool ID
USER_POOL_ID=$(aws --no-cli-pager cloudformation describe-stacks \
  --stack-name "${COGNITO_STACK_NAME}" \
  --query "Stacks[0].Outputs[?ends_with(OutputKey,'UserPoolId')].OutputValue | [0]" \
  --output text --region "${REGION}")

# 2️⃣ Attempt to fetch App Client ID from CF outputs
APP_CLIENT_ID=$(aws --no-cli-pager cloudformation describe-stacks \
  --stack-name "${COGNITO_STACK_NAME}" \
  --query "Stacks[0].Outputs[?ends_with(OutputKey,'UserPoolClientId')].OutputValue | [0]" \
  --output text --region "${REGION}")

# 3️⃣ Fallback to list-user-pool-clients if needed
if [[ -z "${APP_CLIENT_ID}" || "${APP_CLIENT_ID}" == "None" ]]; then
  echo "⚠️ CF outputs missing App Client ID; falling back to list-user-pool-clients..."
  APP_CLIENT_ID=$(aws --no-cli-pager cognito-idp list-user-pool-clients \
    --user-pool-id "${USER_POOL_ID}" \
    --max-results 60 \
    --query "UserPoolClients[?contains(ClientName, '${CLIENT_NAME}')].ClientId | [0]" \
    --output text --region "${REGION}")
fi

# 4️⃣ Determine Redirect URI
SITE_BUCKET=$(aws --no-cli-pager cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='Kashishop2BucketName'].OutputValue | [0]" \
  --output text --region "${REGION}")
REDIRECT_URI="https://${SITE_BUCKET}.s3.${REGION}.amazonaws.com/main/callback.html"

# 5️⃣ Check if client secret exists
set +e
CLIENT_SECRET=$(aws --no-cli-pager cognito-idp describe-user-pool-client \
  --user-pool-id "${USER_POOL_ID}" \
  --client-id "${APP_CLIENT_ID}" \
  --region "${REGION}" \
  --query "UserPoolClient.ClientSecret" \
  --output text 2>/dev/null)
DESCRIBE_STATUS=$?
set -e

# 6️⃣ Recreate client if no secret or error
if [[ ${DESCRIBE_STATUS} -ne 0 || -z "${CLIENT_SECRET}" || "${CLIENT_SECRET}" == "None" ]]; then
  echo "⚠️ No valid client secret; recreating App Client with secret..."
  aws --no-cli-pager cognito-idp delete-user-pool-client \
    --user-pool-id "${USER_POOL_ID}" \
    --client-id "${APP_CLIENT_ID}" \
    --region "${REGION}" > /dev/null 2>&1

  CREATE_JSON=$(aws --no-cli-pager cognito-idp create-user-pool-client \
    --user-pool-id "${USER_POOL_ID}" \
    --client-name "${CLIENT_NAME}" \
    --generate-secret \
    --allowed-o-auth-flows code \
    --allowed-o-auth-flows-user-pool-client \
    --allowed-o-auth-scopes openid email \
    --callback-urls "${REDIRECT_URI}" \
    --prevent-user-existence-errors ENABLED \
    --region "${REGION}")

  APP_CLIENT_ID=$(echo "$CREATE_JSON" | jq -r '.UserPoolClient.ClientId')
  CLIENT_SECRET=$(echo "$CREATE_JSON" | jq -r '.UserPoolClient.ClientSecret')
  echo "   ✓ Recreated client: ID=${APP_CLIENT_ID}, Secret=${CLIENT_SECRET}"
else
  echo "   ✓ Existing client secret: ${CLIENT_SECRET:0:4}..."
fi

echo "----------------------------------------------------------------------"

# 7️⃣ Update OAuth settings on client silently
aws --no-cli-pager cognito-idp update-user-pool-client \
  --user-pool-id "${USER_POOL_ID}" \
  --client-id "${APP_CLIENT_ID}" \
  --supported-identity-providers COGNITO \
  --allowed-o-auth-flows code \
  --allowed-o-auth-flows-user-pool-client \
  --allowed-o-auth-scopes openid email \
  --callback-urls "${REDIRECT_URI}" \
  --prevent-user-existence-errors ENABLED \
  --region "${REGION}" > /dev/null 2>&1

echo "✅ App Client configured with secret (ID=${APP_CLIENT_ID})."
