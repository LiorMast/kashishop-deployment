import boto3
import base64
import json
import mimetypes

s3 = boto3.client('s3')

def get_content_type(image_name):
    # Use mimetypes library to guess the MIME type based on the file extension
    mime_type, _ = mimetypes.guess_type(image_name)
    if not mime_type:
        # Default to image/jpeg if MIME type can't be guessed
        mime_type = "image/jpeg"
    return mime_type

def lambda_handler(event, context):
    BUCKET_NAME = "kashishop2"  # Corrected bucket name
    
    # Handle OPTIONS preflight request
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
        # Parse the body from JSON string to dictionary
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        image_name = body.get('imageName')
        image_base64 = body.get('imageBase64')
        destination_folder = body.get('destinationFolder')
        
        if not image_name or not image_base64 or not destination_folder:
            return {
                "statusCode": 400,
                "headers": {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Credentials': 'true',
                },
                "body": json.dumps({"error": "imageName, imageBase64, and destinationFolder are required"})
            }
        
        # Decode the base64 image data
        image_data = base64.b64decode(image_base64)
        content_type = get_content_type(image_name)
        object_key = f"{destination_folder}/{image_name}"
        
        # Upload the image to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=object_key,
            Body=image_data,
            ContentType=content_type,
            ACL="public-read"  # Make the object publicly readable
        )
        
        # Generate the public URL
        image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_key}"
        
        print(f"Image URL: {image_url}")
        
        return {
            "statusCode": 200,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
            },
            "body": json.dumps({"imageUrl": image_url})
        }
    
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Credentials': 'true',
            },
            "body": json.dumps({"error": "Failed to upload image", "details": str(e)})
        }
