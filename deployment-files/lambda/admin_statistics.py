import boto3
import json
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    
    items_table = dynamodb.Table('Items')
    users_table = dynamodb.Table('Users')
    transactions_table = dynamodb.Table('TransactionHistory')

    try:
        # Scan the Items table to count the total number of items
        items_response = items_table.scan()
        items = items_response.get('Items', [])
        total_items = len(items)

        # Scan the Users table to count the total number of users
        users_response = users_table.scan()
        users = users_response.get('Items', [])
        total_users = len(users)

        # Find the user with the most items
        user_items_count = {}
        for item in items:
            seller_id = item.get('seller', 'Unknown')
            user_items_count[seller_id] = user_items_count.get(seller_id, 0) + 1

        user_with_most_items = max(user_items_count, key=user_items_count.get, default=None)
        user_with_most_items_count = user_items_count.get(user_with_most_items, 0)
        user_with_most_items_data = next(
            (user for user in users if user.get('userID') == user_with_most_items), None
        )
        most_items_username = user_with_most_items_data.get('username', 'Unknown') if user_with_most_items_data else 'Unknown'

        # Find the user with the most purchases (status "accepted")
        transactions_response = transactions_table.scan()
        transactions = transactions_response.get('Items', [])
        user_purchase_count = {}
        for transaction in transactions:
            if transaction.get('status') == 'accepted':
                buyer_id = transaction.get('buyerID', 'Unknown')
                user_purchase_count[buyer_id] = user_purchase_count.get(buyer_id, 0) + 1

        user_with_most_purchases = max(user_purchase_count, key=user_purchase_count.get, default=None)
        user_with_most_purchases_count = user_purchase_count.get(user_with_most_purchases, 0)
        user_with_most_purchases_data = next(
            (user for user in users if user.get('userID') == user_with_most_purchases), None
        )
        most_purchases_username = user_with_most_purchases_data.get('username', 'Unknown') if user_with_most_purchases_data else 'Unknown'

        # Build the response
        result = {
            "total_items": total_items,
            "total_users": total_users,
            "user_with_most_items": {
                "username": most_items_username,
                "userID": user_with_most_items,
                "item_count": user_with_most_items_count
            },
            "user_with_most_purchases": {
                "username": most_purchases_username,
                "userID": user_with_most_purchases,
                "purchase_count": user_with_most_purchases_count
            }
        }

        # Return success response with CORS headers
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps(result, default=str)
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
                'message': 'Error retrieving data',
                'error': str(e)
            })
        }