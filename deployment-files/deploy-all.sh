#!/usr/bin/env bash
#
# deploy-all.sh (updated to include CORS enablement with API_ID extraction)
#
# Usage: ./scripts/deploy-all.sh <ENV>
#
# Performs end-to-end deployment for Kashishop:
#   1. Print AWS caller identity & environment info
#   2. Ensure helper scripts are in Unix format & executable
#   3. Deploy core CloudFormation stack (Cognito, etc.)
#   4. Deploy DynamoDB tables via dynamodb-template
#   5. Deploy S3 buckets via s3-template
#   6. Deploy all Lambda functions
#   7. Deploy API Gateway stack (ensuring S3 bucket for large templates)
#   7.5. Enable CORS on all API Gateway resources by looking up API by name, extracting pure ID if needed
#   8. Update front-end JS with new API endpoint
#   9. Sync frontend files to S3
#  10. Print important outputs (Website URL, API ID)
#
# Example:
#   chmod +x scripts/deploy-all.sh
#   ./scripts/deploy-all.sh dev
#
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "❌ Usage: $0 <ENV>"
  exit 1
fi

ENV="$1"
CORE_STACK_NAME="${ENV}-kashishop-core"
DYNAMO_STACK_NAME="${ENV}-kashishop-dynamo"
S3_STACK_NAME="${ENV}-kashishop-s3"
API_STACK_NAME="${ENV}-kashishop-api"
TEMPLATE_DIR="$(pwd)/templates"
SCRIPTS_DIR="$(pwd)/scripts"
FRONTEND_DIR="$(pwd)/frontend"
LAMBDA_SCRIPT="${SCRIPTS_DIR}/deploy-lambda.sh"
UPDATE_API_SCRIPT="${SCRIPTS_DIR}/update-api-endpoint.sh"
FRONTEND_SCRIPT="${SCRIPTS_DIR}/deploy-frontend.sh"
CORE_TEMPLATE="${TEMPLATE_DIR}/main-template.yaml"
DYNAMO_TEMPLATE="${TEMPLATE_DIR}/dynamodb-template.yaml"
S3_TEMPLATE="${TEMPLATE_DIR}/s3-template.yaml"
API_TEMPLATE="${TEMPLATE_DIR}/api-gateway-template.yaml"
# New enable CORS script (assumed to be placed in scripts/)
ENABLE_CORS_SCRIPT="${SCRIPTS_DIR}/enable-cors-apigw.py"
TEMPLATE_BUCKET="${ENV}-kashishop-templates"

echo "🌐 Environment: ${ENV}"
echo

#
# 1️⃣ AWS Identity & Region/Account Info
#
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
echo -e "
🚩 Using AWS Account: ${ACCOUNT_ID}, Region: ${REGION}"
echo

#
# 2️⃣ Normalize & chmod helper scripts
#
echo "🔄 Converting helper scripts to Unix format & making executable..."
for script in "${SCRIPTS_DIR}"/*.sh; do
  if [[ -f "$script" ]]; then
    dos2unix "$script" 2>/dev/null || true
    chmod +x "$script"
    echo "  • $script"
  fi
done
# Ensure the new enable CORS script is executable
if [[ -f "${ENABLE_CORS_SCRIPT}" ]]; then
  chmod +x "${ENABLE_CORS_SCRIPT}"
  echo "  • ${ENABLE_CORS_SCRIPT}"
fi
echo

#
# 3️⃣ Deploy Core CloudFormation Stack
#

echo "⛅ Deploying Core Stack: ${CORE_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${CORE_TEMPLATE}" \
  --stack-name "${CORE_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ Core Stack deployed."
echo

#
# 4️⃣ Deploy DynamoDB Tables
#

echo "📦 Deploying DynamoDB Tables Stack: ${DYNAMO_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${DYNAMO_TEMPLATE}" \
  --stack-name "${DYNAMO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ DynamoDB Tables deployed."
echo

#
# 5️⃣ Deploy S3 Buckets
#

echo "📦 Deploying S3 Buckets Stack: ${S3_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${S3_TEMPLATE}" \
  --stack-name "${S3_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ S3 Buckets deployed."
echo

#
# 6️⃣ Deploy Lambda Functions
#

echo "🛠️  Deploying Lambda functions..."
"${LAMBDA_SCRIPT}" "${ENV}"
echo "✅ Lambdas deployed."
echo

#
# 7️⃣ Deploy API Gateway Stack (ensure S3 bucket exists)
#

echo "🚀 Deploying API Gateway Stack: ${API_STACK_NAME}"
# Check if the S3 bucket for templates exists
if ! aws s3api head-bucket --bucket "${TEMPLATE_BUCKET}" 2>/dev/null; then
  echo "🔨 S3 bucket '${TEMPLATE_BUCKET}' does not exist. Creating it..."
  aws s3 mb "s3://${TEMPLATE_BUCKET}" --region "${REGION}"
fi
# Deploy with --s3-bucket to support large templates
aws cloudformation deploy \
  --template-file "${API_TEMPLATE}" \
  --stack-name "${API_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}" \
  --s3-bucket "${TEMPLATE_BUCKET}"
echo "✅ API Gateway Stack deployed."
echo

#
# 7️⃣.5️⃣ Enable CORS on API Gateway resources
#
# Fetch the REST API ID by name (as it's not output in the CF stack)
API_NAME="${ENV}Kashishop2API"
RAW_API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='${API_NAME}'].id" \
  --output text --region "${REGION}")
API_ID="${RAW_API_ID}"
# If RAW_API_ID contains a full URL (starts with https://), extract the pure API ID
if [[ "${API_ID}" == https://* ]]; then
  PURE_ID=$(echo "${API_ID}" | sed -E 's|https://([^.]+).*$|\1|')
  API_ID="${PURE_ID}"
fi

if [[ -n "${API_ID}" && -f "${ENABLE_CORS_SCRIPT}" ]]; then
  echo "🔧 Enabling CORS on API Gateway resources for API ID: ${API_ID} (stage: ${ENV})"
  python3 "${ENABLE_CORS_SCRIPT}" --api-id "${API_ID}" --region "${REGION}" --stage "${ENV}"
  echo "✅ CORS enabled on API Gateway resources."
else
  echo "⚠️  Skipped CORS enablement: API_ID not found or script missing."
fi
echo

#
# 8️⃣ Update Frontend JS with new API endpoint
#

echo "🔄 Updating frontend JS with API endpoint..."
"${UPDATE_API_SCRIPT}" "${ENV}"
echo "✅ API endpoint updated in global.js."
echo

#
# 9️⃣ Sync Frontend to S3
#

echo "📦 Syncing frontend files to S3..."
"${FRONTEND_SCRIPT}" "${ENV}"
echo "✅ Frontend synced."
echo

#
# 🔟 Print Key Outputs
#

echo "📢 Deployment complete for environment: ${ENV}"
echo

# Retrieve Website URL from Core Stack outputs
WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name "${CORE_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteURL'].OutputValue" \
  --output text --region "${REGION}")

if [[ -n "${WEBSITE_URL}" ]]; then
  echo "🌐 Frontend Website URL: ${WEBSITE_URL}"
fi

# Retrieve API ID (again, for display)
API_ID_DISPLAY="${API_ID}"
if [[ -n "${API_ID_DISPLAY}" ]]; then
  echo "🛣️  API Gateway ID: ${API_ID_DISPLAY}"
  echo "   Invoke URL (stage: ${ENV}): https://${API_ID_DISPLAY}.execute-api.${REGION}.amazonaws.com/${ENV}"
fi

echo
 echo "🎉 All resources for '${ENV}' have been provisioned and deployed!"
