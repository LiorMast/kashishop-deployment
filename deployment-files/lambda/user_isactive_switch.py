import boto3
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'Users'
    table = dynamodb.Table(table_name)

    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'PUT, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true'
    }

    try:
        # Parse the request body to get the userID
        body = json.loads(event['body'])
        user_id = body.get('userID')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing userID in request body'})
            }

        # Query the user using the userID-index
        response = table.query(
            IndexName="userID-index",
            KeyConditionExpression="userID = :user_id",
            ExpressionAttributeValues={":user_id": user_id}
        )

        # Check if a user is found
        users = response.get('Items', [])
        if not users:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'message': 'User not found'})
            }

        user = users[0]
        username = user['username']  # Retrieve the username from the query result

        # Toggle the value of isActive
        current_is_active = user.get('isActive', 'false').lower()
        new_is_active = "true" if current_is_active == "false" else "false"

        # Update the isActive value in the database
        table.update_item(
            Key={'username': username},
            UpdateExpression='SET isActive = :isActive',
            ExpressionAttributeValues={':isActive': new_is_active},
            ReturnValues='UPDATED_NEW'
        )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'User updated successfully',
                'new_isActive': new_is_active
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': str(e)})
        }
