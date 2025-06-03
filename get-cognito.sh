#!/usr/bin/env bash
#
# This script exports all Cognito User Pools and Identity Pools (with full details)
# into a single JSON file named “cognito_full.json.”
# Debug prints now go to stderr so as not to corrupt the JSON on stdout.
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
echo "Initialized output file with userPools array." >&2

first_pool=true

# 2. List all User Pools (paginated; --max-results ≤ 60)
echo "Fetching list of User Pools..." >&2
POOL_LIST_JSON=$(aws cognito-idp list-user-pools --max-results 60 --output json)
echo "Raw list-user-pools response:" >&2
echo "$POOL_LIST_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
echo >&2

echo "Iterating over each User Pool..." >&2
echo "$POOL_LIST_JSON" \
  | jq -r '.UserPools[] | "\(.Id):::\(.Name)"' \
  | while IFS=":::" read -r POOL_ID POOL_NAME; do
    echo "----------------------------------------------" >&2
    echo "Processing User Pool: ID=$POOL_ID, Name=$POOL_NAME" >&2

    #
    # 2.1 Describe the pool
    #
    echo "  -> Describing User Pool $POOL_ID..." >&2
    POOL_DESC=$(aws cognito-idp describe-user-pool \
                   --user-pool-id "$POOL_ID" \
                   --output json \
               | jq '.UserPool')
    echo "  Retrieved describe-user-pool for $POOL_ID." >&2

    #
    # 2.2 Collect all App Clients for this pool
    #
    echo "  -> Listing App Clients for Pool $POOL_ID..." >&2
    CLIENT_IDS=$(aws cognito-idp list-user-pool-clients \
                   --user-pool-id "$POOL_ID" \
                   --max-results 60 \
                   --output json \
                 | jq -r '.UserPoolClients[].ClientId' || echo "")
    echo "  Found client IDs: $CLIENT_IDS" >&2

    if [ -n "$CLIENT_IDS" ]; then
      echo "    Describing each App Client..." >&2
      # Capture only the JSON lines; debug prints go to stderr
      ALL_CLIENTS_JSON=$(
        for CID in $CLIENT_IDS; do
          echo "      • describe-user-pool-client for client $CID" >&2
          aws cognito-idp describe-user-pool-client \
            --user-pool-id "$POOL_ID" \
            --client-id "$CID" \
            --output json \
          | jq -c --arg clientId "$CID" '{ clientId: $clientId, details: .UserPoolClient }'
        done | jq -s '.'
      )
      echo "    Completed describing all App Clients." >&2
    else
      echo "    No App Clients found for Pool $POOL_ID." >&2
      ALL_CLIENTS_JSON="[]"
    fi

    #
    # 2.3 Collect all Groups for this pool
    #
    echo "  -> Listing Groups for Pool $POOL_ID..." >&2
    GROUP_NAMES=$(aws cognito-idp list-groups \
                    --user-pool-id "$POOL_ID" \
                    --output json \
                  | jq -r '.Groups[].GroupName' || echo "")
    echo "  Found group names: $GROUP_NAMES" >&2

    if [ -n "$GROUP_NAMES" ]; then
      echo "    Fetching details for each Group..." >&2
      ALL_GROUPS_JSON=$(
        for G in $GROUP_NAMES; do
          echo "      • get-group for group $G" >&2
          aws cognito-idp get-group \
            --user-pool-id "$POOL_ID" \
            --group-name "$G" \
            --output json \
          | jq -c --arg groupName "$G" '{ groupName: $groupName, details: .Group }'
        done | jq -s '.'
      )
      echo "    Completed fetching group details." >&2
    else
      echo "    No Groups found for Pool $POOL_ID." >&2
      ALL_GROUPS_JSON="[]"
    fi

    #
    # 2.4 List all Identity Providers configured on this User Pool
    #
    echo "  -> Listing Identity Providers for Pool $POOL_ID..." >&2
    IDP_LIST=$(aws cognito-idp list-identity-providers \
                 --user-pool-id "$POOL_ID" \
                 --max-results 60 \
                 --output json \
               | jq '.Providers' || echo "[]")
    echo "  Identity Providers for $POOL_ID:" >&2
    echo "$IDP_LIST" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2

    #
    # 2.5 List all Resource Servers (custom OAuth scopes) for this pool
    #
    echo "  -> Listing Resource Servers for Pool $POOL_ID..." >&2
    RS_LIST=$(aws cognito-idp list-resource-servers \
                --user-pool-id "$POOL_ID" \
                --max-results 50 \
                --output json \
              | jq '.ResourceServers' || echo "[]")
    echo "  Resource Servers for $POOL_ID:" >&2
    echo "$RS_LIST" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2

    #
    # 2.6 Build a single JSON object for this User Pool
    #
    echo "  -> Building JSON object for Pool $POOL_ID..." >&2
    POOL_OBJ=$(jq -n \
      --arg id "$POOL_ID" \
      --arg name "$POOL_NAME" \
      --argjson details "$POOL_DESC" \
      --argjson clients "$ALL_CLIENTS_JSON" \
      --argjson groups "$ALL_GROUPS_JSON" \
      --argjson idps "$IDP_LIST" \
      --argjson rservers "$RS_LIST" \
      '{
         poolId:            $id,
         poolName:          $name,
         details:           $details,
         clients:           $clients,
         groups:            $groups,
         identityProviders: $idps,
         resourceServers:   $rservers
       }'
    )
    echo "  JSON object for Pool $POOL_ID built successfully." >&2

    #
    # 2.7 Append this object into the "userPools" array
    #
    if [ "$first_pool" = true ]; then
      printf "\n    %s" "$POOL_OBJ" >> "$OUTPUT"
      first_pool=false
      echo "  Appended first pool object." >&2
    else
      printf ",\n    %s" "$POOL_OBJ" >> "$OUTPUT"
      echo "  Appended subsequent pool object." >&2
    fi

    echo "Finished processing Pool $POOL_ID." >&2
    echo "----------------------------------------------" >&2
    echo >&2
  done

# 3. Close the userPools array and start "identityPools"
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
