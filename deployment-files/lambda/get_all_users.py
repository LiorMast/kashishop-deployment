import boto3
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    items_table = dynamodb.Table('Items')
    users_table = dynamodb.Table('Users')

    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true'
    }

    try:
        # Fetch all users from the Users table
        users_response = users_table.scan()
        users = users_response.get('Items', [])

        enriched_users = []

        for user in users:
            user_id = user.get('userID', 'Unknown')
            username = user.get('username', 'Unknown')

            # Query Items table for active items by this user
            items_response = items_table.query(
                IndexName="seller-creationDate-index",
                KeyConditionExpression="seller = :seller_id",
                FilterExpression="isActive = :active_status",
                ExpressionAttributeValues={
                    ":seller_id": user_id,
                    ":active_status": True
                }
            )
            active_items_count = len(items_response.get('Items', []))

            # Add user data with items_for_sale
            enriched_users.append({
                "ID": user_id,
                "username": username,
                "full_name": user.get('name', 'N/A'),
                "phone_number": user.get('phone_number', 'N/A'),
                "items_for_sale": active_items_count,
                "join_date": user.get('creationDate', 'N/A'),
                "isActive": user.get('isActive')  # Assume email_verified indicates user activity
            })

        # Return the enriched users data
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(enriched_users, default=str)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Error retrieving users or items data',
                'error': str(e)
            })
        }
