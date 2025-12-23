# Changelog

## [1.0.0] - 2024-12-22

### 🎉 v1.0 Release - Production Ready

This release marks the first production-ready version of the Redis DynamoDB Table Migrator with comprehensive improvements to reliability, type conversion, and Redis Cloud compatibility.

**Tested with real DynamoDB data**: Successfully migrated 259 items with complex nested structures, Binary Sets, and all DynamoDB data types without errors.

### ✨ Added

#### Redis Cloud Support
- **Redis URI Connection**: Added support for Redis URI format (`redis://user:password@host:port/db`)
- **Authentication Support**: Full support for authenticated Redis instances (Redis Cloud, Redis Enterprise)
- **SSL/TLS Support**: Compatible with `rediss://` URIs for secure connections
- **Connection Testing**: Automatic ping test after connection to verify connectivity

#### Enhanced Type Conversion
- **Comprehensive DynamoDB Type Support**: All DynamoDB types now properly handled:
  - Decimal (N) → int or float (automatic conversion based on value)
  - Binary (B) → string (UTF-8 decoded, or base64 for non-UTF-8 data)
  - String Set (SS) → sorted array
  - Number Set (NS) → sorted array of numbers
  - Binary Set (BS) → array of strings
  - List (L) → array (recursive conversion)
  - Map (M) → object (recursive conversion)
  - Boolean (BOOL) → boolean
  - Null (NULL) → null
  - String (S) → string (with datetime parsing and JSON unwrapping)

- **Intelligent String Processing**:
  - Automatic ISO datetime detection and conversion to Unix timestamps
  - Recursive JSON unwrapping for stringified JSON fields
  - Unicode escape sequence handling
  - Nested string parsing with depth protection

- **Safety Features**:
  - Maximum recursion depth protection (128 levels)
  - Graceful error handling for malformed data
  - Smart Binary Set sorting (converts to strings before sorting to avoid comparison errors)
  - Detailed logging for debugging

### 🔧 Changed

#### Configuration
- **Environment Variables**: 
  - Added `REDIS_URI` (takes precedence over host/port)
  - Maintained backward compatibility with `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
  
- **CLI Arguments**:
  - Added `--redis-uri` parameter
  - Maintained all existing parameters for backward compatibility
  - URI takes precedence when both URI and host/port are provided

#### Code Quality
- **Enhanced Documentation**: 
  - Comprehensive docstrings for all functions
  - Detailed type conversion documentation
  - Clear parameter descriptions
  
- **Improved Logging**:
  - Better connection status messages
  - Warning logs for unexpected data types
  - Debug logs for JSON parsing attempts

### 📚 Documentation

- **Updated README.md**:
  - Production-ready status badge
  - Comprehensive feature list
  - Redis URI examples for various scenarios
  - Data type conversion table
  - Environment variable priority documentation
  - CLI argument reference

- **Added Test Suite**:
  - Comprehensive conversion tests (`test_conversion.py`)
  - Tests for all DynamoDB data types
  - Validation of nested structures
  - Datetime parsing verification

### 🔄 Migration Guide

#### From v0.x to v1.0

**Recommended (Redis URI)**:
```bash
# Old way
-e REDIS_HOST=localhost
-e REDIS_PORT=6379
-e REDIS_PASSWORD=mypassword

# New way (recommended)
-e REDIS_URI=redis://default:mypassword@localhost:6379
```

**Backward Compatible**:
The old host/port method still works! No breaking changes.

### 🧪 Testing

All conversion tests passing:
- ✅ Decimal conversion (whole numbers and floats)
- ✅ Binary data handling (UTF-8 and base64)
- ✅ Set to array conversion (sorted)
- ✅ List processing (recursive)
- ✅ Map/Dict conversion (recursive)
- ✅ Nested structure handling
- ✅ String type preservation
- ✅ Boolean and null handling
- ✅ ISO datetime parsing
- ✅ Stringified JSON unwrapping

### 📦 Dependencies

No changes to dependencies. Still using:
- boto3==1.35.64
- redis==5.2.0
- Python 3.12+

### 🙏 Notes

This v1.0 release is production-ready and has been tested with:
- Complex nested DynamoDB structures
- All DynamoDB data types
- Redis Cloud connections
- Large table pagination
- Various datetime formats
- Stringified JSON fields

For issues or feature requests, please open an issue on GitHub.

