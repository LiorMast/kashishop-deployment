import boto3
import json
from datetime import datetime

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Specify your DynamoDB table name
USER_TABLE = "Users"

# Reference to the DynamoDB table
user_table = dynamodb.Table(USER_TABLE)

def lambda_handler(event, context):
    # Extract user details from the Cognito event
    username = event['userName']  # Unique identifier for the user
    user_attributes = event['request']['userAttributes']
    
    # Get the current timestamp for the creationDate in the desired format
    creation_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')  # Format as YYYY-MM-DDTHH:MM:SS
    
    # Prepare the user data to insert into DynamoDB
    user_data = {
        'username': username,  # Use "username" as the key
        'userID': user_attributes.get('sub', 'Unknown'),  # 'sub' is the unique identifier in Cognito
        'email': user_attributes.get('email'),
        'email_verified': user_attributes.get('email_verified', 'false'),
        'name': user_attributes.get('name', 'Unknown'),
        'phone_number': user_attributes.get('phone_number', 'Unknown'),
        'address': user_attributes.get('address', 'Unknown'),
        'picture': user_attributes.get('picture', 'https://kashishop2.s3.us-east-1.amazonaws.com/images/profile-photos/default-user.png'),
        'creationDate': creation_date,  # Add the current creation date in the desired format
        'isActive': 'true'
    }

    try:
        # Add user to DynamoDB
        user_table.put_item(Item=user_data)
        print(f"User {username} added successfully to DynamoDB.")

        # Return the event back to Cognito
        return event

    except Exception as e:
        print(f"Error adding user {username} to DynamoDB: {str(e)}")
        raise