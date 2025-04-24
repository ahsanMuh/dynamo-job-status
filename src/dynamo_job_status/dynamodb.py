import boto3
from datetime import datetime, UTC
import time
import uuid
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import functools
from typing import Optional, Dict, Any

# Default table name - can be overridden
TABLE_NAME = "workers-job-status"
dynamo_client = boto3.client('dynamodb')
DEBUG=False

class JobStatus:
    """Constants representing possible job states."""
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"


def set_table_name(table_name: str) -> None:
    """
    Set the DynamoDB table name to use for operations.
    
    Args:
        table_name: The name of the DynamoDB table
    """
    global TABLE_NAME
    TABLE_NAME = table_name
    print(f"DynamoDB table name set to: {TABLE_NAME}")


def set_debug(debug: bool) -> None:
    """
    Set the debug flag.
    
    Args:
        debug: The debug flag
    """
    global DEBUG
    DEBUG = debug
    print(f"Debug flag set to: {DEBUG}")

    
def set_dynamo_client(client: Any) -> None:
    """
    Set a custom DynamoDB client.
    
    Args:
        client: A boto3 DynamoDB client instance
    """
    global dynamo_client
    dynamo_client = client
    if DEBUG:
        print("Custom DynamoDB client set")


def with_exponential_backoff(max_attempts=3, min_wait=2, max_wait=10):
    """
    Generic decorator for DynamoDB operations with exponential backoff retry.
    
    Args:   
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
    """
    def decorator(func):
        @functools.wraps(func)
        @retry(
            retry=retry_if_exception_type(ClientError),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            reraise=True
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


@with_exponential_backoff()
def create_job_log(
    job_name: str,
    job_type: str,
    input_key: str,
    bucket_name: str,
) -> str:
    """
    Logs job status to a DynamoDB table with retries and exception handling.
    
    Args:
        job_name: The name of the job
        job_type: The type of the job
        input_key: The key of the input file
        bucket_name: The name of the bucket
        
    Returns:
        The ID of the job
    """
    # Generate a unique ID for each job
    job_id = str(uuid.uuid4())
    
    item = {
        'id': {'S': job_id},
        'jobName': {'S': job_name},
        'jobType': {'S': job_type},
        'inputKey': {'S': input_key},
        'bucketName': {'S': bucket_name},
        'jobStatus': {'S': JobStatus.PENDING},
        'createdAt': {'S': datetime.now(UTC).isoformat()},
        'updatedAt': {'S': datetime.now(UTC).isoformat()},
    }

    dynamo_client.put_item(TableName=TABLE_NAME, Item=item)
    if DEBUG:
        print(f"Log inserted successfully with ID: {job_id}")
    return job_id


@with_exponential_backoff()
def get_job_id_by_name(job_name: str) -> Optional[str]:
    """
    Searches DynamoDB table for a job by jobName and returns the matching id.
    
    Args:
        job_name: The name of the job
        
    Returns:
        The ID of the job or None if not found
    """
    # Use query with limit 1 since we expect only one record with this job name
    response = dynamo_client.scan(
        TableName=TABLE_NAME,
        FilterExpression="jobName = :job_name",
        ExpressionAttributeValues={":job_name": {"S": job_name}},
        ProjectionExpression="id",
        Limit=1  # Limit to just one item since job_name should be unique
    )
    
    items = response.get('Items', [])
    if not items:
        if DEBUG:
            print(f"No job found with name: {job_name}")
        return None
        
    # Return just the ID string instead of a list since we expect only one match
    job_id = items[0]["id"]["S"]
    if DEBUG:
        print(f"Found job with ID: {job_id}")
    return job_id


@with_exponential_backoff()
def update_job_status_by_id(
    job_id: str,
    status: str,
    message: Optional[str] = None,
    output_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates the jobStatus of an item identified by its id in DynamoDB.
    
    Args:
        job_id: The ID of the job
        status: The status of the job
        message: The message of the job
        output_key: The key of the output file
        
    Returns:
        The response from DynamoDB
    """
    # Start with basic update expression and values
    update_expression = "SET jobStatus = :status, updatedAt = :updated_at"
    expression_values = {
        ':status': {'S': status},
        ':updated_at': {'S': datetime.now(UTC).isoformat()}
    }
    
    # Conditionally add message if provided
    if message is not None:
        update_expression += ", message = :message"
        expression_values[':message'] = {'S': message}
    
    # Conditionally add output_key if provided
    if output_key is not None:
        update_expression += ", outputKey = :output_key"
        expression_values[':output_key'] = {'S': output_key}

    # if job ended, add completedAt
    if status == JobStatus.COMPLETE or status == JobStatus.FAILED:
        update_expression += ", completedAt = :completed_at"
        expression_values[':completed_at'] = {'S': datetime.now(UTC).isoformat()}
    
    response = dynamo_client.update_item(
        TableName=TABLE_NAME,
        Key={
            'id': {'S': job_id}
        },
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="UPDATED_NEW"
    )
    if DEBUG:
        print(f"Job status updated successfully")
    return response


@with_exponential_backoff()
def update_parent_job_id(
    job_id: str,
    input_key: str
) -> None:
    """
    Updates the parentJobId of an item identified by  `input_key` == parent_job[output_key].
    
    Args:
        job_id: The ID of the job
        input_key: The key of the input file

    Returns:
        True if the parent job id was updated, False otherwise
    """
    # get parent job id from dynamo
    response = dynamo_client.scan(
        TableName=TABLE_NAME,
        FilterExpression="outputKey = :output_key",
        ExpressionAttributeValues={":output_key": {"S": input_key}},
        ProjectionExpression="id"
    )
    print(f"🔍 Response: {response}")
    items = response.get('Items', [])
    if not items:
        if DEBUG:
            print(f"❌ No parent job found for input key: {input_key}")
        return False
    
    parent_job_id = items[0]["id"]["S"]
    
    # update item to have parentJobId
    dynamo_client.update_item(
        TableName=TABLE_NAME,
        Key={'id': {'S': job_id}},
        UpdateExpression="SET parentJobId = :parent_job_id",
        ExpressionAttributeValues={':parent_job_id': {'S': parent_job_id}}
    )
    if DEBUG:
        print(f"✅ Successfully updated parentJobId for job {job_id} to {parent_job_id}")
    return True
