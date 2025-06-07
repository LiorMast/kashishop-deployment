#!/usr/bin/env python3
import boto3
import argparse

# This script enables CORS for all resources in an existing API Gateway REST API
# Usage: python enable_cors_apigw.py --api-id <API_ID> --region <REGION> --stage <STAGE_NAME>

CORS_HEADERS = {
    'Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
    'Access-Control-Allow-Origin': "'*'"
}

REQUEST_TEMPLATES = {
    'application/json': '{\"statusCode\": 200}'
}


def enable_cors_for_resource(api_client, rest_api_id, resource_id):
    # 1) Create or ensure OPTIONS method and its responses
    try:
        api_client.put_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
    except api_client.exceptions.ConflictException:
        pass

    try:
        api_client.put_integration(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates=REQUEST_TEMPLATES
        )
    except api_client.exceptions.ConflictException:
        pass

    try:
        api_client.put_method_response(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseModels={'application/json': 'Empty'},
            responseParameters={f'method.response.header.{k}': False for k in CORS_HEADERS}
        )
    except api_client.exceptions.ConflictException:
        pass

    try:
        api_client.put_integration_response(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={f'method.response.header.{k}': v for k, v in CORS_HEADERS.items()}
        )
    except api_client.exceptions.ConflictException:
        pass

    # 2) Patch existing non-OPTIONS methods
    try:
        resource = api_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)
    except api_client.exceptions.NotFoundException:
        return

    for method_name in resource.get('resourceMethods', {}):
        if method_name == 'OPTIONS':
            continue

        # Ensure MethodResponse exists for status 200 with CORS header
        try:
            api_client.put_method_response(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=method_name,
                statusCode='200',
                responseModels={'application/json': 'Empty'},
                responseParameters={'method.response.header.Access-Control-Allow-Origin': False}
            )
        except api_client.exceptions.ConflictException:
            pass
        except api_client.exceptions.NotFoundException:
            pass

        # Ensure IntegrationResponse for status 200 includes CORS header
        try:
            api_client.put_integration_response(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=method_name,
                statusCode='200',
                responseParameters={'method.response.header.Access-Control-Allow-Origin': CORS_HEADERS['Access-Control-Allow-Origin']},
                responseTemplates={'application/json': ''}
            )
        except api_client.exceptions.ConflictException:
            pass
        except api_client.exceptions.NotFoundException:
            pass


def main():
    parser = argparse.ArgumentParser(description='Enable CORS on all resources of an existing API Gateway REST API')
    parser.add_argument('--api-id', required=True, help='The ID of the REST API')
    parser.add_argument('--region', default='us-east-1', help='AWS region of the REST API')
    parser.add_argument('--stage', required=True, help='Stage name to redeploy after enabling CORS')
    args = parser.parse_args()

    client = boto3.client('apigateway', region_name=args.region)

    # 1) Get list of resources
    paginator = client.get_paginator('get_resources')
    page_iterator = paginator.paginate(restApiId=args.api_id)

    resource_ids = []
    for page in page_iterator:
        for item in page.get('items', []):
            resource_ids.append(item['id'])

    # 2) Enable CORS on each resource
    for res_id in resource_ids:
        print(f"Enabling CORS for resource: {res_id}")
        enable_cors_for_resource(client, args.api_id, res_id)

    # 3) Redeploy API to the specified stage
    try:
        response = client.create_deployment(
            restApiId=args.api_id,
            stageName=args.stage,
            description='Enable CORS on all resources'
        )
        print(f"Deployment created: {response['id']}")
    except Exception as e:
        print(f"Error creating deployment: {e}")


if __name__ == '__main__':
    main()
