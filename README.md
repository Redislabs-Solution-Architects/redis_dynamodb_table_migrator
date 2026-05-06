# Redis DynamoDB Table Migrator

A production-ready utility to migrate data from a DynamoDB table to Redis in JSON format. This tool supports complex DynamoDB items, including nested maps, lists, and sets, with reliable type conversion and Redis Cloud compatibility.

## ✅ Status: v1.2 Ready

This migrator is production-ready with:
- ✅ Reliable DynamoDB to Redis JSON conversion
- ✅ Comprehensive data type handling (Decimal, Binary, Sets, Lists, Maps, etc.)
- ✅ Redis Cloud support with URI-based authentication
- ✅ Recursive type conversion with depth protection
- ✅ Datetime parsing and JSON unwrapping (all ISO 8601 variants, including milliseconds)
- ✅ Pagination support for large tables with safe retry exhaustion handling
- ✅ Pipelined Redis writes for high-throughput migrations
- ✅ Consistent reads from DynamoDB (`ConsistentRead=True`) for accurate snapshots
- ✅ Safe validation via `SCAN` (no blocking `KEYS *`)

## Features
- **Complete DynamoDB Type Support**: Handles all DynamoDB data types including Decimal, Binary, Sets (SS, NS, BS), Lists, Maps, and nested structures
- **Intelligent Type Conversion**: Automatically converts DynamoDB types to Redis JSON-compatible formats
- **Redis Cloud Compatible**: Supports Redis URI for authenticated connections (Redis Cloud, Redis Enterprise, etc.)
- **Recursive Processing**: Safely handles deeply nested structures with configurable depth limits
- **Datetime Parsing**: Detects and converts all ISO 8601 variants to Unix timestamps (with/without milliseconds, `T`/space separator, `Z` suffix)
- **JSON Unwrapping**: Intelligently parses stringified JSON fields
- **Pipelined Writes**: Batches Redis writes per DynamoDB page for significantly higher throughput
- **Consistent Reads**: Uses `ConsistentRead=True` on DynamoDB scans for accurate point-in-time snapshots
- **Pagination Support**: Efficiently processes large DynamoDB tables with automatic pagination and safe retry exhaustion (no infinite loops)
- **Safe Validation**: Post-migration key count uses `SCAN` instead of the blocking `KEYS` command
- **Dry Run Mode**: Test migrations without writing to Redis
- **Flexible Configuration**: Use environment variables or CLI arguments

---

## Quickstart

### 1. Pull the Docker Image

The latest image is published on Docker Hub for `linux/amd64` and `linux/arm64` (Apple Silicon / AWS Graviton):

```bash
docker pull gacerioni/redis_dynamodb_table_migrator:1.2.0
```

> **Want to build from source instead?**
> ```bash
> docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile \
>   -t gacerioni/redis_dynamodb_table_migrator:1.2.0 --push .
> ```

### 2. Run the Migrator

#### Option A: Using Redis URI (Recommended for Redis Cloud)

Use Redis URI for authenticated connections to Redis Cloud, Redis Enterprise, or any Redis instance with authentication:

**With explicit AWS credentials:**
```bash
docker run --rm \
  -e DYNAMO_TABLE_NAME=gabs-migrator-table \
  -e REDIS_URI="redis://default:your-password@your-redis-host:6379" \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY" \
  gacerioni/redis_dynamodb_table_migrator:1.2.0
```

**Using local AWS credentials (recommended):**
```bash
# AWS credentials automatically loaded from ~/.aws/credentials
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -e DYNAMO_TABLE_NAME=gabs-migrator-table \
  -e REDIS_URI="redis://default:your-password@your-redis-host:6379" \
  gacerioni/redis_dynamodb_table_migrator:1.2.0
```

**Redis URI Format Examples:**
- Local Redis: `redis://localhost:6379`
- Redis with password: `redis://default:password@host:6379`
- Redis Cloud: `redis://default:your-password@redis-12345.c123.us-east-1-1.ec2.cloud.redislabs.com:12345`
- Redis with SSL: `rediss://default:password@host:6380`
- Redis with database selection: `redis://localhost:6379/1`

#### Option B: Using Host/Port (Legacy)

For backward compatibility, you can still use individual host/port parameters:

**With local AWS credentials (recommended):**
```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -e DYNAMO_TABLE_NAME=gabs-migrator-table \
  -e REDIS_HOST=host.docker.internal \
  -e REDIS_PORT=6379 \
  gacerioni/redis_dynamodb_table_migrator:1.2.0
```

**With explicit AWS credentials:**
```bash
docker run --rm \
  -e DYNAMO_TABLE_NAME=gabs-migrator-table \
  -e REDIS_HOST=host.docker.internal \
  -e REDIS_PORT=6379 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY" \
  gacerioni/redis_dynamodb_table_migrator:1.2.0
```

### 3. CLI Options

You can also use CLI arguments if you prefer not to use environment variables:

**Using Redis URI:**
```bash
docker run --rm gacerioni/redis_dynamodb_table_migrator:1.2.0 \
  --dynamo-table gabs-migrator-table \
  --redis-uri "redis://default:password@host:6379" \
  --region us-east-1
```

