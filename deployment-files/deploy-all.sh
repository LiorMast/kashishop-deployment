#!/usr/bin/env bash
#
# deploy-all.sh (updated to deploy Cognito stack and call external callback updater)
#
# Usage: ./deploy-all.sh <ENV>
#
# Performs end-to-end deployment for Kashishop:
#   1. Print AWS caller identity & environment info
#   2. Ensure helper scripts are Unix format & executable
#   3. Deploy DynamoDB tables
#   4. Deploy S3 buckets
#   5. Deploy Cognito resources
#   6. Deploy API Gateway stack
#   7. Deploy all Lambda functions
#   8. Update Cognito callback URL via external script
#   9. Configure Cognito App Client Core Settings (NEW)
#  10. Deploy Cognito Managed Branding via Python script
#  11. Create Admin User (NEW)
#  12. Enable CORS on API Gateway resources
#  13. Update Frontend JS with new API endpoint
#  14. Update Login Button URL (NEW)
#  15. Sync frontend files to S3
#  16. Deploy login.html to S3
#  17. Print Frontend URL

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
API_STACK_NAME="${ENV}-kashishop-api" # Corrected API stack name
TEMPLATE_DIR="$(pwd)/templates"
SCRIPTS_DIR="$(pwd)/scripts"
LAMBDA_SCRIPT="${SCRIPTS_DIR}/deploy-lambda.sh"
UPDATE_COGNITO_SCRIPT="${SCRIPTS_DIR}/update-cognito-callback.sh"
UPDATE_API_SCRIPT="${SCRIPTS_DIR}/update-api-endpoint.sh"
DEPLOY_FRONTEND_SCRIPT="${SCRIPTS_DIR}/deploy-frontend.sh"
ENABLE_CORS_SCRIPT="${SCRIPTS_DIR}/enable-cors-apigw.py"
COGNITO_BRANDING_SCRIPT="${SCRIPTS_DIR}/configure-login.py" # Path to your Python branding script
COGNITO_APP_CLIENT_CONFIG_SCRIPT="${SCRIPTS_DIR}/cognito-client-settings.sh" # Path to your App Client configuration Bash script
SETUP_ADMIN_SCRIPT="${SCRIPTS_DIR}/setup-admin.sh" # Path to your setup-admin.sh script
UPDATE_LOGIN_BUTTON_SCRIPT="${SCRIPTS_DIR}/update-login-button.py" # Path to the new login button update script
COGNITO_FULL_JSON_PATH="$(pwd)/../cognito_full.json" # Assumes cognito_full.json is in the project root
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
[[ -f "${SETUP_ADMIN_SCRIPT}" ]] && chmod +x "${SETUP_ADMIN_SCRIPT}" && echo "    • ${SETUP_ADMIN_SCRIPT}"
[[ -f "${UPDATE_LOGIN_BUTTON_SCRIPT}" ]] && chmod +x "${UPDATE_LOGIN_BUTTON_SCRIPT}" && echo "    • ${UPDATE_LOGIN_BUTTON_SCRIPT}"


# 3️⃣ Deploy DynamoDB Stack
echo "📦 Deploying DynamoDB Stack: ${DYNAMO_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/dynamodb-template.yaml" \
  --stack-name "${DYNAMO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ DynamoDB Stack deployed."

# 4️⃣ Deploy S3 Stack
echo "📦 Deploying S3 Stack: ${S3_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/s3-template.yaml" \
  --stack-name "${S3_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ S3 Stack deployed."

# 5️⃣ Deploy Cognito Stack
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

# 6️⃣ Deploy API Gateway Stack (MOVED UP)
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

# 7️⃣ Deploy Lambda functions
echo "🛠️ Deploying Lambdas..."
"${LAMBDA_SCRIPT}" "${ENV}"
echo "✅ Lambdas deployed."

# 8️⃣ Update Cognito callback URL
echo "🔄 Updating Cognito callback URL via external script..."
"${UPDATE_COGNITO_SCRIPT}" "${ENV}"
echo "✅ Cognito callback updated."

