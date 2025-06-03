#!/usr/bin/env bash
#
# This script exports all AWS Lambda function configurations into a single JSON file named “lambda_full.json.”
# It gathers each function’s settings (configuration, tags, resource‐based policy, aliases, versions, event source mappings).
# Debug prints go to stderr to avoid corrupting the JSON on stdout.
#
# Prerequisites:
#  • AWS CLI v2 (configured with credentials & region)
#  • jq
#
# Usage:
#  chmod +x get-lambda.sh
#  ./get-lambda.sh
#

set -euo pipefail

OUTPUT="lambda_full.json"

echo "=== Starting Lambda export script ===" >&2
echo "Output will be written to: $OUTPUT" >&2
echo >&2

# 1. Start the JSON array
printf '[\n' > "$OUTPUT"
first_function=true

# 2. List all Lambda functions
echo "Listing all Lambda functions..." >&2
RAW_LIST=$( aws lambda list-functions --output json 2>/dev/null || echo '{ "Functions": [] }' )
if [[ -z "$RAW_LIST" ]] || ! echo "$RAW_LIST" | jq empty 2>/dev/null; then
  echo "⚠️  list-functions returned empty/invalid JSON; defaulting to empty list." >&2
  FUNCTION_LIST='{ "Functions": [] }'
else
  FUNCTION_LIST="$RAW_LIST"
fi

echo "Raw list-functions response (or fallback):" >&2
echo "$FUNCTION_LIST" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
echo >&2

