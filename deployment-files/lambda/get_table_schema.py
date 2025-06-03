import boto3

def get_table_schema(table_name):
    """
    Retrieves the schema of a specified DynamoDB table.

    Args:
        table_name: The name of the DynamoDB table.

    Returns:
        A dictionary containing the table schema information, 
        including attribute definitions, key schema, and more. 
        Returns None if the table does not exist.
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        table_description = table.describe_table()
        return table_description
    except Exception as e:
        print(f"Error getting table schema: {e}")
        return None

# Example Usage:
table_name = 'Items'
table_schema = get_table_schema(table_name)

if table_schema:
    print("Table Schema:")
    print(table_schema)
else:
    print(f"Table '{table_name}' not found.")