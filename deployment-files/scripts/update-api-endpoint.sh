#!/usr/bin/env bash
#
# update-api-endpoint.sh
#
# Usage: ./update-api-endpoint.sh <EnvPrefix>
#
# This script retrieves the API Gateway invoke URL from the CloudFormation stack
# named <EnvPrefix>-kashishop-api, then updates the 'const API' variable in
# ../frontend/script/global.js to point to that URL.
#
# Requirements:
#  • AWS CLI v2 (configured with credentials & region)
#  • The CFN stack "<EnvPrefix>-kashishop-api" must exist and export ApiGatewayRestApiId
#  • Node-style JS file at ../frontend/script/global.js containing a line like:
#      const API = "...";
#
# Example:
#   chmod +x update-api-endpoint.sh
#   ./update-api-endpoint.sh dev

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <EnvPrefix>"
  exit 1
fi

EnvPrefix="$1"
API_STACK_NAME="${EnvPrefix}-kashishop-api"
GLOBAL_JS="$(pwd)/../frontend/script/global.js"

if [ ! -f "$GLOBAL_JS" ]; then
  echo "❌ global.js not found at '$GLOBAL_JS'"
  exit 1
fi

echo "Retrieving API Gateway ID from CloudFormation stack: $API_STACK_NAME" >&2
API_ID=$(aws cloudformation describe-stacks \
  --stack-name "$API_STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayRestApiId'].OutputValue" \
  --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
  echo "❌ Could not find ApiGatewayRestApiId output in stack '$API_STACK_NAME'."
  exit 1
fi

# Construct the invoke URL for the 'prod' stage
REGION=$(aws configure get region || echo "us-east-1")
INVOKE_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"

echo "Updating global.js with API endpoint: $INVOKE_URL" >&2

# Use sed to replace the const API value (handles single or double quotes)
# Matches: const API = "...";  or const API = '...';
# and replaces inner string with new URL
sed -i.bak -E "s@(const API *= *[\"\'])[^"]*([\"\'];)@\1${INVOKE_URL}\2@" "$GLOBAL_JS"

if [ $? -eq 0 ]; then
  echo "✅ global.js updated successfully." >&2
  rm -f "${GLOBAL_JS}.bak"
else
  echo "❌ Failed to update global.js" >&2
  exit 1
fi
