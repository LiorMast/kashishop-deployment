import boto3
import csv

def import_csv_to_dynamodb(csv_file, table_name):
    """
    Imports data from a CSV file into a specified DynamoDB table.

    Args:
        csv_file (str): Path to the CSV file.
        table_name (str): Name of the DynamoDB table.
    """

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # row['itemID'] = int(row['itemID'])
            # print(row)
            try:
                table.put_item(Item=row)
                print(f"Successfully imported row: {row}")
            except Exception as e:
                print(f"Error importing row: {row} - {e}")

# Example usage:
# csv_file_path = 'path/to/your/data.csv'
# dynamodb_table_name = 'your_dynamodb_table_name'
import_csv_to_dynamodb("items_2.csv", "Items")

# aws s3api list-objects --bucket kashishop --prefix images/item-images --output text | awk '{print "https://" $3}'