# 9️⃣ Configure Cognito App Client Core Settings
echo "⚙️  Configuring Cognito App Client core settings (IDPs, OAuth, Scopes)..."
# Pass the environment and region to the new script
"${COGNITO_APP_CLIENT_CONFIG_SCRIPT}" "${ENV}" "${REGION}"
echo "✅ Cognito App Client core settings applied."

# 🔟 Deploy Cognito Managed Branding via Python script
echo "🎨 Deploying Cognito Managed Branding..."

# Fetch the Kashishop2BucketName output from S3 stack for branding assets
S3_BUCKET_FOR_BRANDING=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='Kashishop2BucketName'].OutputValue | [0]" \
  --output text --region "${REGION}")

LOGIN_PAGE_URL="" # Initialize variable to store the URL

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
      # Run the Python script to apply branding and capture its output (the login URL)
      # We redirect stderr to stdout (2>&1) and then grep for the specific URL line
      # from the script's output. The `tail -n 1` ensures we get the last line,
      # and `sed` extracts just the URL.
      python3 "${COGNITO_BRANDING_SCRIPT}" "${COGNITO_FULL_JSON_PATH}" "${REGION}" "${S3_BUCKET_FOR_BRANDING}" "${ENV}" 2>&1
      echo "✅ Cognito Managed Branding deployment initiated."
  fi
fi

# 1️⃣1️⃣ Create Admin User
echo "👤 Creating Admin User and configuring associated resources..."
# Note: setup-admin.sh expects ENV, and optionally ADMIN_USERNAME and ADMIN_PASSWORD
# If you want to customize admin credentials, pass them here.
# For now, using default 'admin' / 'Admin123!' as defined in setup-admin.sh
"${SETUP_ADMIN_SCRIPT}" "${ENV}" "admin" "Admin123!"
echo "✅ Admin user setup completed."

# 1️⃣2️⃣ Enable CORS on API Gateway
API_NAME="${ENV}Kashishop2API"
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${API_NAME}'].id" --output text --region "${REGION}")
if [[ -n "${API_ID}" && -f "${ENABLE_CORS_SCRIPT}" ]]; then
  python3 "${ENABLE_CORS_SCRIPT}" --api-id "${API_ID}" --region "${REGION}" --stage "${ENV}"
fi

# 1️⃣3️⃣ Update Frontend JS with new API endpoint (MOVED UP)
echo "🔄 Updating frontend JS with API endpoint..."
"${UPDATE_API_SCRIPT}" "${ENV}" "${API_ID}"
echo "✅ API endpoint updated in global.js."
echo

# 1️⃣4️⃣ Update Login Button URL (MOVED UP)
# echo "⬆️ Updating login button URL in global.js..."
# if [[ -n "${LOGIN_PAGE_URL}" && -x "${UPDATE_LOGIN_BUTTON_SCRIPT}" ]]; then
#     "${UPDATE_LOGIN_BUTTON_SCRIPT}" "${LOGIN_PAGE_URL}"
#     echo "✅ Login button URL updated."
# else
#     echo "⚠️ Skipping login button URL update. Either URL not found or script not executable."
# fi
echo

# 1️⃣5️⃣ Sync frontend files to S3 (MOVED DOWN)
echo "🔄 Syncing frontend files to S3..."
"${DEPLOY_FRONTEND_SCRIPT}" "${ENV}"
echo "✅ Frontend synced."

# 1️⃣7️⃣ Print Frontend URL
# Note: BUCKET_NAME should be the same as S3_BUCKET_FOR_BRANDING
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'BucketName')].OutputValue | [0]"\
  --output text --region "${REGION}")

if [[ -n "${BUCKET_NAME}" ]]; then
  FRONTEND_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/main/index.html"
  echo "🌐 Frontend Website URL: ${FRONTEND_URL}"
fi

 echo "🎉 All resources for '${ENV}' have been provisioned and deployed!"
