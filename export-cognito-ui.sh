#!/usr/bin/env bash
#
# export-cognito-ui.sh
#
# Exports domain + UI branding for all Cognito User Pools
# into cognito-ui-export.json
#
# Prereqs:
#  • AWS CLI v2 configured (region + creds)
#  • jq installed
#
# Usage:
#   chmod +x export-cognito-ui.sh
#   ./export-cognito-ui.sh

set -euo pipefail

OUTFILE="cognito-ui-export.json"
echo "[" > "$OUTFILE"
first=true

# 1. List all user pools
aws cognito-idp list-user-pools --max-results 60 --output json \
  | jq -r '.UserPools[].Id' \
  | while read -r POOL_ID; do

    # 2. Describe User Pool (so you know settings to recreate it)
    POOL_DESC=$(aws cognito-idp describe-user-pool \
                  --user-pool-id "$POOL_ID" \
                  --output json \
                | jq '.UserPool')

    # 3. Describe Hosted UI domain configuration
    DOMAIN_DESC=$(aws cognito-idp describe-user-pool-domain \
                    --domain "$(echo "$POOL_DESC" | jq -r '.Domain // empty')" \
                    --output json \
                  | jq '.DomainDescription // empty')

    # 4. Get classic Hosted UI CSS + logo
    UICUST=$(aws cognito-idp get-ui-customization \
               --user-pool-id "$POOL_ID" \
               --output json \
             | jq '.UICustomization // {}')

    # 5. Assemble export object
    OBJ=$(jq -n \
      --arg id "$POOL_ID" \
      --argjson pool "$POOL_DESC" \
      --argjson domain "$DOMAIN_DESC" \
      --argjson ui "$UICUST" \
      '{
         UserPoolId:   $id,
         PoolSettings: $pool,
         DomainDescription: $domain,
         UICustomization:    $ui
       }'
    )

    # 6. Append with comma separation
    if $first; then
      echo "  $OBJ" >> "$OUTFILE"
      first=false
    else
      echo ", $OBJ" >> "$OUTFILE"
    fi

  done

echo "]" >> "$OUTFILE"

echo "✅ Export complete: $OUTFILE"
