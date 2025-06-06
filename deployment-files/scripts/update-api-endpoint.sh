#!/usr/bin/env bash
#
# update-api-endpoint.sh (fully fixed)
#
# Usage: ./update-api-endpoint.sh <EnvPrefix>
#
# Retrieves the API endpoint from the CloudFormation stack
# <EnvPrefix>-kashishop-api (using the ApiEndpoint output), and
# updates the const API variable in frontend/script/global.js
# to that value (no duplicating https://).
#
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <EnvPrefix>"
  exit 1
fi

EnvPrefix="$1"
API_STACK_NAME="${EnvPrefix}-kashishop-api"
GLOBAL_JS="$(pwd)/frontend/script/global.js"

if [ ! -f "$GLOBAL_JS" ]; then
  echo "❌ global.js not found at '$GLOBAL_JS'"
  exit 1
fi

echo "Retrieving API endpoint from CloudFormation stack: $API_STACK_NAME" >&2
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "$API_STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)

if [ -z "$API_ENDPOINT" ] || [ "$API_ENDPOINT" == "None" ]; then
  echo "❌ Could not find ApiEndpoint output in stack '$API_STACK_NAME'."
  exit 1
fi

# If the output already begins with http/https, use it. Otherwise, build the full URL
if [[ "$API_ENDPOINT" =~ ^https?:// ]]; then
  INVOKE_URL="$API_ENDPOINT"
else
  REGION=$(aws configure get region || echo "us-east-1")
  INVOKE_URL="https://${API_ENDPOINT}.execute-api.${REGION}.amazonaws.com/prod"
fi

echo "Updating global.js with API endpoint: $INVOKE_URL" >&2

# Replace the full const API assignment line (handles both single‐ and double‐quoted)
# Pattern matches: const API = "..."; or const API = '...';

sed -i.bak -E \
  "s|const[[:space:]]+API[[:space:]]*=[[:space:]]*\"[^\"]*\";|const API = \"${INVOKE_URL}\";|; \
  s|const[[:space:]]+API[[:space:]]*=[[:space:]]*'[^']*';|const API = '${INVOKE_URL}';|" \
  "$GLOBAL_JS"

if [ $? -eq 0 ]; then
  echo "✅ global.js updated successfully." >&2
  rm -f "${GLOBAL_JS}.bak"
else
  echo "❌ Failed to update global.js" >&2
  exit 1
fi
