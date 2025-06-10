#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage: $0 <CognitoStackName|AppClientId> <S3Bucket> <Region> <RedirectUri> [DomainPrefix]"
  exit 1
fi

INPUT_ID="$1"
S3_BUCKET="$2"
REGION="$3"
REDIRECT_URI="$4"
DOMAIN_PREFIX="${5:-}"

echo "Input identifier:      $INPUT_ID"
echo "S3 bucket:             $S3_BUCKET"
echo "AWS region:            $REGION"
echo "Redirect URI:          $REDIRECT_URI"
if [[ -n "$DOMAIN_PREFIX" ]]; then
  echo "Provided domain prefix: $DOMAIN_PREFIX"
fi
echo

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: figure out your real stack name & client ID
# ─────────────────────────────────────────────────────────────────────────────
set +e
aws cloudformation describe-stacks --stack-name "$INPUT_ID" --region "$REGION" >/dev/null 2>&1
if [[ $? -eq 0 ]]; then
  COGNITO_STACK_NAME="$INPUT_ID"
  APP_CLIENT_ID=""
else
  COGNITO_STACK_NAME=""
  APP_CLIENT_ID="$INPUT_ID"
fi
set -e

if [[ -z "$COGNITO_STACK_NAME" ]]; then
  echo "⚠️  “$INPUT_ID” isn’t a stack name; searching for a stack that created App-Client-ID $APP_CLIENT_ID…"
  COGNITO_STACK_NAME=$(
    aws cloudformation describe-stacks \
      --region "$REGION" \
      --query "Stacks[?Outputs && contains(Outputs[].OutputValue, '$APP_CLIENT_ID')].StackName" \
      --output text
  )
  if [[ -z "$COGNITO_STACK_NAME" ]]; then
    echo "❌ Error: no CloudFormation stack outputs contain App-Client-ID $APP_CLIENT_ID"
    exit 1
  fi
  echo "   ✓ Found stack: $COGNITO_STACK_NAME"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: pull both IDs from the stack outputs
# ─────────────────────────────────────────────────────────────────────────────
echo
echo "🔍 Fetching Cognito IDs from stack $COGNITO_STACK_NAME…"
USER_POOL_ID=$(
  aws cloudformation describe-stacks \
    --stack-name "$COGNITO_STACK_NAME" \
    --region     "$REGION" \
    --query      "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolId')].OutputValue" \
    --output     text
)
APP_CLIENT_ID=$(
  aws cloudformation describe-stacks \
    --stack-name "$COGNITO_STACK_NAME" \
    --region     "$REGION" \
    --query      "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolClientId')].OutputValue" \
    --output     text
)
echo "   ✓ User Pool ID:  $USER_POOL_ID"
echo "   ✓ App Client ID: $APP_CLIENT_ID"
echo

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: grab (or reuse) the Hosted-UI domain prefix
# ─────────────────────────────────────────────────────────────────────────────
if [[ -z "$DOMAIN_PREFIX" ]]; then
  DOMAIN_PREFIX=$(
    aws cloudformation describe-stacks \
      --stack-name "$COGNITO_STACK_NAME" \
      --region     "$REGION" \
      --query      "Stacks[0].Outputs[?ends_with(OutputKey, 'UserPoolDomainId')].OutputValue" \
      --output     text
  )
  echo "   ✓ Using domain prefix from stack: $DOMAIN_PREFIX"
else
  echo "   ✓ Using provided domain prefix:    $DOMAIN_PREFIX"
fi
echo

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: build the login URL + deploy
# ─────────────────────────────────────────────────────────────────────────────
LOGIN_URL="https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/login?response_type=code&client_id=${APP_CLIENT_ID}&redirect_uri=${REDIRECT_URI}"
echo "   → Hosted UI login URL: $LOGIN_URL"
echo

TMPDIR="$(mktemp -d)"
cat >"$TMPDIR/login.html" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Sign In</title>
  <style>
    body { font-family: sans-serif; text-align: center; padding: 4rem; }
    a.button {
      display: inline-block; padding: 1rem 2rem;
      background: #4f46e5; color: white; border-radius: 0.5rem;
      text-decoration: none; font-size: 1.2rem;
    }
  </style>
</head>
<body>
  <h1>Welcome</h1>
  <p><a class="button" href="${LOGIN_URL}">Sign in with Cognito</a></p>
</body>
</html>
EOF

echo "📄 Syncing to s3://${S3_BUCKET}/"
aws s3 sync "$TMPDIR" "s3://${S3_BUCKET}/" --region "$REGION"

echo "🔧 Configuring S3 static website hosting"
aws s3 website "s3://${S3_BUCKET}/" \
  --index-document login.html \
  --error-document login.html \
  --region "$REGION"

echo
echo "✅ Done! Your login page is live at:"
echo "   http://${S3_BUCKET}.s3-website.${REGION}.amazonaws.com/login.html"
