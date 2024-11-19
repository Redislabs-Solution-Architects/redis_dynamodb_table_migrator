import os
import boto3
import redis
import argparse
import logging
import time
import json
from boto3.dynamodb.types import Binary
from decimal import Decimal
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_aws_session():
    """Initialize a boto3 session using token, env vars, or EC2 IAM role."""
    try:
        session = boto3.Session()
        logger.info("Successfully initialized AWS session.")
        return session
    except NoCredentialsError as e:
        logger.error("AWS credentials not found: %s", e)
        raise
    except PartialCredentialsError as e:
        logger.error("Incomplete AWS credentials: %s", e)
        raise


def connect_dynamodb(table_name, region=None):
    """Connect to DynamoDB and return the specified table."""
    try:
        session = get_aws_session()
        dynamodb = session.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)

        if not table.key_schema:
            raise ValueError(f"Table {table_name} does not have a valid key schema.")
        logger.info("Connected to DynamoDB table: %s", table_name)
        return table
    except Exception as e:
        logger.error("Error connecting to DynamoDB: %s", e)
        raise


def connect_redis(host, port, db, password=None):
    """Connect to Redis and return the connection object."""
    try:
        pool = redis.ConnectionPool(
            host=host, port=port, db=db, password=password, decode_responses=True
        )
        redis_client = redis.Redis(connection_pool=pool)
        logger.info("Connected to Redis at %s:%s", host, port)
        return redis_client
    except Exception as e:
        logger.error("Error connecting to Redis: %s", e)
        raise


def sanitize_dynamodb_value(value, depth=0, max_depth=128):
    """
    Sanitize a single DynamoDB value into a JSON-compatible type.
    Handles Decimal, Binary, Sets, Lists, Maps, and nested structures.
    Applies a max depth to avoid infinite recursion.
    """
    if depth > max_depth:
        # Beyond max depth, serialize the remaining structure to a string
        return json.dumps(value, default=str)

    if isinstance(value, Decimal):
        # Convert Decimal to int or float
        return int(value) if value % 1 == 0 else float(value)
    elif isinstance(value, Binary):
        # Decode Binary to UTF-8 string
        return value.value.decode("utf-8", errors="replace")
    elif isinstance(value, set):
        # Recursively sanitize Set items
        return [sanitize_dynamodb_value(v, depth + 1) for v in value]
    elif isinstance(value, list):
        # Recursively sanitize List items
        return [sanitize_dynamodb_value(v, depth + 1) for v in value]
    elif isinstance(value, dict):
        # Recursively sanitize dictionary (Map) items
        return {k: sanitize_dynamodb_value(v, depth + 1) for k, v in value.items()}
    else:
        # Fallback: Return the value as-is for basic types
        return value



def dynamodb_to_json(item):
    """
    Convert a DynamoDB item returned by boto3 into a JSON-compatible dictionary.
    """
    return {key: sanitize_dynamodb_value(value) for key, value in item.items()}


def migrate_table_to_redis(table, redis_client, batch_size=100, dry_run=False):
    """
    Migrate data from DynamoDB table to Redis as JSON objects.
    """
    try:
        logger.info("Starting migration from DynamoDB to Redis...")
        total_migrated = 0
        retries = 0
        response = table.scan(Limit=batch_size)

        while True:
            # Extract items from the current response
            items = response.get("Items", [])

            if not items:
                logger.info("No items found in the current page.")

            for item in items:
                try:
                    # Extract primary key and sort key
                    partition_key = item.get(table.key_schema[0]["AttributeName"])
                    sort_key = (
                        item.get(table.key_schema[1]["AttributeName"])
                        if len(table.key_schema) > 1
                        else None
                    )

                    if not partition_key:
                        logger.warning("Skipping item without partition key: %s", item)
                        continue

                    # Construct Redis key
                    redis_key = f"{table.table_name}:{partition_key}"
                    if sort_key:
                        redis_key += f":{sort_key}"  # Append sort key if present

                    # Convert item to JSON
                    json_item = dynamodb_to_json(item)

                    if dry_run:
                        logger.info("[DRY-RUN] Would write to Redis key: %s", redis_key)
                        logger.info("[DRY-RUN] JSON Data: %s", json.dumps(json_item))
                    else:
                        redis_client.json().set(redis_key, "$", json_item)
                        logger.info("Stored JSON in Redis key: %s", redis_key)

                    total_migrated += 1
                except Exception as e:
                    logger.error("Error processing item: %s", e)

            logger.info("Processed %d items so far...", total_migrated)

            # Handle pagination
            if "LastEvaluatedKey" not in response:
                logger.info("All items processed. No more pages to fetch.")
                break

            last_evaluated_key = response["LastEvaluatedKey"]
            logger.info("Pagination detected. Fetching next page with LastEvaluatedKey: %s", last_evaluated_key)

            while retries < 5:
                try:
                    response = table.scan(Limit=batch_size, ExclusiveStartKey=last_evaluated_key)
                    retries = 0
                    break
                except Exception as e:
                    retries += 1
                    wait_time = 2 ** retries
                    logger.warning("Retrying in %d seconds due to: %s", wait_time, str(e))
                    time.sleep(wait_time)

        logger.info("Migration completed: %d items migrated to Redis.", total_migrated)
        return total_migrated

    except Exception as e:
        logger.error("Error during migration: %s", e)
        raise


def validate_migration(processed_count, redis_client, table_name):
    """
    Validate that the number of items processed matches the number of keys in Redis.
    """
    try:
        redis_key_pattern = f"{table_name}:*"
        redis_count = len(redis_client.keys(redis_key_pattern))

        if processed_count == redis_count:
            logger.info("Validation successful: All items migrated (Processed=%d, Redis=%d).", processed_count, redis_count)
        else:
            logger.warning("Validation failed: Processed count=%d, Redis count=%d.", processed_count, redis_count)
    except Exception as e:
        logger.error("Error during validation: %s", e)


def parse_arguments():
    """Parse CLI arguments, falling back to environment variables."""
    parser = argparse.ArgumentParser(description="Migrate DynamoDB table to Redis as JSON.")
    parser.add_argument("--dynamo-table", default=os.getenv("DYNAMO_TABLE_NAME"), help="DynamoDB table name or ARN.")
    parser.add_argument("--redis-host", default=os.getenv("REDIS_HOST", "localhost"), help="Redis host.")
    parser.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", 6379)), help="Redis port.")
    parser.add_argument("--redis-db", type=int, default=int(os.getenv("REDIS_DB", 0)), help="Redis database number.")
    parser.add_argument("--redis-password", default=os.getenv("REDIS_PASSWORD"), help="Redis password (optional).")
    parser.add_argument("--region", default=os.getenv("AWS_REGION"), help="AWS region for DynamoDB (optional).")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("BATCH_SIZE", 100)), help="Batch size for processing.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without writing to Redis.")
    return parser.parse_args()


def main():
    """Main entry point for the utility."""
    args = parse_arguments()

    table = connect_dynamodb(args.dynamo_table, args.region)
    redis_client = connect_redis(
        host=args.redis_host,
        port=args.redis_port,
        db=args.redis_db,
        password=args.redis_password,
    )

    processed_count = migrate_table_to_redis(table, redis_client, batch_size=args.batch_size, dry_run=args.dry_run)

    if not args.dry_run:
        validate_migration(processed_count, redis_client, args.dynamo_table)


if __name__ == "__main__":
    main()