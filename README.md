# Redis DynamoDB Table Migrator

A utility to migrate data from a DynamoDB table to Redis in JSON format. This tool supports complex DynamoDB items, including nested maps, lists, and sets, making it easy to migrate data with minimal effort.

## 🚧 Status Panel

| **Status**         | **Reason**                                      | **Details**                                                              |
|---------------------|------------------------------------------------|---------------------------------------------------------------------------|
| 🛠 **Work in Progress** | Testing corner cases and weird DynamoDB nested structures | Ensuring all edge cases and complex data types are migrated successfully. |



## Features
- Handles DynamoDB's diverse data types (including nested structures).
- Converts DynamoDB items into Redis JSON objects.
- Supports pagination for large tables.
- Easily configurable using environment variables or CLI arguments.

---

## Quickstart

### 1. Build the Docker Image
Build the Docker image locally (if you don't already have it):

```bash
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile -t gacerioni/redis_dynamodb_table_migrator:0.0.1 --push .
```

### 2. Run the Migrator

Use the following command to migrate data from your DynamoDB table to Redis:
```bash
docker run --rm \
  -e DYNAMO_TABLE_NAME=gabs-migrator-table \
  -e REDIS_HOST=host.docker.internal \
  -e REDIS_PORT=6379 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY" \
  gacerioni/redis_dynamodb_table_migrator:0.0.1
```
### 3. CLI Options

You can also use CLI arguments if you prefer not to use environment variables:

```bash
docker run --rm gacerioni/redis_dynamodb_table_migrator:0.0.1 \
  --dynamo-table gabs-migrator-table \
  --redis-host host.docker.internal \
  --redis-port 6379 \
  --region us-east-1
```

## Environment Variables

| Variable              | Description                          | Default      |
|------------------------|--------------------------------------|--------------|
| `DYNAMO_TABLE_NAME`    | Name of the DynamoDB table.          | **Required** |
| `REDIS_HOST`           | Redis host address.                  | `localhost`  |
| `REDIS_PORT`           | Redis port number.                   | `6379`       |
| `AWS_REGION`           | AWS region of the DynamoDB table.    | `us-east-1`  |
| `AWS_ACCESS_KEY_ID`    | AWS access key ID.                   | `None`       |
| `AWS_SECRET_ACCESS_KEY`| AWS secret access key.               | `None`       |


### Notes
- Ensure Redis is accessible to the container. For Docker Desktop, use host.docker.internal for the REDIS_HOST.
- Validate your DynamoDB table permissions to ensure read access is available.

### Example Data

If you’d like to test with example data, you can use the provided script to populate your DynamoDB table:

```bash
python utils/add_items_to_dynamodb_table.py
```

This script generates a diverse dataset to test the migrator.


## License

This project is licensed under the MIT License.
