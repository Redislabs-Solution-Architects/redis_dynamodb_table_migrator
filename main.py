import os
import boto3
import redis
import argparse
import logging
import time
import json
import re
import base64
from datetime import datetime, timezone
from boto3.dynamodb.types import Binary
from decimal import Decimal
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def is_stringified_json(value: str) -> bool:
    return value.strip().startswith(('{', '['))

def try_parse_datetime(value: str) -> int | str:
    iso_pattern = r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z)?$"
    if not re.match(iso_pattern, value.strip()):
        return value

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return int(dt.replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return value

def sanitize_dynamodb_value(value, depth=0, max_depth=128, parse_json=True):
    """
    Recursively convert DynamoDB values to Redis JSON-compatible types.

    Handles all DynamoDB data types:
    - Decimal -> int or float
    - Binary -> string (UTF-8 decoded)
    - Set -> list (DynamoDB sets become JSON arrays)
    - List -> list (recursive)
    - Map/Dict -> dict (recursive)
    - String -> string (with datetime parsing and JSON unwrapping)
    - Number -> int or float
    - Boolean -> bool
    - Null -> None

    Args:
        value: The DynamoDB value to sanitize
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops
        parse_json: Whether to parse stringified JSON values

    Returns:
        JSON-compatible Python value
    """
    # Prevent infinite recursion
    if depth > max_depth:
        logger.warning("Max recursion depth reached at depth %d, converting to JSON string", depth)
        return json.dumps(value, default=str)

    # Handle DynamoDB Decimal type (numbers)
    if isinstance(value, Decimal):
        # Convert to int if it's a whole number, otherwise float
        return int(value) if value % 1 == 0 else float(value)

    # Handle DynamoDB Binary type
    elif isinstance(value, Binary):
        try:
            # Try to decode as UTF-8, fallback to base64 representation
            return value.value.decode("utf-8")
        except UnicodeDecodeError:
            # If binary data is not valid UTF-8, return base64 encoded string
            return base64.b64encode(value.value).decode("utf-8")

    # Handle DynamoDB Sets (SS, NS, BS) and Lists (L)
    elif isinstance(value, (set, list)):
        # Convert sets to lists for JSON compatibility
        if isinstance(value, list):
            iterable = value
        else:
            # For sets, convert to list first, then sort if possible
            list_value = list(value)
            try:
                # Try to sort - works for strings and numbers
                iterable = sorted(list_value)
            except TypeError:
                # If sorting fails (e.g., Binary objects), convert first then sort by string representation
                # This handles Binary Sets (BS) which can't be compared directly
                converted = [sanitize_dynamodb_value(v, depth + 1, max_depth, parse_json) for v in list_value]
                try:
                    iterable = sorted(converted, key=str)
                except TypeError:
                    # If still can't sort, just use the list as-is
                    iterable = converted
                return iterable

        return [sanitize_dynamodb_value(v, depth + 1, max_depth, parse_json) for v in iterable]

    # Handle DynamoDB Maps (M) and Python dicts
    elif isinstance(value, dict):
        return {k: sanitize_dynamodb_value(v, depth + 1, max_depth, parse_json) for k, v in value.items()}

    # Handle strings with special processing
    elif isinstance(value, str):
        original = value.strip()

        # Try to parse as datetime (ISO format) and convert to Unix timestamp
        for candidate in (original, original.encode("utf-8").decode("unicode_escape")):
            dt = try_parse_datetime(candidate)
            if isinstance(dt, int):
                return dt

        # If parse_json is enabled and string looks like JSON, try to deserialize
        if parse_json and is_stringified_json(original):
            try:
                parsed = json.loads(original)
            except Exception as e:
                logger.debug("Failed to parse JSON string: %s", e)
                parsed = original

            # Recursively unwrap nested stringified JSON
            while isinstance(parsed, str):
                candidate = parsed.strip().strip('"')

                # Check if nested string is a datetime
                for cand in (candidate, candidate.encode("utf-8").decode("unicode_escape")):
                    dt_nested = try_parse_datetime(cand)
                    if isinstance(dt_nested, int):
                        return dt_nested

                # Try to parse nested JSON
                if is_stringified_json(candidate):
                    try:
                        parsed = json.loads(candidate)
                    except Exception:
                        break
                else:
                    return candidate

            # Recursively sanitize the parsed value
            return sanitize_dynamodb_value(parsed, depth + 1, max_depth, parse_json)

        return original

    # Handle booleans explicitly
    elif isinstance(value, bool):
        return value

    # Handle None/null
    elif value is None:
        return None

    # Handle numeric types (int, float)
    elif isinstance(value, (int, float)):
        return value

    # Fallback for any other type
    else:
        logger.warning("Unexpected type %s for value %s, converting to string", type(value), value)
        return str(value)

def get_aws_session():
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

def connect_redis(redis_uri=None, host=None, port=None, db=0, password=None):
    """
    Connect to Redis using either a URI or individual connection parameters.

    Args:
        redis_uri: Redis connection URI (e.g., redis://user:password@host:port/db)
        host: Redis host (used if redis_uri is not provided)
        port: Redis port (used if redis_uri is not provided)
        db: Redis database number
        password: Redis password (used if redis_uri is not provided)

    Returns:
        Redis client instance
    """
    try:
        if redis_uri:
            # Use URI-based connection for Redis Cloud and authenticated instances
            redis_client = redis.from_url(redis_uri, decode_responses=True)
            logger.info("Connected to Redis using URI: %s", redis_uri.split('@')[-1] if '@' in redis_uri else redis_uri)
        else:
            # Fallback to host/port connection for backward compatibility
            pool = redis.ConnectionPool(
                host=host, port=port, db=db, password=password, decode_responses=True
            )
            redis_client = redis.Redis(connection_pool=pool)
            logger.info("Connected to Redis at %s:%s", host, port)

        # Test the connection
        redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error("Error connecting to Redis: %s", e)
        raise

def dynamodb_to_json(item, parse_json=True):
    return {key: sanitize_dynamodb_value(value, parse_json=parse_json) for key, value in item.items()}

def migrate_table_to_redis(table, redis_client, batch_size=100, dry_run=False, parse_json=True):
    try:
        logger.info("Starting migration from DynamoDB to Redis...")
        total_migrated = 0
        retries = 0
        response = table.scan(Limit=batch_size)

        while True:
            items = response.get("Items", [])

            if not items:
                logger.info("No items found in the current page.")

            for item in items:
                try:
                    partition_key = item.get(table.key_schema[0]["AttributeName"])
                    sort_key = (
                        item.get(table.key_schema[1]["AttributeName"])
                        if len(table.key_schema) > 1
                        else None
                    )

                    if not partition_key:
                        logger.warning("Skipping item without partition key: %s", item)
                        continue

                    redis_key = f"{table.table_name}:{partition_key}"
                    if sort_key:
                        redis_key += f":{sort_key}"

                    json_item = dynamodb_to_json(item, parse_json=parse_json)

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
    parser = argparse.ArgumentParser(description="Migrate DynamoDB table to Redis as JSON.")
    parser.add_argument("--dynamo-table", default=os.getenv("DYNAMO_TABLE_NAME"), help="DynamoDB table name or ARN.")

    # Redis connection options - URI takes precedence
    parser.add_argument("--redis-uri", default=os.getenv("REDIS_URI"),
                        help="Redis connection URI (e.g., redis://user:password@host:port/db). Takes precedence over individual parameters.")
    parser.add_argument("--redis-host", default=os.getenv("REDIS_HOST", "localhost"),
                        help="Redis host (used if --redis-uri is not provided).")
    parser.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", 6379)),
                        help="Redis port (used if --redis-uri is not provided).")
    parser.add_argument("--redis-db", type=int, default=int(os.getenv("REDIS_DB", 0)),
                        help="Redis database number (used if --redis-uri is not provided).")
    parser.add_argument("--redis-password", default=os.getenv("REDIS_PASSWORD"),
                        help="Redis password (used if --redis-uri is not provided).")

    parser.add_argument("--region", default=os.getenv("AWS_REGION"), help="AWS region for DynamoDB (optional).")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("BATCH_SIZE", 100)), help="Batch size for processing.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without writing to Redis.")
    parser.add_argument("--no-parse-json", action="store_true", help="Disable parsing of stringified JSON fields.")
    return parser.parse_args()

def main():
    args = parse_arguments()

    # Connect to DynamoDB
    table = connect_dynamodb(args.dynamo_table, args.region)

    # Connect to Redis - URI takes precedence over individual parameters
    if args.redis_uri:
        logger.info("Using Redis URI for connection")
        redis_client = connect_redis(redis_uri=args.redis_uri)
    else:
        logger.info("Using Redis host/port for connection")
        redis_client = connect_redis(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_db,
            password=args.redis_password,
        )

    # Perform migration
    processed_count = migrate_table_to_redis(
        table,
        redis_client,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        parse_json=not args.no_parse_json
    )

    # Validate migration if not a dry run
    if not args.dry_run:
        validate_migration(processed_count, redis_client, args.dynamo_table)

if __name__ == "__main__":
    main()