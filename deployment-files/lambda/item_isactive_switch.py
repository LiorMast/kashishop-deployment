import boto3
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'Items'
    table = dynamodb.Table(table_name)

    try:
        # Parse the request body to get the itemID
        body = json.loads(event['body'])
        item_id = body.get('itemID')

        if not item_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'PUT, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                },
                'body': json.dumps({'message': 'Missing itemID in request body'})
            }

        # Retrieve the current item by itemID
        response = table.get_item(Key={'itemID': item_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'PUT, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                },
                'body': json.dumps({'message': 'Item not found'})
            }

        # Toggle the value of isActive
        current_is_active = item.get('isActive', 'false')
        new_is_active = "true" if current_is_active == "false" else "false"

        # Update the isActive value in the database
        table.update_item(
            Key={'itemID': item_id},
            UpdateExpression='SET isActive = :isActive',
            ExpressionAttributeValues={':isActive': new_is_active},
            ReturnValues='UPDATED_NEW'
        )

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'PUT, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                },
            'body': json.dumps({
                'message': 'Item updated successfully',
                'new_isActive': new_is_active
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'PUT, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': json.dumps({'message': str(e)})
        }