# 3. Iterate over each function
echo "Iterating over each Lambda function..." >&2
echo "$FUNCTION_LIST" | jq -r '.Functions[].FunctionName' | while read -r FN; do
  echo "----------------------------------------------" >&2
  echo "Processing function: $FN" >&2

  #
  # 3.1 Get function configuration
  #
  echo "  -> get-function-configuration for $FN..." >&2
  RAW_CFG=$( aws lambda get-function-configuration --function-name "$FN" --output json 2>/dev/null || echo '{ }' )
  if [[ -z "$RAW_CFG" ]] || ! echo "$RAW_CFG" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-function-configuration returned empty/invalid JSON; using '{}'." >&2
    CFG_JSON='{ }'
  else
    CFG_JSON="$RAW_CFG"
  fi
  echo "  CFG_JSON:" >&2
  echo "$CFG_JSON" >&2
  echo >&2

  #
  # 3.2 Get tags
  #
  FUNCTION_ARN=$( echo "$CFG_JSON" | jq -r '.FunctionArn // empty' )
  if [[ -z "$FUNCTION_ARN" ]]; then
    echo "  ⚠️  Could not extract FunctionArn; skipping tags." >&2
    TAGS_JSON='{ "Tags": {} }'
  else
    echo "  -> list-tags for $FUNCTION_ARN ..." >&2
    RAW_TAGS=$( aws lambda list-tags --resource "$FUNCTION_ARN" --output json 2>/dev/null || echo '{ "Tags": {} }' )
    if [[ -z "$RAW_TAGS" ]] || ! echo "$RAW_TAGS" | jq empty 2>/dev/null; then
      echo "  ⚠️  list-tags returned empty/invalid JSON; using '{\"Tags\":{}}'." >&2
      TAGS_JSON='{ "Tags": {} }'
    else
      TAGS_JSON="$RAW_TAGS"
    fi
  fi
  echo "  TAGS_JSON:" >&2
  echo "$TAGS_JSON" >&2
  echo >&2

  #
  # 3.3 Get resource-based policy
  #
  echo "  -> get-policy for $FN ..." >&2
  RAW_POLICY=$( aws lambda get-policy --function-name "$FN" --output json 2>/dev/null || echo '{ }' )
  if [[ -z "$RAW_POLICY" ]] || ! echo "$RAW_POLICY" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-policy returned empty/invalid JSON; using '{}'." >&2
    POLICY_JSON='{ }'
  else
    POLICY_JSON="$RAW_POLICY"
  fi
  echo "  POLICY_JSON:" >&2
  echo "$POLICY_JSON" >&2
  echo >&2

  #
  # 3.4 List aliases
  #
  echo "  -> list-aliases for $FN ..." >&2
  RAW_ALIASES=$( aws lambda list-aliases --function-name "$FN" --output json 2>/dev/null || echo '{ "Aliases": [] }' )
  if [[ -z "$RAW_ALIASES" ]] || ! echo "$RAW_ALIASES" | jq empty 2>/dev/null; then
    echo "  ⚠️  list-aliases returned empty/invalid JSON; using '{\"Aliases\":[]}'." >&2
    ALIASES_JSON='{ "Aliases": [] }'
  else
    ALIASES_JSON="$RAW_ALIASES"
  fi
  echo "  ALIASES_JSON:" >&2
  echo "$ALIASES_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  #
  # 3.5 List versions
  #
  echo "  -> list-versions-by-function for $FN ..." >&2
  RAW_VERSIONS=$( aws lambda list-versions-by-function --function-name "$FN" --output json 2>/dev/null || echo '{ "Versions": [] }' )
  if [[ -z "$RAW_VERSIONS" ]] || ! echo "$RAW_VERSIONS" | jq empty 2>/dev/null; then
    echo "  ⚠️  list-versions-by-function returned empty/invalid JSON; using '{\"Versions\":[]}'." >&2
    VERSIONS_JSON='{ "Versions": [] }'
  else
    VERSIONS_JSON="$RAW_VERSIONS"
  fi
  echo "  VERSIONS_JSON:" >&2
  echo "$VERSIONS_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  #
  # 3.6 List event source mappings
  #
  echo "  -> list-event-source-mappings for $FN ..." >&2
  RAW_ESM=$( aws lambda list-event-source-mappings --function-name "$FN" --output json 2>/dev/null || echo '{ "EventSourceMappings": [] }' )
  if [[ -z "$RAW_ESM" ]] || ! echo "$RAW_ESM" | jq empty 2>/dev/null; then
    echo "  ⚠️  list-event-source-mappings returned empty/invalid JSON; using '{\"EventSourceMappings\":[]}'." >&2
    ESM_JSON='{ "EventSourceMappings": [] }'
  else
    ESM_JSON="$RAW_ESM"
  fi
  echo "  ESM_JSON:" >&2
  echo "$ESM_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  #
  # 3.7 Build the JSON object for this function
  #
  echo "  -> Final variables before jq -n (step 3.7):" >&2
  echo "       FunctionName       = $(echo "$CFG_JSON" | jq -r '.FunctionName // empty')" >&2
  echo "       CFG_JSON           = $CFG_JSON" >&2
  echo "       TAGS_JSON          = $TAGS_JSON" >&2
  echo "       POLICY_JSON        = $POLICY_JSON" >&2
  echo "       ALIASES_JSON       = $ALIASES_JSON" >&2
  echo "       VERSIONS_JSON      = $VERSIONS_JSON" >&2
  echo "       ESM_JSON           = $ESM_JSON" >&2
  echo >&2

  echo "  -> Building JSON object for function $FN..." >&2
  FUNC_OBJ=$(jq -n \
    --arg fn      "$(echo "$CFG_JSON" | jq -r '.FunctionName')" \
    --argjson  cfg     "$CFG_JSON" \
    --argjson  tags    "$TAGS_JSON" \
    --argjson  policy  "$POLICY_JSON" \
    --argjson  aliases "$ALIASES_JSON" \
    --argjson  versions "$VERSIONS_JSON" \
    --argjson  esm     "$ESM_JSON" \
    '{
       functionName:       $fn,
       configuration:      $cfg,
       tags:               ($tags.Tags // {}),
       policy:             (
                              # If policy.Policy is a JSON string, parse it; else null
                              if ($policy.Policy // null) | type == "string" then 
                                ($policy.Policy | fromjson) 
                              else 
                                null 
                              end
                           ),
       aliases:            ($aliases.Aliases // []),
       versions:           ($versions.Versions // []),
       eventSourceMappings: ($esm.EventSourceMappings // [])
     }'
  )
  echo "  JSON object for function $FN built successfully." >&2

  #
  # 3.8 Append this function object to the JSON array
  #
  if [ "$first_function" = true ]; then
    printf "  %s" "$FUNC_OBJ" >> "$OUTPUT"
    first_function=false
    echo "  Appended first function object." >&2
  else
    printf ",\n  %s" "$FUNC_OBJ" >> "$OUTPUT"
    echo "  Appended subsequent function object." >&2
  fi

  echo "Finished processing function: $FN" >&2
  echo "----------------------------------------------" >&2
  echo >&2
done

# 4. Close the JSON array
printf "\n]\n" >> "$OUTPUT"
echo "Closed JSON array." >&2

echo "✅ Done. See full Lambda export in $OUTPUT." >&2
