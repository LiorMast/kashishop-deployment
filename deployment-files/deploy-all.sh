#!/usr/bin/env bash
#
# deploy-all.sh (updated to deploy Cognito stack and call external callback updater)
#
# Usage: ./deploy-all.sh <ENV>
#
# Performs end-to-end deployment for Kashishop:
#   1. Print AWS caller identity & environment info
#   2. Ensure helper scripts are Unix format & executable
#   3. Deploy core CloudFormation stack (skipped in this version for brevity, usually part of full setup)
#   4. Deploy DynamoDB tables
#   5. Deploy S3 buckets
#   6. Deploy Cognito resources
#   7. Deploy all Lambda functions
#   8. Sync frontend files to S3 (this is now after API update)
#   9. Update Cognito callback URL via external script
#  10. Configure Cognito App Client Core Settings (NEW)
#  11. Deploy Cognito Managed Branding via Python script
#  12. Deploy API Gateway stack
#  13. Enable CORS on API Gateway resources
#  14. Print Frontend URL

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "❌ Usage: $0 <ENV>"
  exit 1
fi

ENV="$1"
CORE_STACK_NAME="${ENV}-kashishop-core"
DYNAMO_STACK_NAME="${ENV}-kashishop-dynamo"
S3_STACK_NAME="${ENV}-kashishop-s3"
COGNITO_STACK_NAME="${ENV}-kashishop-cognito"
API_STACK_NAME="${ENV}-kashishop-api"
TEMPLATE_DIR="$(pwd)/templates"
SCRIPTS_DIR="$(pwd)/scripts"
LAMBDA_SCRIPT="${SCRIPTS_DIR}/deploy-lambda.sh"
UPDATE_COGNITO_SCRIPT="${SCRIPTS_DIR}/update-cognito-callback.sh"
UPDATE_API_SCRIPT="${SCRIPTS_DIR}/update-api-endpoint.sh"
DEPLOY_FRONTEND_SCRIPT="${SCRIPTS_DIR}/deploy-frontend.sh"
ENABLE_CORS_SCRIPT="${SCRIPTS_DIR}/enable-cors-apigw.py"
COGNITO_BRANDING_SCRIPT="${SCRIPTS_DIR}/configure_cognito_branding.py" # Path to your Python branding script
COGNITO_APP_CLIENT_CONFIG_SCRIPT="${SCRIPTS_DIR}/cognito-client-settings.sh" # Path to your new Bash script
COGNITO_FULL_JSON_PATH="$(pwd)/cognito_full.json" # Assumes cognito_full.json is in the project root
TEMPLATE_BUCKET="${ENV}-kashishop-templates"

# 1️⃣ AWS Identity & Region/Account Info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
echo "🚩 AWS Account: ${ACCOUNT_ID}, Region: ${REGION}"

