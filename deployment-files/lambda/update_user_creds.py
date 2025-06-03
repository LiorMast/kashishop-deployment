import boto3
import json
from boto3.dynamodb.conditions import Attr

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('Users')
cognito_client = boto3.client('cognito-idp')

USER_POOL_ID = 'us-east-1_dhjcBYrYa'

def lambda_handler(event, context):
    # Handle preflight CORS requests
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            },
            'body': json.dumps({'message': 'CORS preflight successful'}),
        }
    
    try:
        # Parse input data
        body = json.loads(event['body'])
        email = body.get('email')
        phone_number = body.get('phone_number')
        password = body.get('password')
        photo_url = body.get('photo_url')
        current_user_id = body.get('userID')

        # Update Cognito attributes
        cognito_attributes = []
        if email:
            cognito_attributes.append({'Name': 'email', 'Value': email})
        if phone_number:
            cognito_attributes.append({'Name': 'phone_number', 'Value': phone_number})
        if photo_url:
            cognito_attributes.append({'Name': 'custom:photo', 'Value': photo_url})
        # if password:
        #     cognito_client.admin_set_user_password(
        #         UserPoolId=USER_POOL_ID,
        #         Username=current_user_id,
        #         Password=password,
        #         Permanent=True
        #     )

        # if cognito_attributes:
        #     cognito_client.admin_update_user_attributes(
        #         UserPoolId=USER_POOL_ID,
        #         Username=current_user_id,
        #         UserAttributes=cognito_attributes
        #     )

        # Update DynamoDB
        update_expression = []
        expression_values = {}
        if email:
            update_expression.append("email = :email")
            expression_values[':email'] = email
        if phone_number:
            update_expression.append("phone_number = :phone")
            expression_values[':phone'] = phone_number
        if photo_url:
            update_expression.append("photo = :photo")
            expression_values[':photo'] = photo_url

        if update_expression:
            users_table.update_item(
                Key={'username': current_user_id},
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeValues=expression_values
            )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',  # Allow all origins
            },
            'body': json.dumps({'message': 'Profile updated successfully.'}),
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',  # Allow all origins
            },
            'body': json.dumps({'error': str(e)}),
        }
        
        
# Mock event for testing the lambda function
test_event = {
    'httpMethod': 'POST',
    'body': json.dumps({
        'email': 'test@example.com',
        'phone_number': '+1234567890',
        'photo_url': 'https://example.com/photo.jpg',
        'userID': '0408e418-e061-7026-a190-dfd66d5734dc'
    })
}

# Call the lambda handler with mock event
response = lambda_handler(test_event, None)
print(response)