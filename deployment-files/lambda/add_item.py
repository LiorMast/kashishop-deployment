import boto3
import json
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

def lambda_handler(event, context):
    """
    Lambda function to add a new item to the DynamoDB table "Items".
    """
    
    dynamodb = boto3.resource('dynamodb')
    table_name = "Items"
    table = dynamodb.Table(table_name)

    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
            },
            'body': json.dumps({'message': 'CORS preflight request successful'})
        }

    try:
        # Extracting the item details from the event body
        item = json.loads(event['body'])

        # Validating required fields
        required_fields = ["item_name", "isActive", "seller", "image", "item_description", "price"]
        for field in required_fields:
            if field not in item:
                raise ValueError(f"Missing required field: {field}")

        # Adding timestamp if creationDate is not provided
        if not item.get("creationDate"):
            item["creationDate"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not item.get("itemID"):
            item["itemID"] = generate_uuid()

        # Putting the item into the DynamoDB table
        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
            },
            'body': json.dumps({'message': 'Item successfully added.', 'item': item})
        }

    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
            },
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
            },
            'body': json.dumps({'error': str(e)})
        }
