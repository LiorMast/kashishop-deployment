import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Get the itemID from the query string parameters
        itemID = event['queryStringParameters'].get('itemid')
        if not itemID:
            return {
                'statusCode': 400,
                'body': json.dumps({"message": "Missing or invalid itemid in query parameters."})
            }

        # Get the DynamoDB table
        table = dynamodb.Table('Items')

        # Check if the item exists
        try:
            response = table.get_item(Key={"itemID": itemID})
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'body': json.dumps({"message": "Item not found."})
                }
        except ClientError as e:
            print(f"DynamoDB ClientError during get_item: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({"message": "An error occurred while checking item existence."})
            }

        # Parse the request body to get the updated item details
        request_body = json.loads(event['body'])
        required_fields = ["item_name", "isActive", "isSold", "seller", "image", "item_description", "price"]

        if not all(field in request_body for field in required_fields):
            return {
                'statusCode': 400,
                'body': json.dumps({"message": "Missing required fields in the request body."})
            }

        # Extract fields from the request body
        item_name = str(request_body["item_name"])
        isActive = str(request_body["isActive"])
        isSold = str(request_body["isSold"])
        seller = str(request_body["seller"])
        image = str(request_body["image"])
        item_description = str(request_body["item_description"])
        price = str(request_body["price"])

        # Update the item in the DynamoDB table
        update_expression = "SET item_name = :item_name, isActive = :isActive, isSold = :isSold, seller = :seller, image = :image, item_description = :item_description, price = :price"
        expression_attribute_values = {
            ":item_name": item_name,
            ":isActive": isActive,
            ":isSold": isSold,
            ":seller": seller,
            ":image": image,
            ":item_description": item_description,
            ":price": price
        }

        table.update_item(
            Key={"itemID": itemID},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )

        return {
            'statusCode': 200,
            'body': json.dumps({"message": "Item updated successfully."})
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"message": "An error occurred while updating the item."})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"message": "An unexpected error occurred."})
        }

        
        
# # Mock event for testing the lambda function
# test_event = {
#     'queryStringParameters': {
#         'itemid': '1337'
#     },
#     'body': json.dumps({
#         'item_name': 'Test Item',
#         'isActive': 'TRUE',
#         'isSold': 'FALSE',
#         'seller': '6',
#         'image': 'https://example.com/test-image.jpg',
#         'item_description': 'This is a test item description',
#         'price': 99.99
#     })
# }

# # Test the lambda function
# response = lambda_handler(test_event, None)
# print(response)