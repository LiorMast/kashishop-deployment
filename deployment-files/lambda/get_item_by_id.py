import boto3

def query_items_by_partition_key(table_name, partition_key_name, partition_key_value):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            KeyConditionExpression=f'{partition_key_name} = :val1',
            ExpressionAttributeValues={
                ':val1': partition_key_value  # Remove the {'S': ...} wrapper
            }
        )
    except Exception as e:
        # print(f"Error querying table: {e}")
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }

    return {
        'statusCode': 200,
        'body': response['Items']
    }
# Example usage:
# table_name = 'Items'
# partition_key_name = 'itemID'
# partition_key_value = '0'

# items = query_items_by_partition_key(table_name, partition_key_name, partition_key_value)

# for item in items:
#     print(item)