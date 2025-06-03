#!/usr/bin/env bash
#
# Prerequisites:
# - AWS CLI v2 (configured with appropriate credentials/region)
# - `jq` (for JSON parsing)
#
# This script generates a file called `all_apis.json` containing an array of objects.
# Each object describes one API Gateway REST API in detail (resources, methods, integrations, etc.).

# 1. Start the JSON array
echo "[" > all_apis.json

# 2. Retrieve all APIs (paginated automatically by AWS CLI)
#    `get-rest-apis` returns a JSON with an "items" array of { id, name, ... } :contentReference[oaicite:0]{index=0}.
aws apigateway get-rest-apis --output json | jq -c '.items[]' | while read -r api; do
  # Extract the REST API’s ID and name
  API_ID=$(echo "$api" | jq -r '.id')
  API_NAME=$(echo "$api" | jq -r '.name')

  # 3. Get all resources for this API, embedding each resource’s methods:
  #    --embed=methods causes AWS to include “resourceMethods” for each resource :contentReference[oaicite:1]{index=1}.
  RESOURCES=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --embed methods \
    --output json)

  # 4. Get this API’s authorizers (if any) :contentReference[oaicite:2]{index=2}.
  AUTHORIZERS=$(aws apigateway get-authorizers \
    --rest-api-id "$API_ID" \
    --output json)

  # 5. Get this API’s models (if any) :contentReference[oaicite:3]{index=3}.
  MODELS=$(aws apigateway get-models \
    --rest-api-id "$API_ID" \
    --output json)

  # 6. Get this API’s stages (deployment stages, e.g., “dev”, “prod”) :contentReference[oaicite:4]{index=4}.
  STAGES=$(aws apigateway get-stages \
    --rest-api-id "$API_ID" \
    --output json)

  # 7. Get this API’s deployments (historical deployments) :contentReference[oaicite:5]{index=5}.
  DEPLOYMENTS=$(aws apigateway get-deployments \
    --rest-api-id "$API_ID" \
    --output json)

  # 8. Build one JSON object that wraps all of the above for this API.
  #    We pull out the “.items” arrays where appropriate so the final structure is more compact.
  API_OBJ=$(jq -n \
    --arg id "$API_ID" \
    --arg name "$API_NAME" \
    --argjson resources "$(echo "$RESOURCES"   | jq '.items')" \
    --argjson authorizers "$(echo "$AUTHORIZERS" | jq '.items')" \
    --argjson models "$(echo "$MODELS"         | jq '.items')" \
    --argjson stages "$(echo "$STAGES"         | jq '.item')" \
    --argjson deployments "$(echo "$DEPLOYMENTS"| jq '.items')" \
    '{
      apiId:       $id,
      name:        $name,
      resources:   $resources,
      authorizers: $authorizers,
      models:      $models,
      stages:      $stages,
      deployments: $deployments
    }')

  # 9. Append a comma if this is not the first object; otherwise just print the object.
  if grep -q '"apiId"' all_apis.json; then
    # already added at least one API → prefix with comma
    printf ",\n%s" "$API_OBJ" >> all_apis.json
  else
    # first API: no leading comma
    printf "\n%s" "$API_OBJ" >> all_apis.json
  fi
done

# 10. Close the JSON array and newline
echo -e "\n]" >> all_apis.json

echo "Done. See detailed API descriptions in all_apis.json."
