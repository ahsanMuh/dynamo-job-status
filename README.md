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
from dynamo_job_status.dynamodb import create_job_log, update_job_status_by_id, JobStatus

# Create a new job
job_id = create_job_log(
    job_name="my-process-job",
    job_type="data-processing",
    input_key="input-file.csv",
    bucket_name="my-s3-bucket"
)

# Update job status
update_job_status_by_id(
    job_id=job_id, 
    status=JobStatus.PROCESSING
)

# Mark job as complete
update_job_status_by_id(
    job_id=job_id, 
    status=JobStatus.COMPLETE, 
    output_key="output-results.json"
)
```

## Features

- **Automatic Retries**: All DynamoDB operations are wrapped with exponential backoff retries
- **Job Status Tracking**: Easily track jobs through their lifecycle (PENDING, PROCESSING, COMPLETE, FAILED)
- **Simple API**: Straightforward functions for common DynamoDB operations
- **Type Hints**: Full type hinting for better IDE support

## Configuration

By default, the package uses the "workers-job-status" table name. You can override this by setting:

```python
from dynamo_job_status.dynamodb import set_table_name

set_table_name("my-custom-table-name")
```

## License

MIT