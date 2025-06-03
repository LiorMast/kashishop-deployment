#!/usr/bin/env bash
#
# This script exports all DynamoDB table configurations into a single JSON file named "dynamodb_full.json."  
# It gathers each table’s settings (attribute definitions, key schema, provisioned throughput or on-demand mode,
# global and local secondary indexes, stream specification, TTL configuration, encryption settings, tags,
# and backups). Debug prints go to stderr to avoid corrupting the JSON on stdout.
#
# Prerequisites:
#  • AWS CLI v2 (configured with credentials & region)
#  • jq
#
# Usage:
#  chmod +x get-dynamodb.sh
#  ./get-dynamodb.sh
#
set -euo pipefail

OUTPUT="dynamodb_full.json"

echo "=== Starting DynamoDB export script ===" >&2
echo "Output will be written to: $OUTPUT" >&2
echo >&2

# 1. Start the JSON array in the output file
printf '[\n' > "$OUTPUT"
first_table=true

# 2. List all DynamoDB tables
echo "Listing all DynamoDB tables..." >&2
RAW_TABLE_LIST=$( aws dynamodb list-tables --output json 2>/dev/null || echo '{ "TableNames": [] }' )
if [[ -z "$RAW_TABLE_LIST" ]] || ! echo "$RAW_TABLE_LIST" | jq empty 2>/dev/null; then
  echo "⚠️  list-tables returned empty/invalid JSON; defaulting to empty list." >&2
  TABLE_LIST='{ "TableNames": [] }'
else
  TABLE_LIST="$RAW_TABLE_LIST"
fi

echo "Raw list-tables response (or fallback):" >&2
echo "$TABLE_LIST" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
echo >&2

# 3. Iterate over each table name
echo "Iterating over each table..." >&2
echo "$TABLE_LIST" | jq -r '.TableNames[]' | while read -r TABLE; do
  echo "----------------------------------------------" >&2
  echo "Processing table: $TABLE" >&2

  # 3.1 Describe table
  echo "  -> Describing table $TABLE..." >&2
  RAW_DESC=$( aws dynamodb describe-table --table-name "$TABLE" --output json 2>/dev/null || echo '{ "Table": {} }' )
  if [[ -z "$RAW_DESC" ]] || ! echo "$RAW_DESC" | jq empty 2>/dev/null; then
    echo "  ⚠️  describe-table returned empty/invalid JSON; using '{\"Table\":{}}'." >&2
    DESC_JSON='{ "Table": {} }'
  else
    DESC_JSON="$RAW_DESC"
  fi
  echo "  DESC_JSON:" >&2
echo "$DESC_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  # 3.2 Get tags for table
  # ARN format: arn:aws:dynamodb:<region>:<acct>:table/<TableName>
  TABLE_ARN=$( echo "$DESC_JSON" | jq -r '.Table.TableArn // empty' )
  if [[ -z "$TABLE_ARN" ]]; then
    echo "  ⚠️  Could not extract TableArn; skipping tags." >&2
    TAGS_JSON='{ "Tags": [] }'
  else
    echo "  -> list-tags-of-resource for $TABLE_ARN ..." >&2
    RAW_TAGS=$( aws dynamodb list-tags-of-resource --resource-arn "$TABLE_ARN" --output json 2>/dev/null || echo '{ "Tags": [] }' )
    if [[ -z "$RAW_TAGS" ]] || ! echo "$RAW_TAGS" | jq empty 2>/dev/null; then
      echo "  ⚠️  list-tags-of-resource returned empty/invalid JSON; using '{\"Tags\":[]}'." >&2
      TAGS_JSON='{ "Tags": [] }'
    else
      TAGS_JSON="$RAW_TAGS"
    fi
  fi
  echo "  TAGS_JSON:" >&2
