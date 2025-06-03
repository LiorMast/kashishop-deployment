import boto3
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    transactions_table = dynamodb.Table('TransactionHistory')
    items_table = dynamodb.Table('Items')
    users_table = dynamodb.Table('Users')

    # Add CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true'
    }

    try:
        # Get userID from query string
        user_id = event['queryStringParameters'].get('userID')
        if not user_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing userID parameter'})
            }

        # Query the Transactions table with status="accepted"
        response = transactions_table.scan(
            FilterExpression="(buyerID = :user_id OR sellerID = :user_id) AND #status = :accepted_status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":user_id": user_id,  # Ensure user_id is passed as a string
                ":accepted_status": "accepted"
            }
        )
        transactions = response.get('Items', [])

        # Enrich transactions with item and user details
        enriched_transactions = []
        for transaction in transactions:
            is_buyer = transaction['buyerID'] == user_id
            other_user_id = transaction['sellerID'] if is_buyer else transaction['buyerID']

            # Fetch item details
            item_response = items_table.get_item(Key={'itemID': transaction['ItemID']})
            item = item_response.get('Item', {})
            item_name = item.get('item_name', 'Unknown Item')
            item_price = item.get('price', 'Unknown Price')

            # Fetch username of the other user
            user_response = users_table.scan(
                FilterExpression="userID = :user_id",
                ExpressionAttributeValues={":user_id": other_user_id}
            )
            other_user = user_response.get('Items', [{}])[0]
            other_username = other_user.get('username', 'Unknown User')

            # Build enriched transaction
            enriched_transaction = {
                'transactionID': transaction['transactionID'],
                'itemID': transaction['ItemID'],
                'state': 'bought' if is_buyer else 'sold',
                'itemName': item_name,
                'itemPrice': item_price,
                'transactionDate': transaction['transactionDate'],
                'buyerOrSellerID': other_user_id,
                'buyerOrSellerName': other_username
            }
            enriched_transactions.append(enriched_transaction)

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(enriched_transactions)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to process request', 'details': str(e)})
        }
