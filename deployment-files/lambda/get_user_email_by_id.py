import boto3
import json

def lambda_handler(event, context):
    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    users_table = dynamodb.Table('Users')

    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true'
    }

    try:
        # Get userID from query string parameters
        user_id = event['queryStringParameters'].get('userID')
        if not user_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing userID parameter'})
            }

        # Scan the Users table to find the user with the given userID
        response = users_table.scan(
            FilterExpression="userID = :user_id",
            ExpressionAttributeValues={
                ":user_id": user_id
            }
        )

        # Extract the user details
        users = response.get('Items', [])
        if not users:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'User not found'})
            }

        # Get the email address from the first matching user
        user = users[0]
        email = user.get('email', 'Email not found')

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'email': email})
        }

    except Exception as e:
        # Handle unexpected errors
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to process request', 'details': str(e)})
        }
