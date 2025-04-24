# Dynamo Job Status

A utility package for working with AWS DynamoDB job status tracking, featuring:

- Automatic retries with exponential backoff
- Error handling
- Job status tracking
- Simple API for common DynamoDB operations

## Installation

```bash
pip install git+https://github.com/ahsanMuh/dynamo-job-status.git
```

## Usage

```python
from dynamo_job_status.dynamodb import create_job_log, update_job_status_by_id, update_parent_job_id, JobStatus, set_table_name

# Set custom table name (optional)
# By default, the package uses "workers-job-status" table
set_table_name("my-custom-table-name")

# Create a new job
job_id = create_job_log(
    job_name="my-process-job",
    job_type="data-processing",
    input_key="your-s3-input-file-path",
    bucket_name="my-s3-bucket"
)



# Update job status
update_job_status_by_id(
    job_id=job_id, 
    status=JobStatus.PROCESSING,
    message=None,  # Optional: Add a message about the job status
    output_key=None  # Optional: The S3 key where output is stored
)

# Mark job as complete
update_job_status_by_id(
    job_id=job_id, 
    status=JobStatus.COMPLETE, 
    output_key="your-s3-output-file-path"
)

# Set parent job relationship
from dynamo_job_status.dynamodb import update_parent_job_id

update_parent_job_id(
    job_id=job_id,
    input_key="your-s3-input-file-path"  # This should match a previous job's output_key
)
```

## Features

- **Automatic Retries**: All DynamoDB operations are wrapped with exponential backoff retries
- **Job Status Tracking**: Easily track jobs through their lifecycle (PENDING, PROCESSING, COMPLETE, FAILED)
- **Job Relationships**: Track parent-child relationships between jobs in a workflow
- **Simple API**: Straightforward functions for common DynamoDB operations
- **Type Hints**: Full type hinting for better IDE support

## License

MIT