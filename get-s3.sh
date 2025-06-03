#!/usr/bin/env bash
#
# This script exports all S3 bucket configurations into a single JSON file named “s3_full.json.”
# It gathers each bucket’s settings (location, versioning, encryption, lifecycle, tags, CORS, policy,
# ACL, website configuration, logging, replication, notification configuration). Debug prints go to stderr.
# Added robust checks so that empty or invalid JSON is always replaced by a fallback.
#
# Prerequisites:
#  • AWS CLI v2 (configured with credentials & region)
#  • jq
#
# Usage:
#  chmod +x get-s3.sh
#  ./get-s3.sh
#

set -euo pipefail

OUTPUT="s3_full.json"

echo "=== Starting S3 export script ===" >&2
echo "Output will be written to: $OUTPUT" >&2
echo >&2

# 1. Start the JSON array in the output file
printf '[\n' > "$OUTPUT"
first_bucket=true

# 2. List all S3 buckets
echo "Listing all S3 buckets..." >&2
RAW_BUCKET_LIST=$( aws s3api list-buckets --output json 2>/dev/null || echo '{ "Buckets": [] }' )
if [[ -z "$RAW_BUCKET_LIST" ]] || ! echo "$RAW_BUCKET_LIST" | jq empty 2>/dev/null; then
  echo "⚠️  list-buckets returned empty or invalid JSON; defaulting to empty list." >&2
  BUCKET_LIST_JSON='{ "Buckets": [] }'
else
  BUCKET_LIST_JSON="$RAW_BUCKET_LIST"
fi

echo "Raw list-buckets response (or fallback):" >&2
echo "$BUCKET_LIST_JSON" | jq . 2>/dev/null >&2 || echo "(could not parse JSON)" >&2
echo >&2

