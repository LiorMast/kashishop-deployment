#!/usr/bin/env bash
#
# deploy-lambda.sh (updated)
#
# Usage: ./deploy-lambda.sh <EnvPrefix>
#
# Checks for Python3 and runs deploy-lambda.py if available. Otherwise, prints error and exits.
#
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <EnvPrefix>"
  exit 1
fi

EnvPrefix="$1"
LambdaDir="$(pwd)/lambda"

if [ ! -d "$LambdaDir" ]; then
  echo "❌ Directory '$LambdaDir' not found. Run this script from the repo root."
  exit 1
fi

# Check for python3 and deploy-lambda.py script
SCRIPT_DIR="$(dirname "$0")"
PY_DEPLOY="$SCRIPT_DIR/deploy-lambda.py"

if command -v python3 >/dev/null 2>&1 && [ -f "$PY_DEPLOY" ]; then
  echo "🐍 Python3 detected and deploy-lambda.py found. Running Python-based deployment..."
  python3 "$PY_DEPLOY" "$EnvPrefix"
  exit 0
else
  echo "❌ Python3 or deploy-lambda.py not found. Please install Python3 and ensure deploy-lambda.py is present in the same directory."
  exit 1
fi
