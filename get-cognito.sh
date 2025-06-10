#!/usr/bin/env bash
#
# This script exports all Cognito User Pools and Identity Pools (with full details)
# plus Hosted UI domain & branding configuration into a single JSON file named “cognito_full.json.”
#
# Prerequisites:
#  • AWS CLI v2 (configured with credentials & region)
#  • jq
#
# Usage:
#  chmod +x get-cognito.sh
#  ./get-cognito.sh
#

set -euo pipefail

OUTPUT="cognito_full.json"

echo "=== Starting Cognito export script ===" >&2
echo "Output will be written to: $OUTPUT" >&2
echo >&2

# 1. Start the top‐level JSON object with "userPools"
printf '{\n  "userPools": [' > "$OUTPUT"

first_pool=true

# 2. List all User Pools
POOL_LIST_JSON=$(aws cognito-idp list-user-pools --max-results 60 --output json)

echo "$POOL_LIST_JSON" \
  | jq -r '.UserPools[] | "\(.Id):::\(.Name)"' \
  | while IFS=":::" read -r POOL_ID POOL_NAME; do

    # 2.1 Describe the pool
    POOL_DESC=$(aws cognito-idp describe-user-pool \
                   --user-pool-id "$POOL_ID" \
                   --output json \
               | jq '.UserPool')

    # 2.2 Collect App Clients (unchanged)…
    CLIENT_IDS=$(aws cognito-idp list-user-pool-clients \
                   --user-pool-id "$POOL_ID" \
                   --max-results 60 \
                   --output json \
                 | jq -r '.UserPoolClients[].ClientId' || echo "")
    if [ -n "$CLIENT_IDS" ]; then
      ALL_CLIENTS_JSON=$(
        for CID in $CLIENT_IDS; do
          aws cognito-idp describe-user-pool-client \
            --user-pool-id "$POOL_ID" \
            --client-id "$CID" \
            --output json \
          | jq -c --arg clientId "$CID" '{ clientId: $clientId, details: .UserPoolClient }'
        done | jq -s '.'
      )
    else
      ALL_CLIENTS_JSON="[]"
    fi

    # 2.3 Collect Groups (unchanged)…
    GROUP_NAMES=$(aws cognito-idp list-groups \
                    --user-pool-id "$POOL_ID" \
                    --output json \
                  | jq -r '.Groups[].GroupName' || echo "")
    if [ -n "$GROUP_NAMES" ]; then
      ALL_GROUPS_JSON=$(
        for G in $GROUP_NAMES; do
          aws cognito-idp get-group \
            --user-pool-id "$POOL_ID" \
            --group-name "$G" \
            --output json \
          | jq -c --arg groupName "$G" '{ groupName: $groupName, details: .Group }'
        done | jq -s '.'
      )
    else
      ALL_GROUPS_JSON="[]"
    fi

    # 2.4 Identity Providers (unchanged)…
    IDP_LIST=$(aws cognito-idp list-identity-providers \
                 --user-pool-id "$POOL_ID" \
                 --max-results 60 \
                 --output json \
               | jq '.Providers' || echo "[]")

    # 2.5 Resource Servers (unchanged)…
    RS_LIST=$(aws cognito-idp list-resource-servers \
                --user-pool-id "$POOL_ID" \
                --max-results 50 \
                --output json \
              | jq '.ResourceServers' || echo "[]")

    # ────────────────────────────────────────────────────────────
    # 2.6 NEW: Describe Hosted UI Domain Configuration
    # ────────────────────────────────────────────────────────────
    DOMAIN_PREFIX=$(echo "$POOL_DESC" | jq -r '.Domain // empty')
    if [ -n "$DOMAIN_PREFIX" ] && [ "$DOMAIN_PREFIX" != "null" ]; then
      DOMAIN_DESC=$(aws cognito-idp describe-user-pool-domain \
                     --domain "$DOMAIN_PREFIX" \
                     --output json \
                   | jq '.DomainDescription')
    else
      DOMAIN_DESC="null"
    fi

    # ────────────────────────────────────────────────────────────
    # 2.7 NEW: Get Hosted UI (classic) Branding CSS & Logo
    # ────────────────────────────────────────────────────────────
    UI_CUSTOM=$(aws cognito-idp get-ui-customization \
                  --user-pool-id "$POOL_ID" \
                  --output json \
                | jq '.UICustomization // {}')
        # ────────────────────────────────────────────────────────────
    # 2.8 NEW: Collect Managed Login Branding per App Client
    # ────────────────────────────────────────────────────────────
    if [ -n "$CLIENT_IDS" ]; then
      ALL_MANAGED_BRANDING_JSON=$(
        for CID in $CLIENT_IDS; do
          aws cognito-idp describe-managed-login-branding-by-client \
            --user-pool-id "$POOL_ID" \
            --client-id "$CID" \
            --return-merged-resources \
            --output json \
          | jq -c --arg clientId "$CID" '{ clientId: $clientId, managedLoginBranding: .ManagedLoginBranding }'
        done | jq -s '.'
      )
    else
      ALL_MANAGED_BRANDING_JSON="[]"
    fi

    # ────────────────────────────────────────────────────────────
    # 2.8 Build the JSON object for this pool (extended, using slurpfiles)
    # ────────────────────────────────────────────────────────────
   POOL_OBJ=$(jq -n \
     --arg id "$POOL_ID" \
     --arg name "$POOL_NAME" \
     --slurpfile details <(printf '%s' "$POOL_DESC") \
     --slurpfile clients <(printf '%s' "$ALL_CLIENTS_JSON") \
     --slurpfile groups  <(printf '%s' "$ALL_GROUPS_JSON") \
     --slurpfile idps    <(printf '%s' "$IDP_LIST") \
     --slurpfile rservrs <(printf '%s' "$RS_LIST") \
     --slurpfile domain  <(printf '%s' "$DOMAIN_DESC") \
     --slurpfile ui      <(printf '%s' "$UI_CUSTOM") \
     --slurpfile branding <(printf '%s' "$ALL_MANAGED_BRANDING_JSON") \
     '{
        poolId:             $id,
        poolName:           $name,
        details:            $details[0],
        clients:            $clients,
        groups:             $groups,
        identityProviders:  $idps,
        resourceServers:    $rservrs,
        hostedUIDomain:     $domain[0],
        uiCustomization:    $ui[0],
        managedLoginBranding:$branding
      }'
   )


    # 2.9 Append into output
    if [ "$first_pool" = true ]; then
      printf "\n    %s" "$POOL_OBJ" >> "$OUTPUT"
      first_pool=false
    else
      printf ",\n    %s" "$POOL_OBJ" >> "$OUTPUT"
    fi

  done