# 3. Iterate over each bucket name
echo "Iterating over each bucket..." >&2
echo "$BUCKET_LIST_JSON" | jq -r '.Buckets[].Name' | while read -r BUCKET; do
  echo "----------------------------------------------" >&2
  echo "Processing bucket: $BUCKET" >&2

  #
  # 3.1 Location
  #
  echo "  -> Getting bucket location..." >&2
  RAW_LOCATION=$( aws s3api get-bucket-location --bucket "$BUCKET" --output json 2>/dev/null \
                     || echo '{ "LocationConstraint": null }' )
  if [[ -z "$RAW_LOCATION" ]] || ! echo "$RAW_LOCATION" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-location returned empty/invalid JSON; using '{\"LocationConstraint\":null}' as fallback." >&2
    LOCATION_JSON='{ "LocationConstraint": null }'
  else
    LOCATION_JSON="$RAW_LOCATION"
  fi
  echo "  LOCATION_JSON:" >&2
  echo "$LOCATION_JSON" >&2
  echo >&2

  #
  # 3.2 Versioning configuration
  #
  echo "  -> Getting bucket versioning configuration..." >&2
  RAW_VERSIONING=$( aws s3api get-bucket-versioning --bucket "$BUCKET" --output json 2>/dev/null \
                     || echo '{ }' )
  if [[ -z "$RAW_VERSIONING" ]] || ! echo "$RAW_VERSIONING" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-versioning returned empty/invalid JSON; using '{}' as fallback." >&2
    VERSIONING_JSON='{ }'
  else
    VERSIONING_JSON="$RAW_VERSIONING"
  fi
  echo "  VERSIONING_JSON:" >&2
  echo "$VERSIONING_JSON" >&2
  echo >&2

  #
  # 3.3 Encryption configuration
  #
  echo "  -> Getting bucket encryption configuration..." >&2
  RAW_ENCRYPTION=$( aws s3api get-bucket-encryption --bucket "$BUCKET" --output json 2>/dev/null \
                     || echo '{ }' )
  if [[ -z "$RAW_ENCRYPTION" ]] || ! echo "$RAW_ENCRYPTION" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-encryption returned empty/invalid JSON; using '{}' as fallback." >&2
    ENCRYPTION_JSON='{ }'
  else
    ENCRYPTION_JSON="$RAW_ENCRYPTION"
  fi
  echo "  ENCRYPTION_JSON:" >&2
  echo "$ENCRYPTION_JSON" >&2
  echo >&2

  #
  # 3.4 Lifecycle configuration
  #
  echo "  -> Getting bucket lifecycle configuration..." >&2
  RAW_LIFECYCLE=$( aws s3api get-bucket-lifecycle-configuration --bucket "$BUCKET" --output json 2>/dev/null \
                     || echo '{ }' )
  if [[ -z "$RAW_LIFECYCLE" ]] || ! echo "$RAW_LIFECYCLE" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-lifecycle-configuration returned empty/invalid JSON; using '{}' as fallback." >&2
    LIFECYCLE_JSON='{ }'
  else
    LIFECYCLE_JSON="$RAW_LIFECYCLE"
  fi
  echo "  LIFECYCLE_JSON:" >&2
  echo "$LIFECYCLE_JSON" >&2
  echo >&2

  #
  # 3.5 Tags
  #
  echo "  -> Getting bucket tags..." >&2
  RAW_TAGS=$( aws s3api get-bucket-tagging --bucket "$BUCKET" --output json 2>/dev/null \
               | jq '{ TagSet: .TagSet }' 2>/dev/null \
               || echo '{ "TagSet": [] }' )
  if [[ -z "$RAW_TAGS" ]] || ! echo "$RAW_TAGS" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-tagging returned empty/invalid JSON; using '{\"TagSet\":[]}' as fallback." >&2
    TAGS_JSON='{ "TagSet": [] }'
  else
    TAGS_JSON="$RAW_TAGS"
  fi
  echo "  TAGS_JSON:" >&2
  echo "$TAGS_JSON" >&2
  echo >&2

  #
  # 3.6 CORS configuration
  #
  echo "  -> Getting bucket CORS configuration..." >&2
  RAW_CORS=$( aws s3api get-bucket-cors --bucket "$BUCKET" --output json 2>/dev/null \
               || echo '{ "CORSRules": [] }' )
  if [[ -z "$RAW_CORS" ]] || ! echo "$RAW_CORS" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-cors returned empty/invalid JSON; using '{\"CORSRules\":[]}' as fallback." >&2
    CORS_JSON='{ "CORSRules": [] }'
  else
    CORS_JSON="$RAW_CORS"
  fi
  echo "  CORS_JSON:" >&2
  echo "$CORS_JSON" >&2
  echo >&2

  #
  # 3.7 Policy
  #
  echo "  -> Getting bucket policy..." >&2
  RAW_POLICY=$( aws s3api get-bucket-policy --bucket "$BUCKET" --output json 2>/dev/null \
                 | jq '{ Policy: .Policy }' 2>/dev/null \
                 || echo '{ "Policy": null }' )
  if [[ -z "$RAW_POLICY" ]] || ! echo "$RAW_POLICY" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-policy returned empty/invalid JSON; using '{\"Policy\":null}' as fallback." >&2
    POLICY_JSON='{ "Policy": null }'
  else
    POLICY_JSON="$RAW_POLICY"
  fi
  echo "  POLICY_JSON:" >&2
  echo "$POLICY_JSON" >&2
  echo >&2

  #
  # 3.8 ACL
  #
  echo "  -> Getting bucket ACL..." >&2
  RAW_ACL=$( aws s3api get-bucket-acl --bucket "$BUCKET" --output json 2>/dev/null \
               || echo '{ }' )
  if [[ -z "$RAW_ACL" ]] || ! echo "$RAW_ACL" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-acl returned empty/invalid JSON; using '{}' as fallback." >&2
    ACL_JSON='{ }'
  else
    ACL_JSON="$RAW_ACL"
  fi
  echo "  ACL_JSON:" >&2
  echo "$ACL_JSON" >&2
  echo >&2

  #
  # 3.9 Website configuration
  #
  echo "  -> Getting bucket website configuration..." >&2
  RAW_WEBSITE=$( aws s3api get-bucket-website --bucket "$BUCKET" --output json 2>/dev/null \
                   || echo '{ }' )
  if [[ -z "$RAW_WEBSITE" ]] || ! echo "$RAW_WEBSITE" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-website returned empty/invalid JSON; using '{}' as fallback." >&2
    WEBSITE_JSON='{ }'
  else
    WEBSITE_JSON="$RAW_WEBSITE"
  fi
  echo "  WEBSITE_JSON:" >&2
  echo "$WEBSITE_JSON" >&2
  echo >&2

  #
  # 3.10 Logging configuration
  #
  echo "  -> Getting bucket logging configuration..." >&2
  RAW_LOGGING=$( aws s3api get-bucket-logging --bucket "$BUCKET" --output json 2>/dev/null \
                  || echo '{ }' )
  if [[ -z "$RAW_LOGGING" ]] || ! echo "$RAW_LOGGING" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-logging returned empty/invalid JSON; using '{}' as fallback." >&2
    LOGGING_JSON='{ }'
  else
    LOGGING_JSON="$RAW_LOGGING"
  fi
  echo "  LOGGING_JSON:" >&2
  echo "$LOGGING_JSON" >&2
  echo >&2

  #
  # 3.11 Replication configuration
  #
  echo "  -> Getting bucket replication configuration..." >&2
  RAW_REPLICATION=$( aws s3api get-bucket-replication --bucket "$BUCKET" --output json 2>/dev/null \
                     || echo '{ }' )
  if [[ -z "$RAW_REPLICATION" ]] || ! echo "$RAW_REPLICATION" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-replication returned empty/invalid JSON; using '{}' as fallback." >&2
    REPLICATION_JSON='{ }'
  else
    REPLICATION_JSON="$RAW_REPLICATION"
  fi
  echo "  REPLICATION_JSON:" >&2
  echo "$REPLICATION_JSON" >&2
  echo >&2

  #
  # 3.12 Notification configuration
  #
  echo "  -> Getting bucket notification configuration..." >&2
  RAW_NOTIFICATION=$( aws s3api get-bucket-notification-configuration --bucket "$BUCKET" --output json 2>/dev/null \
                       || echo '{ }' )
  if [[ -z "$RAW_NOTIFICATION" ]] || ! echo "$RAW_NOTIFICATION" | jq empty 2>/dev/null; then
    echo "  ⚠️  get-bucket-notification-configuration returned empty/invalid JSON; using '{}' as fallback." >&2
    NOTIFICATION_JSON='{ }'
  else
    NOTIFICATION_JSON="$RAW_NOTIFICATION"
  fi
  echo "  NOTIFICATION_JSON:" >&2
  echo "$NOTIFICATION_JSON" >&2
  echo >&2

  #
  # 3.13 Build the JSON object for this bucket
  #
  echo "  -> Final variables before jq -n (step 3.13):" >&2
  echo "       bucketName         = $BUCKET" >&2
  echo "       LOCATION_JSON      = $LOCATION_JSON" >&2
  echo "       VERSIONING_JSON    = $VERSIONING_JSON" >&2
  echo "       ENCRYPTION_JSON    = $ENCRYPTION_JSON" >&2
  echo "       LIFECYCLE_JSON     = $LIFECYCLE_JSON" >&2
  echo "       TAGS_JSON          = $TAGS_JSON" >&2
  echo "       CORS_JSON          = $CORS_JSON" >&2
  echo "       POLICY_JSON        = $POLICY_JSON" >&2
  echo "       ACL_JSON           = $ACL_JSON" >&2
  echo "       WEBSITE_JSON       = $WEBSITE_JSON" >&2
  echo "       LOGGING_JSON       = $LOGGING_JSON" >&2
  echo "       REPLICATION_JSON   = $REPLICATION_JSON" >&2
  echo "       NOTIFICATION_JSON  = $NOTIFICATION_JSON" >&2
  echo >&2

  echo "  -> Building JSON object for bucket $BUCKET..." >&2
  BUCKET_OBJ=$(jq -n \
    --arg name             "$BUCKET" \
    --argjson location     "$LOCATION_JSON" \
    --argjson versioning   "$VERSIONING_JSON" \
    --argjson encryption   "$ENCRYPTION_JSON" \
    --argjson lifecycle    "$LIFECYCLE_JSON" \
    --argjson tags         "$TAGS_JSON" \
    --argjson cors         "$CORS_JSON" \
    --argjson policy       "$POLICY_JSON" \
    --argjson acl          "$ACL_JSON" \
    --argjson website      "$WEBSITE_JSON" \
    --argjson logging      "$LOGGING_JSON" \
    --argjson replication  "$REPLICATION_JSON" \
    --argjson notification "$NOTIFICATION_JSON" \
    '{
       bucketName:               $name,
       location:                 $location,
       versioning:               $versioning,
       encryption:               $encryption,
       lifecycleConfiguration:   $lifecycle,
       tags:                     $tags,
       corsConfiguration:        $cors,
       policy:                   $policy,
       acl:                      $acl,
       websiteConfiguration:     $website,
       loggingConfiguration:     $logging,
       replicationConfiguration: $replication,
       notificationConfiguration: $notification
     }'
  )
  echo "  JSON object for bucket $BUCKET built successfully." >&2

  #
  # 3.14 Append this bucket object to the JSON array
  #
  if [ "$first_bucket" = true ]; then
    printf "  %s" "$BUCKET_OBJ" >> "$OUTPUT"
    first_bucket=false
    echo "  Appended first bucket object." >&2
  else
    printf ",\n  %s" "$BUCKET_OBJ" >> "$OUTPUT"
    echo "  Appended subsequent bucket object." >&2
  fi

  echo "Finished processing bucket: $BUCKET" >&2
  echo "----------------------------------------------" >&2
  echo >&2
done

# 4. Close the JSON array
printf "\n]\n" >> "$OUTPUT"
echo "Closed JSON array." >&2

echo "✅ Done. See full S3 export in $OUTPUT." >&2
