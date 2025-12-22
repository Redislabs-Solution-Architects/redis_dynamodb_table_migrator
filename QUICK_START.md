# Quick Start Guide - v1.0

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker installed (or Python 3.12+)
- AWS credentials with DynamoDB read access
- Redis instance (local or Redis Cloud)

### Option 1: Docker (Recommended)

#### For Redis Cloud or Authenticated Redis:
```bash
docker run --rm \
  -e DYNAMO_TABLE_NAME=your-table-name \
  -e REDIS_URI="redis://default:your-password@your-host:port" \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID="your-key" \
  -e AWS_SECRET_ACCESS_KEY="your-secret" \
  gacerioni/redis_dynamodb_table_migrator:1.0.0
```

#### For Local Redis:
```bash
docker run --rm \
  -e DYNAMO_TABLE_NAME=your-table-name \
  -e REDIS_URI="redis://host.docker.internal:6379" \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID="your-key" \
  -e AWS_SECRET_ACCESS_KEY="your-secret" \
  gacerioni/redis_dynamodb_table_migrator:1.0.0
```

### Option 2: Python (Local Development)

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Configure Environment
Create a `.env` file:
```bash
DYNAMO_TABLE_NAME=your-table-name
REDIS_URI=redis://localhost:6379
AWS_REGION=us-east-1
```

#### 3. Run Migration
```bash
python main.py
```

## 🧪 Test First (Dry Run)

Always test with `--dry-run` first:

```bash
# Docker
docker run --rm \
  -e DYNAMO_TABLE_NAME=your-table-name \
  -e REDIS_URI="redis://localhost:6379" \
  -e AWS_REGION=us-east-1 \
  gacerioni/redis_dynamodb_table_migrator:1.0.0 \
  --dry-run

# Python
python main.py --dry-run
```

## 📊 Common Scenarios

### Scenario 1: Redis Cloud Migration
```bash
# Get your Redis Cloud connection string from the Redis Cloud console
# Format: redis://default:password@endpoint:port

docker run --rm \
  -e DYNAMO_TABLE_NAME=production-events \
  -e REDIS_URI="redis://default:abc123@redis-12345.c1.us-east-1.ec2.cloud.redislabs.com:12345" \
  -e AWS_REGION=us-east-1 \
  gacerioni/redis_dynamodb_table_migrator:1.0.0
```

### Scenario 2: Large Table with Custom Batch Size
```bash
docker run --rm \
  -e DYNAMO_TABLE_NAME=large-table \
  -e REDIS_URI="redis://localhost:6379" \
  -e BATCH_SIZE=500 \
  gacerioni/redis_dynamodb_table_migrator:1.0.0
```

### Scenario 3: Skip JSON Parsing
```bash
# If you want to preserve stringified JSON as-is
docker run --rm \
  -e DYNAMO_TABLE_NAME=your-table \
  -e REDIS_URI="redis://localhost:6379" \
  gacerioni/redis_dynamodb_table_migrator:1.0.0 \
  --no-parse-json
```

## 🔍 Verify Migration

After migration, check your Redis instance:

```bash
# Connect to Redis
redis-cli

# Count migrated keys
KEYS your-table-name:*

# View a sample record
JSON.GET your-table-name:your-partition-key

# Check data structure
JSON.TYPE your-table-name:your-partition-key $
```

## 📈 Expected Results

### DynamoDB Item:
```json
{
  "id": "user-123",
  "name": "John Doe",
  "age": 30,
  "balance": 1234.56,
  "tags": ["premium", "verified"],
  "metadata": {
    "created": "2024-01-15T10:30:00Z",
    "active": true
  }
}
```

### Redis JSON (after migration):
```json
{
  "id": "user-123",
  "name": "John Doe",
  "age": 30,
  "balance": 1234.56,
  "tags": ["premium", "verified"],
  "metadata": {
    "created": 1705314600,
    "active": true
  }
}
```

**Redis Key**: `your-table-name:user-123`

## 🆘 Troubleshooting

### Connection Issues
- **Redis Cloud**: Ensure you're using the full connection string with password
- **Local Redis**: Use `host.docker.internal` instead of `localhost` in Docker
- **Firewall**: Check that Redis port is accessible

### AWS Credentials
- Ensure credentials have `dynamodb:Scan` and `dynamodb:DescribeTable` permissions
- For EC2/ECS, use IAM roles instead of access keys

### Performance
- Adjust `BATCH_SIZE` (default: 100) based on item size
- Monitor DynamoDB read capacity units
- Use provisioned capacity or on-demand billing

## 📚 Next Steps

1. ✅ Run test migration with `--dry-run`
2. ✅ Verify a few sample records
3. ✅ Run full migration
4. ✅ Validate record count
5. ✅ Test your application with Redis data

For more details, see [README.md](README.md) and [CHANGELOG.md](CHANGELOG.md).

