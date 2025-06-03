#!/usr/bin/env bash
#
# deploy-all.sh
#
# Usage: ./scripts/deploy-all.sh <ENV>
#
# Performs end-to-end deployment for Kashishop:
#   1. Print AWS caller identity & environment info
#   2. Ensure helper scripts are in Unix format & executable
#   3. Deploy core CloudFormation stack (S3, DynamoDB, Cognito)
#   4. Deploy all Lambda functions
#   5. Deploy API Gateway stack (ensuring S3 bucket for large templates)
#   6. Sync frontend files to S3
#   7. Print important outputs (Website URL, API ID)
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
API_STACK_NAME="${ENV}-kashishop-api"
TEMPLATE_DIR="$(pwd)/templates"
SCRIPTS_DIR="$(pwd)/scripts"
FRONTEND_DIR="$(pwd)/frontend"
LAMBDA_SCRIPT="${SCRIPTS_DIR}/deploy-lambda.sh"
FRONTEND_SCRIPT="${SCRIPTS_DIR}/deploy-frontend.sh"
API_TEMPLATE="${TEMPLATE_DIR}/api-gateway-template.yaml"
CORE_TEMPLATE="${TEMPLATE_DIR}/main-template.yaml"
TEMPLATE_BUCKET="${ENV}-kashishop-templates"

echo "🌐 Environment: ${ENV}"
echo

#
# 1️⃣ AWS Identity & Region/Account Info
#
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
echo -e "\n🚩 Using AWS Account: ${ACCOUNT_ID}, Region: ${REGION}"
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
echo

#
# 3️⃣ Deploy Core CloudFormation Stack
#
# Uncomment if core stack deployment is required here
# echo "⛅ Deploying Core Stack: ${CORE_STACK_NAME}"
# aws cloudformation deploy \
#   --template-file "${CORE_TEMPLATE}" \
#   --stack-name "${CORE_STACK_NAME}" \
#   --parameter-overrides EnvPrefix="${ENV}" \
#   --capabilities CAPABILITY_NAMED_IAM \
#   --region "${REGION}"
# echo "✅ Core Stack deployed."
echo

#
# 4️⃣ Deploy Lambda Functions
#
echo "🛠️  Deploying Lambda functions..."
"${LAMBDA_SCRIPT}" "${ENV}"
echo "✅ Lambdas deployed."
echo

#
# 5️⃣ Deploy API Gateway Stack (ensure S3 bucket exists)
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
# 6️⃣ Sync Frontend to S3
#
echo "📦 Syncing frontend files to S3..."
"${FRONTEND_SCRIPT}" "${ENV}"
echo "✅ Frontend synced."
echo

#
# 7️⃣ Print Key Outputs
#
echo "📢 Deployment complete for environment: ${ENV}"
echo

# Retrieve Website URL from Core Stack outputs
WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name "${CORE_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteURL'].OutputValue" \
  --output text --region "${REGION}")

if [[ -n "$WEBSITE_URL" ]]; then
  echo "🌐 Frontend Website URL: $WEBSITE_URL"
fi

# Retrieve API ID from API Stack outputs
API_ID=$(aws cloudformation describe-stacks \
  --stack-name "${API_STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayRestApiId'].OutputValue" \
  --output text --region "${REGION}")

if [[ -n "$API_ID" ]]; then
  echo "🛣️  API Gateway ID: $API_ID"
  echo "   Invoke URL (production stage): https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"
fi

echo
 echo "🎉 All resources for '${ENV}' have been provisioned and deployed!"