# 3. Close userPools and proceed with identityPools (unchanged)…
printf "\n  ],\n  \"identityPools\": [" >> "$OUTPUT"
echo "Closed userPools array. Starting identityPools array." >&2

first_ip=true

# 4. List all Identity Pools (paginated; --max-results ≤ 60)
echo "Fetching list of Identity Pools..." >&2
IDENTITY_LIST_JSON=$(aws cognito-identity list-identity-pools --max-results 60 --output json)
echo "Raw list-identity-pools response:" >&2
echo "$IDENTITY_LIST_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2

echo "Iterating over each Identity Pool..." >&2
echo "$IDENTITY_LIST_JSON" \
  | jq -r '.IdentityPools[] | "\(.IdentityPoolId):::\(.IdentityPoolName)"' \
  | while IFS=":::" read -r IP_ID IP_NAME; do
    echo "----------------------------------------------" >&2
    echo "Processing Identity Pool: ID=$IP_ID, Name=$IP_NAME" >&2

    #
    # 4.1 Describe the Identity Pool
    #
    echo "  -> Describing Identity Pool $IP_ID..." >&2
    IP_DESC=$(aws cognito-identity describe-identity-pool \
                --identity-pool-id "$IP_ID" \
                --output json)
    echo "  Retrieved describe-identity-pool for $IP_ID." >&2

    #
    # 4.2 Get the IAM role mappings for this Identity Pool
    #
    echo "  -> Fetching roles for Identity Pool $IP_ID..." >&2
    IP_ROLES=$(aws cognito-identity get-identity-pool-roles \
                --identity-pool-id "$IP_ID" \
                --output json)
    echo "  Retrieved get-identity-pool-roles for $IP_ID." >&2

    #
    # 4.3 Build a single JSON object for this Identity Pool
    #
    echo "  -> Building JSON object for Identity Pool $IP_ID..." >&2
    IP_OBJ=$(jq -n \
      --arg id "$IP_ID" \
      --arg name "$IP_NAME" \
      --argjson details "$IP_DESC" \
      --argjson roles "$IP_ROLES" \
      '{
         identityPoolId:   $id,
         identityPoolName: $name,
         details:          $details,
         roles:            $roles
       }'
    )
    echo "  JSON object for Identity Pool $IP_ID built successfully." >&2

    #
    # 4.4 Append this object into the "identityPools" array
    #
    if [ "$first_ip" = true ]; then
      printf "\n    %s" "$IP_OBJ" >> "$OUTPUT"
      first_ip=false
      echo "  Appended first identity pool object." >&2
    else
      printf ",\n    %s" "$IP_OBJ" >> "$OUTPUT"
      echo "  Appended subsequent identity pool object." >&2
    fi

    echo "Finished processing Identity Pool $IP_ID." >&2
    echo "----------------------------------------------" >&2
    echo >&2
  done

# 5. Close the identityPools array and the JSON object
printf "\n  ]\n}\n" >> "$OUTPUT"
echo "Closed identityPools array and JSON object." >&2

echo "✅ Done. See full Cognito export in $OUTPUT." >&2
