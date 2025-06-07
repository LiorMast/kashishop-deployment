#!/usr/bin/env bash
#
# update-api-endpoint.sh (now accepts EnvPrefix and ApiId)
#
# Usage: ./update-api-endpoint.sh <EnvPrefix> <ApiId>
#
# Constructs the invoke URL as:
#     https://<ApiId>.execute-api.<REGION>.amazonaws.com/<EnvPrefix>/
# and updates the const API variable in frontend/script/global.js.
#
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <EnvPrefix> <ApiId>"
  exit 1
fi

EnvPrefix="$1"
API_ID="$2"
GLOBAL_JS="$(pwd)/frontend/script/global.js"

if [ ! -f "$GLOBAL_JS" ]; then
  echo "❌ global.js not found at '$GLOBAL_JS'"
  exit 1
fi

# Determine AWS region
REGION=$(aws configure get region || echo "us-east-1")

# Construct invoke URL with trailing slash
INVOKE_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${EnvPrefix}/"

echo "Updating global.js with API endpoint: ${INVOKE_URL}" >&2

# Replace only the const API line
sed -i.bak -E "s|^const API = .*;|const API = \"${INVOKE_URL}\";|" "$GLOBAL_JS"

if [ $? -eq 0 ]; then
  echo "✅ global.js updated successfully" >&2
  rm -f "${GLOBAL_JS}.bak"
else
  echo "❌ Failed to update global.js" >&2
  exit 1
fi