# 2️⃣ Normalize helper scripts & make executable
echo
echo " 🛠️ Normalizing helper scripts & making executable:"
for script in "${SCRIPTS_DIR}"/*.sh; do
  [[ -f "$script" ]] || continue
  dos2unix "$script" 2>/dev/null || true
  chmod +x "$script"
  echo "    • $script"
done
[[ -f "${ENABLE_CORS_SCRIPT}" ]] && chmod +x "${ENABLE_CORS_SCRIPT}" && echo "    • ${ENABLE_CORS_SCRIPT}"
[[ -f "${COGNITO_BRANDING_SCRIPT}" ]] && chmod +x "${COGNITO_BRANDING_SCRIPT}" && echo "    • ${COGNITO_BRANDING_SCRIPT}"
[[ -f "${COGNITO_APP_CLIENT_CONFIG_SCRIPT}" ]] && chmod +x "${COGNITO_APP_CLIENT_CONFIG_SCRIPT}" && echo "    • ${COGNITO_APP_CLIENT_CONFIG_SCRIPT}"


# # 4️⃣ Deploy DynamoDB Stack
echo "📦 Deploying DynamoDB Stack: ${DYNAMO_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/dynamodb-template.yaml" \
  --stack-name "${DYNAMO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ DynamoDB Stack deployed."

# 5️⃣ Deploy S3 Stack
echo "📦 Deploying S3 Stack: ${S3_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/s3-template.yaml" \
  --stack-name "${S3_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ S3 Stack deployed."

# 6️⃣ Deploy Cognito Stack
echo "🔐 Deploying Cognito Stack: ${COGNITO_STACK_NAME}"
# — ensure the template bucket exists
if ! aws s3api head-bucket --bucket "${TEMPLATE_BUCKET}" 2>/dev/null; then
  aws s3 mb "s3://${TEMPLATE_BUCKET}" --region "${REGION}"
fi
# — deploy via S3 to work around the 51 200 byte limit
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/cognito-template.yaml" \
  --stack-name "${COGNITO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}" \
  --s3-bucket "${TEMPLATE_BUCKET}"
echo "✅ Cognito Stack deployed."


# # 7️⃣ Deploy Lambda functions
echo "🛠️ Deploying Lambdas..."
"${LAMBDA_SCRIPT}" "${ENV}"
echo "✅ Lambdas deployed."

# 8️⃣ Sync frontend to S3
echo "🔄 Syncing frontend files to S3 (moved earlier)..."
"${DEPLOY_FRONTEND_SCRIPT}" "${ENV}"
echo "✅ Frontend synced."

# 9️⃣ Update Cognito callback URL
echo "🔄 Updating Cognito callback URL via external script..."
"${UPDATE_COGNITO_SCRIPT}" "${ENV}"
echo "✅ Cognito callback updated."

# 🔟 Configure Cognito App Client Core Settings
echo "⚙️  Configuring Cognito App Client core settings (IDPs, OAuth, Scopes)..."
# Pass the environment and region to the new script
"${COGNITO_APP_CLIENT_CONFIG_SCRIPT}" "${ENV}" "${REGION}"
echo "✅ Cognito App Client core settings applied."

# 1️⃣1️⃣ Deploy Cognito Managed Branding via Python script
echo "🎨 Deploying Cognito Managed Branding..."

# Fetch the Kashishop2BucketName output from S3 stack for branding assets
S3_BUCKET_FOR_BRANDING=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='Kashishop2BucketName'].OutputValue | [0]" \
  --output text --region "${REGION}")

if [[ -z "${S3_BUCKET_FOR_BRANDING}" || "${S3_BUCKET_FOR_BRANDING}" == "None" ]]; then
  echo "❌ Could not find S3 bucket name 'Kashishop2BucketName' from stack ${S3_STACK_NAME}."
  echo "   Skipping Cognito Managed Branding deployment."
else
  # Check if python3 is available
  if ! command -v python3 &> /dev/null
  then
      echo "❌ 'python3' command not found. Skipping Cognito Managed Branding deployment."
      echo "   Please install Python 3 to run the branding script."
  else
      # Run the Python script to apply branding
      python3 "${COGNITO_BRANDING_SCRIPT}" "${COGNITO_FULL_JSON_PATH}" "${REGION}" "${S3_BUCKET_FOR_BRANDING}" "${ENV}"
      echo "✅ Cognito Managed Branding deployment initiated."
  fi
fi


# 1️⃣2️⃣ Deploy API Gateway Stack
echo "🚀 Deploying API Gateway Stack: ${API_STACK_NAME}"
if ! aws s3api head-bucket --bucket "${TEMPLATE_BUCKET}" 2>/dev/null; then
  aws s3 mb "s3://${TEMPLATE_BUCKET}" --region "${REGION}"
fi
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/api-gateway-template.yaml" \
  --stack-name "${API_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}" \
  --s3-bucket "${TEMPLATE_BUCKET}"
echo "✅ API Gateway Stack deployed."

# 1️⃣3️⃣ Enable CORS on API Gateway
API_NAME="${ENV}Kashishop2API"
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${API_NAME}'].id" --output text --region "${REGION}")
if [[ -n "${API_ID}" && -f "${ENABLE_CORS_SCRIPT}" ]]; then
  python3 "${ENABLE_CORS_SCRIPT}" --api-id "${API_ID}" --region "${REGION}" --stage "${ENV}"
fi

#
# Update Frontend JS with new API endpoint (re-ordered for clarity)
#
echo "🔄 Updating frontend JS with API endpoint..."
"${UPDATE_API_SCRIPT}" "${ENV}" "${API_ID}"
echo "✅ API endpoint updated in global.js."
echo

# 1️⃣4️⃣ Print Frontend URL
# Note: BUCKET_NAME should be the same as S3_BUCKET_FOR_BRANDING
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'BucketName')].OutputValue | [0]"\
  --output text --region "${REGION}")

  # 🆕 Deploy login.html to S3 as Cognito login landing page
LOGIN_SCRIPT="${SCRIPTS_DIR}/deploy-login.sh"
if [[ -x "$LOGIN_SCRIPT" ]]; then
  echo "🚪 Deploying Cognito login page (login.html)..."

  # Extract app client ID and redirect URI
# Fetch the User Pool ID from CFN stack outputs (the OutputKey ending in 'UserPoolId')
USER_POOL_ID=$(
  aws cloudformation describe-stacks \
    --stack-name "$COGNITO_STACK_NAME" \
    --region     "$REGION" \
    --query      "Stacks[0].Outputs[?ends_with(OutputKey, \`UserPoolId\`)].OutputValue" \
    --output     text
)

# Fetch the App Client ID from CFN stack outputs (the OutputKey ending in 'UserPoolClientId')
APP_CLIENT_ID=$(
  aws cloudformation describe-stacks \
    --stack-name "$COGNITO_STACK_NAME" \
    --region     "$REGION" \
    --query      "Stacks[0].Outputs[?ends_with(OutputKey, \`UserPoolClientId\`)].OutputValue" \
    --output     text
)

echo "User Pool ID: $USER_POOL_ID"
echo "App Client ID: $APP_CLIENT_ID"


  # Redirect URI should match what was configured in the callback update script
  REDIRECT_URI="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/main/callback.html"

  "$LOGIN_SCRIPT" "$APP_CLIENT_ID" "$BUCKET_NAME" "$REGION" "$REDIRECT_URI"

  echo "✅ Login page deployed to:"
  echo "   http://${BUCKET_NAME}.s3-website.${REGION}.amazonaws.com/login.html"
else
  echo "⚠️ Warning: login deployment script not found at ${LOGIN_SCRIPT}"
fi

if [[ -n "${BUCKET_NAME}" ]]; then
  FRONTEND_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/main/index.html"
  echo "🌐 Frontend Website URL: ${FRONTEND_URL}"
fi

 echo "🎉 All resources for '${ENV}' have been provisioned and deployed!"
