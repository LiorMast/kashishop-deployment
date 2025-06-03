# This script lists all DynamoDB tables and retrieves their descriptions,
# saving the output to dyn_db.json.
# Ensure you have the AWS CLI and jq installed to run this script.
# Usage: Save this script as get-dynamodb.sh and run it in a terminal with AWS CLI configured.
# Make sure to give execute permission to the script:
# chmod +x get-dynamodb.sh
# Note: The script assumes you have the necessary permissions to list and describe DynamoDB tables.

#!/bin/bash
aws dynamodb list-tables --output json \
  | jq -r '.TableNames[]' \
  | xargs -n1 -I{} aws dynamodb describe-table --table-name {} --output json \
  | jq -s '.' > dyn_db.json
echo "DynamoDB tables and their descriptions have been saved to dyn_db.json"