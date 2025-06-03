import boto3
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Table names
    items_table_name = "Items"
    users_table_name = "Users"

    # Access the DynamoDB tables
    items_table = dynamodb.Table(items_table_name)
    users_table = dynamodb.Table(users_table_name)

    try:
        # Scan the Items table
        items_response = items_table.scan()
        items = items_response['Items']

        # Convert all properties to strings and include sellerUsername
        updated_items = []

        for item in items:
            # Get the seller ID from the item
            seller_id = item.get('seller').strip()  # seller corresponds to userID in the Users table
            seller_username = "Unknown"  # Default value

            if seller_id:
                try:
                    # Query the GSI userID-index
                    user_response = users_table.query(
                        IndexName="userID-index",
                        KeyConditionExpression=boto3.dynamodb.conditions.Key('userID').eq(seller_id)
                    )
                    if user_response['Items']:
                        seller_username = user_response['Items'][0].get('username', "Unknown")
                except Exception as e:
                    print(f"Error querying userID-index with userID {seller_id}: {e}")

            # Convert all item properties to strings and add sellerUsername
            updated_item = {key: str(value) for key, value in item.items()}
            updated_item['sellerUsername'] = seller_username
            updated_items.append(updated_item)

        # Sort items by 'itemID' as a string
        updated_items = sorted(updated_items, key=lambda x: x['itemID'])

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps(updated_items)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'message': 'Error fetching items and usernames from DynamoDB',
                'error': str(e)
            })
        }

# # Mock test call to lambda_handler
# test_event = {}
# test_context = {}
# result = lambda_handler(test_event, test_context)
# print("Lambda handler response:")
# print(json.dumps(result, indent=2))
