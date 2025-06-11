#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  cat <<USAGE
Usage: $0 <ENV> [<ADMIN_USERNAME> <ADMIN_PASSWORD>]

  <ENV>               : prefix used in deploy-all.sh (e.g. test, dev, prod)
  <ADMIN_USERNAME>    : (optional) username for admin (default: admin)
  <ADMIN_PASSWORD>    : (optional) password for admin (default: Admin123!)
USAGE
  exit 1
fi

ENV="$1"
# Change STACK_NAME to reference the API Gateway stack
API_STACK_NAME="${ENV}-kashishop-api" # This should match the API_STACK_NAME in deploy-all.sh
REGION=$(aws configure get region || echo "us-east-1")

ADMIN_USER="${2:-admin}"
ADMIN_PASS="${3:-Admin123!}"

echo "🔍 Looking up Cognito User Pool '${ENV}-kashishop-cognito'…"
# Changed query to match the UserPoolId output from the Cognito CloudFormation stack
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "${ENV}-kashishop-cognito" \
  --query "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolId')].OutputValue | [0]" \
  --output text --region "${REGION}")


if [[ -z "$USER_POOL_ID" ]]; then
  echo "❌ Could not find User Pool '${ENV}-kashishop-cognito' in region ${REGION}."
  exit 1
fi
echo "✅ UserPoolId = ${USER_POOL_ID}"

echo "🔍 Looking up Cognito App Client '${ENV}-kashishop-cognito' UserPoolClientId…"
# Changed query to match the UserPoolClientId output from the Cognito CloudFormation stack
COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "${ENV}-kashishop-cognito" \
  --query "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolClientId')].OutputValue | [0]" \
  --output text --region "${REGION}")


if [[ -z "$COGNITO_CLIENT_ID" ]]; then
  echo "❌ Could not find App Client ID in User Pool ${USER_POOL_ID} from stack outputs."
  exit 1
fi
echo "✅ Cognito App Client ID = ${COGNITO_CLIENT_ID}"

# 0️⃣ Ensure the App Client allows ADMIN_NO_SRP_AUTH and USER_PASSWORD_AUTH
echo "🛠️  Enabling ADMIN_NO_SRP_AUTH and USER_PASSWORD_AUTH on App Client…"
# The previous `cognito-client-settings.sh` already sets allowed-oauth-flows-user-pool-client
# and other flows. This step ensures ADMIN_NO_SRP_AUTH for `admin-initiate-auth`.
# FIX: Removed 'ADD' as it's not a valid flow for --explicit-auth-flows.
# The parameter expects a list of flow names directly.
aws cognito-idp update-user-pool-client \
  --user-pool-id    "$USER_POOL_ID" \
  --client-id       "$COGNITO_CLIENT_ID" \
  --explicit-auth-flows ADMIN_NO_SRP_AUTH USER_PASSWORD_AUTH \
  >/dev/null
echo "✅ Auth flows enabled on App Client"

# 1️⃣ Ensure 'admin' group exists
echo "👥 Ensuring group 'admin' exists…"
aws cognito-idp create-group \
  --user-pool-id "$USER_POOL_ID" \
  --group-name admin \
  --description "Admin group for upload pipeline" \
  >/dev/null 2>&1 || echo "ℹ️ Group 'admin' already exists"

# 2️⃣ Create or confirm admin user
if aws cognito-idp admin-get-user \
     --user-pool-id "$USER_POOL_ID" \
     --username "$ADMIN_USER" >/dev/null 2>&1; then
  echo "ℹ️ User '${ADMIN_USER}' already exists; skipping creation."
else
  echo "🔐 Creating user '${ADMIN_USER}'…"
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$ADMIN_USER" \
    --temporary-password "$ADMIN_PASS" \
    --message-action SUPPRESS \
    >/dev/null

  echo "🔄 Setting permanent password for '${ADMIN_USER}'…"
  aws cognito-idp admin-set-user-password \
    --user-pool-id "$USER_POOL_ID" \
    --username "$ADMIN_USER" \
    --password "$ADMIN_PASS" \
    --permanent
fi

# 3️⃣ Add user to admin group
echo "➕ Adding '${ADMIN_USER}' to group 'admin'…"
aws cognito-idp admin-add-user-to-group \
  --user-pool-id "$USER_POOL_ID" \
  --username "$ADMIN_USER" \
  --group-name admin \
  >/dev/null 2>&1 || echo "ℹ️ User already in group 'admin'"


