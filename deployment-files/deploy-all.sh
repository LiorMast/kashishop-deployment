#!/usr/bin/env bash
#
# deploy-all.sh (updated to deploy Cognito stack and call external callback updater)
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
#   8. Sync frontend files to S3
#   9. Update Cognito callback URL via external script
#  10. Deploy API Gateway stack
#  11. Enable CORS on API Gateway resources
#  12. Print Frontend URL

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
DEPLOY_FRONTEND_SCRIPT="${SCRIPTS_DIR}/deploy-frontend.sh"
ENABLE_CORS_SCRIPT="${SCRIPTS_DIR}/enable-cors-apigw.py"
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

# # 3️⃣ Deploy Core Stack
# echo "⛅ Deploying Core Stack: ${CORE_STACK_NAME}"
# aws cloudformation deploy \
#   --template-file "${TEMPLATE_DIR}/main-template.yaml" \
#   --stack-name "${CORE_STACK_NAME}" \
#   --parameter-overrides EnvPrefix="${ENV}" \
#   --capabilities CAPABILITY_NAMED_IAM \
#   --region "${REGION}"
# echo "✅ Core Stack deployed."

# 4️⃣ Deploy DynamoDB Stack
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
aws cloudformation deploy \
  --template-file "${TEMPLATE_DIR}/cognito-template.yaml" \
  --stack-name "${COGNITO_STACK_NAME}" \
  --parameter-overrides EnvPrefix="${ENV}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}"
echo "✅ Cognito Stack deployed."

# 7️⃣ Deploy Lambda functions
echo "🛠️ Deploying Lambdas..."
"${LAMBDA_SCRIPT}" "${ENV}"
echo "✅ Lambdas deployed."

# 8️⃣ Sync frontend to S3
echo "🔄 Syncing frontend files to S3..."
"${DEPLOY_FRONTEND_SCRIPT}" "${ENV}"
echo "✅ Frontend synced."

# 9️⃣ Update Cognito callback URL
echo "🔄 Updating Cognito callback URL via external script..."
"${UPDATE_COGNITO_SCRIPT}" "${ENV}"
echo "✅ Cognito callback updated."

# 🔟 Deploy API Gateway Stack
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

# 11️⃣ Enable CORS on API Gateway
API_NAME="${ENV}Kashishop2API"
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${API_NAME}'].id" --output text --region "${REGION}")
if [[ -n "${API_ID}" && -f "${ENABLE_CORS_SCRIPT}" ]]; then
  python3 "${ENABLE_CORS_SCRIPT}" --api-id "${API_ID}" --region "${REGION}" --stage "${ENV}"
fi

# 12️⃣ Print Frontend URL
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${S3_STACK_NAME}" \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'BucketName')].OutputValue | [0]"\
  --output text --region "${REGION}")
if [[ -n "${BUCKET_NAME}" ]]; then
  FRONTEND_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/main/index.html"
  echo "🌐 Frontend Website URL: ${FRONTEND_URL}"
fi

 echo "🎉 All resources for '${ENV}' have been provisioned and deployed!"