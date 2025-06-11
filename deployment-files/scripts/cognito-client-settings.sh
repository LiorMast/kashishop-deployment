#!/usr/bin/env bash
#
# configure-cognito-app-client.sh
#
# Usage: ./configure-cognito-app-client.sh <ENV> [REGION]
#
# Configures the essential settings for a Cognito User Pool App Client
# via AWS CLI, including Identity Providers, OAuth Grant Types,
# OpenID Connect Scopes, and dynamically determined Callback URLs.
# This script should be run AFTER the Cognito User Pool and S3 bucket
# have been deployed (e.g., after the deploy-all.sh script's initial phases).

set -euo pipefail

# Check for required arguments
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "❌ Usage: $0 <ENV> [REGION]"
  echo "  <ENV>: Your deployment environment (e.g., 'dev', 'prod')"
  echo "  [REGION]: (Optional) The AWS region where your resources are deployed (e.g., 'us-east-1'). Defaults to us-east-1 if not provided."
  exit 1
fi

ENV="$1"
# Set REGION: if $2 is provided, use it; otherwise, default to us-east-1
if [[ -n "$2" ]]; then
  REGION="$2"
else
  REGION="us-east-1"
fi


echo "⚙️  Configuring Cognito App Client settings for environment '${ENV}' in region '${REGION}'..."
echo "----------------------------------------------------------------------"

# Define CloudFormation stack names based on the environment
COGNITO_STACK_NAME="${ENV}-kashishop-cognito"
S3_STACK_NAME="${ENV}-kashishop-s3"

# --- Step 1: Fetch User Pool ID and App Client ID ---
echo "Retrieving User Pool ID and App Client ID from CloudFormation stack: ${COGNITO_STACK_NAME}..."
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "${COGNITO_STACK_NAME}" \
  --query "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolId')].OutputValue | [0]" \
  --output text --region "${REGION}" 2>/dev/null || echo "NOT_FOUND")

APP_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "${COGNITO_STACK_NAME}" \
  --query "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolClientId')].OutputValue | [0]" \
  --output text --region "${REGION}" 2>/dev/null || echo "NOT_FOUND")

if [[ "${USER_POOL_ID}" == "NOT_FOUND" || -z "${USER_POOL_ID}" ]]; then
  echo "❌ Error: Could not find User Pool ID in stack '${COGNITO_STACK_NAME}'. Is the stack deployed?"
  exit 1
fi

if [[ "${APP_CLIENT_ID}" == "NOT_FOUND" || -z "${APP_CLIENT_ID}" ]]; then
  echo "❌ Error: Could not find App Client ID in stack '${COGNITO_STACK_NAME}'. Is the stack deployed?"
  exit 1
fi

echo "   ✓ User Pool ID:    ${USER_POOL_ID}"
echo "   ✓ App Client ID:   ${APP_CLIENT_ID}"
echo "----------------------------------------------------------------------"

# --- Step 2: Dynamically determine Callback URI ---
echo "Determining Redirect URI from S3 CloudFormation stack: ${S3_STACK_NAME}..."
SITE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='Kashishop2BucketName'].OutputValue | [0]" \
  --output text --region "${REGION}" 2>/dev/null || echo "NOT_FOUND")

if [[ "${SITE_BUCKET}" == "NOT_FOUND" || -z "${SITE_BUCKET}" ]]; then
  echo "❌ Error: Could not find 'Kashishop2BucketName' output in stack '${S3_STACK_NAME}'. Is the S3 stack deployed?"
  exit 1
fi

REDIRECT_URI="https://${SITE_BUCKET}.s3.${REGION}.amazonaws.com/main/callback.html"
echo "   ✓ Redirect URI:    ${REDIRECT_URI}"
echo "----------------------------------------------------------------------"

## --- Step 3: Apply App Client Settings using aws cognito-idp update-user-pool-client ---
echo "Applying App Client settings (Identity Providers, OAuth Flows, Scopes)..."

SUPPORTED_IDENTITY_PROVIDERS=("COGNITO")
ALLOWED_OAUTH_FLOWS=("code")
ALLOWED_OAUTH_SCOPES=("openid" "email")

set +e

aws cognito-idp update-user-pool-client \
  --user-pool-id "${USER_POOL_ID}" \
  --client-id "${APP_CLIENT_ID}" \
  --supported-identity-providers "${SUPPORTED_IDENTITY_PROVIDERS[@]}" \
  --allowed-o-auth-flows "${ALLOWED_OAUTH_FLOWS[@]}" \
  --allowed-o-auth-flows-user-pool-client \
  --allowed-o-auth-scopes "${ALLOWED_OAUTH_SCOPES[@]}" \
  --callback-urls "${REDIRECT_URI}" \
  --prevent-user-existence-errors ENABLED \
  --region "${REGION}"

CLI_EXIT_CODE=$?
set -e # Re-enable exit on error

if [[ ${CLI_EXIT_CODE} -eq 0 ]]; then
  echo "   ✅ Cognito App Client settings updated successfully!"
else
  echo "   ❌ Error updating Cognito App Client settings. AWS CLI command failed with exit code: ${CLI_EXIT_CODE}"
  # The output of the AWS command will now be visible directly in the console
  echo "      Please check the error messages above for details (from AWS CLI output)."
  echo "      Ensure your AWS credentials have sufficient permissions (cognito-idp:UpdateUserPoolClient)."
  exit 1
fi

echo "----------------------------------------------------------------------"
echo "🎉 Cognito App Client configuration completed."
echo "You can verify the settings in the AWS Cognito Console."
echo "----------------------------------------------------------------------"