echo "$TAGS_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  # 3.3 Get TTL configuration
  echo "  -> describe-time-to-live for $TABLE ..." >&2
  RAW_TTL=$( aws dynamodb describe-time-to-live --table-name "$TABLE" --output json 2>/dev/null || echo '{ "TimeToLiveDescription": {} }' )
  if [[ -z "$RAW_TTL" ]] || ! echo "$RAW_TTL" | jq empty 2>/dev/null; then
    echo "  ⚠️  describe-time-to-live returned empty/invalid JSON; using '{\"TimeToLiveDescription\":{}}'." >&2
    TTL_JSON='{ "TimeToLiveDescription": {} }'
  else
    TTL_JSON="$RAW_TTL"
  fi
  echo "  TTL_JSON:" >&2
echo "$TTL_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  # 3.4 List global tables description
  echo "  -> describe-global-table for $TABLE ..." >&2
  RAW_GLOBAL=$( aws dynamodb describe-global-table --global-table-name "$TABLE" --output json 2>/dev/null || echo '{ }' )
  if [[ -z "$RAW_GLOBAL" ]] || ! echo "$RAW_GLOBAL" | jq empty 2>/dev/null; then
    echo "  ⚠️  describe-global-table returned empty/invalid JSON or table not global; using '{}' ." >&2
    GLOBAL_JSON='{ }'
  else
    GLOBAL_JSON="$RAW_GLOBAL"
  fi
  echo "  GLOBAL_JSON:" >&2
echo "$GLOBAL_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  # 3.5 List backups for table (latest)
  echo "  -> list-backups for $TABLE ..." >&2
  RAW_BACKUPS=$( aws dynamodb list-backups --table-name "$TABLE" --output json 2>/dev/null || echo '{ "BackupSummaries": [] }' )
  if [[ -z "$RAW_BACKUPS" ]] || ! echo "$RAW_BACKUPS" | jq empty 2>/dev/null; then
    echo "  ⚠️  list-backups returned empty/invalid JSON; using '{\"BackupSummaries\":[]}'." >&2
    BACKUPS_JSON='{ "BackupSummaries": [] }'
  else
    BACKUPS_JSON="$RAW_BACKUPS"
  fi
  echo "  BACKUPS_JSON:" >&2
echo "$BACKUPS_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
  echo >&2

  # 3.6 Print all variables before building JSON object
  echo "  -> Debug: Variables before JSON assembly:" >&2
  echo "     TABLE: $TABLE" >&2
  echo "     DESC_JSON: $DESC_JSON" >&2
  echo "     TAGS_JSON: $TAGS_JSON" >&2
  echo "     TTL_JSON: $TTL_JSON" >&2
  echo "     GLOBAL_JSON: $GLOBAL_JSON" >&2
  echo "     BACKUPS_JSON: $BACKUPS_JSON" >&2
  echo >&2

  # 3.7 Build JSON object for this table
  echo "  -> Building JSON object for table $TABLE..." >&2
  TABLE_OBJ=$(jq -n \
    --arg name        "$TABLE" \
    --argjson desc    "$DESC_JSON" \
    --argjson tags    "$TAGS_JSON" \
    --argjson ttl     "$TTL_JSON" \
    --argjson global  "$GLOBAL_JSON" \
    --argjson backups "$BACKUPS_JSON" \
    '{
       tableName:          $name,
       description:        $desc.Table,
       tags:               ($tags.Tags // []),
       timeToLive:         $ttl.TimeToLiveDescription,
       globalTableInfo:    ($global.GlobalTableDescription // null),
       backups:            ($backups.BackupSummaries // [])
     }'
  )
  echo "  JSON object for table $TABLE built successfully." >&2

  # 3.8 Append this table object to the JSON array
  if [ "$first_table" = true ]; then
    printf "  %s" "$TABLE_OBJ" >> "$OUTPUT"
    first_table=false
    echo "  Appended first table object." >&2
  else
    printf ",\n  %s" "$TABLE_OBJ" >> "$OUTPUT"
    echo "  Appended subsequent table object." >&2
  fi

  echo "Finished processing table: $TABLE" >&2
  echo "----------------------------------------------" >&2
  echo >&2

done

# 4. Close the JSON array
printf "\n]\n" >> "$OUTPUT"
echo "Closed JSON array." >&2

echo "✅ Done. See full DynamoDB export in $OUTPUT." >&2
