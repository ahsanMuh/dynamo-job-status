import unittest
from unittest.mock import patch, MagicMock
import boto3
from aws_dynamo_utils.dynamodb import (
    create_job_log,
    get_job_id_by_name,
    update_job_status_by_id,
    JobStatus,
    set_table_name
)


class TestDynamoUtils(unittest.TestCase):
    
    def setUp(self):
        # Set a test table name
        set_table_name("test-table")
        
        # Create a mock for the DynamoDB client
        self.mock_dynamo_patcher = patch('aws_dynamo_utils.dynamodb.dynamo_client')
        self.mock_dynamo = self.mock_dynamo_patcher.start()
        
    def tearDown(self):
        # Stop the patcher
        self.mock_dynamo_patcher.stop()
        
    def test_create_job_log(self):
        # Configure the mock
        self.mock_dynamo.put_item.return_value = {}
        
        # Call the function
        job_id = create_job_log(
            job_name="test-job",
            job_type="test-type",
            input_key="test-input.txt",
            bucket_name="test-bucket"
        )
        
        # Assert dynamo client was called with correct parameters
        self.mock_dynamo.put_item.assert_called_once()
        call_args = self.mock_dynamo.put_item.call_args[1]
        
        # Check table name
        self.assertEqual(call_args['TableName'], "test-table")
        
        # Check the job name in the item
        self.assertEqual(call_args['Item']['jobName']['S'], "test-job")
        
        # Check job ID was returned
        self.assertIsNotNone(job_id)
        
    def test_get_job_id_by_name_found(self):
        # Mock response for when job is found
        self.mock_dynamo.scan.return_value = {
            'Items': [{'id': {'S': 'test-uuid'}}]
        }
        
        # Call the function
        job_id = get_job_id_by_name("existing-job")
        
        # Verify correct result is returned
        self.assertEqual(job_id, "test-uuid")
        
    def test_get_job_id_by_name_not_found(self):
        # Mock response for when job is not found
        self.mock_dynamo.scan.return_value = {'Items': []}
        
        # Call the function
        job_id = get_job_id_by_name("non-existent-job")
        
        # Verify None is returned
        self.assertIsNone(job_id)
        
    def test_update_job_status(self):
        # Mock the update_item response
        self.mock_dynamo.update_item.return_value = {
            'Attributes': {
                'jobStatus': {'S': JobStatus.COMPLETE}
            }
        }
        
        # Call the function
        response = update_job_status_by_id(
            job_id="test-job-id",
            status=JobStatus.COMPLETE,
            output_key="test-output.json"
        )
        
        # Check dynamo client was called
        self.mock_dynamo.update_item.assert_called_once()
        
        # Verify response is returned correctly
        self.assertIn('Attributes', response)


if __name__ == "__main__":
    unittest.main()