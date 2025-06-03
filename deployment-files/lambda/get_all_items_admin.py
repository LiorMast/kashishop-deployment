import boto3
import json
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    
    items_table_name = 'Items'
    users_table_name = 'Users'
    items_table = dynamodb.Table(items_table_name)
    users_table = dynamodb.Table(users_table_name)

    try:
        logger.info("Fetching all items from Items table...")
        
        # Scan the Items table to retrieve all items
        response = items_table.scan()
        items = response.get('Items', [])

        enriched_items = []

        # Enrich each item with user details
        for item in items:
            seller_id = item.get('seller', 'Unknown')
            poster_username = 'Unknown'

            # Fetch the username from the Users table using a scan
            if seller_id != 'Unknown':
                user_response = users_table.scan(
                    FilterExpression="userID = :user_id",
                    ExpressionAttributeValues={":user_id": seller_id}
                )
                user = user_response.get('Items', [])
                if user:
                    poster_username = user[0].get('username', 'Unknown')

            # Append the enriched item data
            enriched_items.append({
                "itemID": item.get('itemID', 'Undefined'),
                "name": item.get('item_name', 'Unnamed'),
                "description": item.get('item_description', 'No description available'),
                "price": item.get('price', 0),
                "poster_username": poster_username,
                "poster_id": seller_id,  # Keep the seller's userID as the poster ID
                "isActive": item.get('isActive', 'false'),
                "isSold": item.get('isSold', 'false')
            })

        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps(enriched_items, default=str)
        }

    except Exception as e:
        logger.error("Error: %s", str(e))  # Log the error
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'message': 'Error retrieving items',
                'error': str(e)
            })
        }
