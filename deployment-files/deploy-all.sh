#!/usr/bin/env bash
#
# deploy-all.sh (updated to deploy Cognito stack)
#
# Usage: ./deploy-all.sh <ENV>
#
# Performs end-to-end deployment for Kashishop:
#   1. Print AWS caller identity & environment info
#   2. Ensure helper scripts are Unix format & executable
#   3. Deploy core CloudFormation stack
#   4. Deploy DynamoDB tables
#   5. Deploy S3 buckets
#   6. Deploy Cognito resources
#   7. Deploy all Lambda functions
#   8. Deploy API Gateway stack
#   8.5 Enable CORS on API Gateway resources
#   9. Sync frontend files to S3
#  10. Print important outputs (Frontend URL, API ID)

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
FRONTEND_DIR="$(pwd)/frontend"
LAMBDA_SCRIPT="${SCRIPTS_DIR}/deploy-lambda.sh"
UPDATE_API_SCRIPT="${SCRIPTS_DIR}/update-api-endpoint.sh"
FRONTEND_SCRIPT="${SCRIPTS_DIR}/deploy-frontend.sh"
CORE_TEMPLATE="${TEMPLATE_DIR}/main-template.yaml"
DYNAMO_TEMPLATE="${TEMPLATE_DIR}/dynamodb-template.yaml"
S3_TEMPLATE="${TEMPLATE_DIR}/s3-template.yaml"
COGNITO_TEMPLATE="${TEMPLATE_DIR}/cognito-template.yaml"
API_TEMPLATE="${TEMPLATE_DIR}/api-gateway-template.yaml"
ENABLE_CORS_SCRIPT="${SCRIPTS_DIR}/enable-cors-apigw.py"
TEMPLATE_BUCKET="${ENV}-kashishop-templates"

# 1️⃣ AWS Identity & Region/Account Info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
echo "🚩 Using AWS Account: ${ACCOUNT_ID}, Region: ${REGION}"

echo "🔄 Normalizing helper scripts & making executable..."
for script in "${SCRIPTS_DIR}"/*.sh; do
  [[ -f "$script" ]] || continue
  dos2unix "$script" 2>/dev/null || true
  chmod +x "$script"
  echo "  • $script"
done
[[ -f "${ENABLE_CORS_SCRIPT}" ]] && chmod +x "${ENABLE_CORS_SCRIPT}" && echo "  • ${ENABLE_CORS_SCRIPT}"

echo "⛅ Deploying Core Stack: ${CORE_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${CORE_TEMPLATE}" \
  --stack-name "${CORE_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ Core Stack deployed."

echo "📦 Deploying DynamoDB Tables Stack: ${DYNAMO_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${DYNAMO_TEMPLATE}" \
  --stack-name "${DYNAMO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ DynamoDB Tables deployed."

echo "📦 Deploying S3 Buckets Stack: ${S3_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${S3_TEMPLATE}" \
  --stack-name "${S3_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ S3 Buckets deployed."

# 🚀 Deploying Cognito Stack
echo "🔐 Deploying Cognito Stack: ${COGNITO_STACK_NAME}"
aws cloudformation deploy \
  --template-file "${COGNITO_TEMPLATE}" \
  --stack-name "${COGNITO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ Cognito Stack deployed."

# 🛠️  Deploying Lambda functions...
"${LAMBDA_SCRIPT}" "${ENV}"
echo "✅ Lambdas deployed."

echo "🚀 Deploying API Gateway Stack: ${API_STACK_NAME}"
# Ensure template bucket exists for large templates
if ! aws s3api head-bucket --bucket "${TEMPLATE_BUCKET}" 2>/dev/null; then
  aws s3 mb "s3://${TEMPLATE_BUCKET}" --region "${REGION}"
fi
aws cloudformation deploy \
  --template-file "${API_TEMPLATE}" \
  --stack-name "${API_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}" \
  --s3-bucket "${TEMPLATE_BUCKET}"
echo "✅ API Gateway Stack deployed."

# 8️⃣.5️⃣ Enable CORS on API Gateway resources
API_NAME="${ENV}Kashishop2API"
RAW_API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${API_NAME}'].id" --output text --region "${REGION}")
API_ID="${RAW_API_ID}"
if [[ "${API_ID}" == https://* ]]; then
  API_ID=$(echo "${API_ID}" | sed -E 's|https://([^.]+).*$|\1|')
fi
if [[ -n "${API_ID}" && -f "${ENABLE_CORS_SCRIPT}" ]]; then
  python3 "${ENABLE_CORS_SCRIPT}" --api-id "${API_ID}" --region "${REGION}" --stage "${ENV}"
fi

echo "🔄 Syncing frontend files to S3..."
"${FRONTEND_SCRIPT}" "${ENV}"
echo "✅ Frontend synced."

# 🔟 Construct and print Frontend Website URL from S3 object URL
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucket'].OutputValue" \
  --output text --region "${REGION}")
if [[ -n "${BUCKET_NAME}" ]]; then
  FRONTEND_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/main/index.html"
  echo "🌐 Frontend Website URL: ${FRONTEND_URL}"
fi

echo "🎉 All resources for '${ENV}' have been provisioned and deployed!"