**Using Host/Port:**
```bash
docker run --rm gacerioni/redis_dynamodb_table_migrator:1.2.0 \
  --dynamo-table gabs-migrator-table \
  --redis-host host.docker.internal \
  --redis-port 6379 \
  --region us-east-1
```

**Dry Run Mode:**
```bash
docker run --rm gacerioni/redis_dynamodb_table_migrator:1.2.0 \
  --dynamo-table gabs-migrator-table \
  --redis-uri "redis://localhost:6379" \
  --dry-run
```

## Environment Variables

| Variable              | Description                          | Default      | Priority | Required |
|------------------------|--------------------------------------|--------------|----------|----------|
| `DYNAMO_TABLE_NAME`    | Name of the DynamoDB table.          | `None`       | - | **Yes** |
| `REDIS_URI`            | Redis connection URI (recommended).  | `None`       | **High** (takes precedence) | No |
| `REDIS_HOST`           | Redis host address.                  | `localhost`  | Low (used if REDIS_URI not set) | No |
| `REDIS_PORT`           | Redis port number.                   | `6379`       | Low (used if REDIS_URI not set) | No |
| `REDIS_DB`             | Redis database number.               | `0`          | Low (used if REDIS_URI not set) | No |
| `REDIS_PASSWORD`       | Redis password.                      | `None`       | Low (used if REDIS_URI not set) | No |
| `AWS_REGION`           | AWS region of the DynamoDB table.    | `None` (auto-detected) | - | No |
| `AWS_ACCESS_KEY_ID`    | AWS access key ID.                   | `None` (uses `~/.aws/credentials`) | - | No |
| `AWS_SECRET_ACCESS_KEY`| AWS secret access key.               | `None` (uses `~/.aws/credentials`) | - | No |
| `BATCH_SIZE`           | Number of items to process per batch.| `100`        | - | No |

## CLI Arguments

All environment variables can be overridden with CLI arguments:

| Argument              | Description                                      |
|------------------------|--------------------------------------------------|
| `--dynamo-table`       | DynamoDB table name or ARN                       |
| `--redis-uri`          | Redis connection URI (takes precedence)          |
| `--redis-host`         | Redis host (used if --redis-uri not provided)    |
| `--redis-port`         | Redis port (used if --redis-uri not provided)    |
| `--redis-db`           | Redis database number                            |
| `--redis-password`     | Redis password                                   |
| `--region`             | AWS region for DynamoDB                          |
| `--batch-size`         | Batch size for processing                        |
| `--dry-run`            | Simulate migration without writing to Redis      |
| `--no-parse-json`      | Disable parsing of stringified JSON fields       |

## Data Type Conversion

The migrator handles all DynamoDB data types and converts them to Redis JSON-compatible formats:

| DynamoDB Type | Redis JSON Type | Notes |
|---------------|-----------------|-------|
| String (S)    | string          | Datetime strings converted to Unix timestamps |
| Number (N)    | number          | Decimals converted to int or float |
| Binary (B)    | string          | UTF-8 decoded, or base64 if not valid UTF-8 |
| Boolean (BOOL)| boolean         | Direct conversion |
| Null (NULL)   | null            | Direct conversion |
| Map (M)       | object          | Recursively converted |
| List (L)      | array           | Recursively converted |
| String Set (SS)| array          | Converted to sorted array |
| Number Set (NS)| array          | Converted to sorted array of numbers |
| Binary Set (BS)| array          | Converted to array of strings |

### Notes

#### AWS Credentials (Automatic Fallback)
The migrator uses the standard AWS credential chain in this order:
1. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
2. **AWS credentials file**: `~/.aws/credentials` (recommended for local development)
3. **AWS config file**: `~/.aws/config`
4. **IAM roles**: Automatically used when running on EC2, ECS, or Lambda

**Recommendation**: Use `~/.aws/credentials` for local development and IAM roles for production deployments. Only use environment variables when necessary.

#### Redis Connection
- **Redis URI takes precedence**: If `REDIS_URI` is set, individual host/port/password parameters are ignored
- **Redis Cloud**: Use the connection string provided by Redis Cloud (format: `redis://default:password@host:port`)
- **Docker Desktop**: For local Redis, use `host.docker.internal` as the host or `redis://host.docker.internal:6379`

#### Other
- **DynamoDB Permissions**: Ensure your AWS credentials have `dynamodb:Scan` and `dynamodb:DescribeTable` permissions
- **Depth Protection**: Nested structures are processed up to 128 levels deep to prevent infinite recursion

### Example Data

If you’d like to test with example data, you can use the provided script to populate your DynamoDB table:

```bash
python utils/add_items_to_dynamodb_table.py
```

This script generates a diverse dataset (250 standard items + 10 edge-case items) to stress-test the migrator across all DynamoDB type combinations, including: ISO datetimes, stringified JSON, floats, empty collections, Unicode/emoji, NULL, non-UTF-8 binary, deeply nested maps, mixed-type lists, and large sets.


## License

This project is licensed under the MIT License.
