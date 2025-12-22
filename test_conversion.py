#!/usr/bin/env python3
"""
Test script to verify DynamoDB to Redis JSON conversion logic.
"""

import json
from decimal import Decimal
from boto3.dynamodb.types import Binary
from main import sanitize_dynamodb_value

def test_conversion():
    """Test various DynamoDB data types conversion."""
    
    print("Testing DynamoDB to Redis JSON conversion...\n")
    
    # Test cases
    test_cases = [
        # Decimal conversion
        ("Decimal (whole number)", Decimal("42"), 42),
        ("Decimal (float)", Decimal("3.14"), 3.14),
        
        # Binary conversion
        ("Binary (UTF-8)", Binary(b"Hello World"), "Hello World"),
        
        # Set conversion (becomes sorted list)
        ("String Set", {"apple", "banana", "cherry"}, ["apple", "banana", "cherry"]),
        ("Number Set", {1, 2, 3}, [1, 2, 3]),
        ("Binary Set", {Binary(b"Binary1"), Binary(b"Binary2"), Binary(b"Binary3")},
         ["Binary1", "Binary2", "Binary3"]),
        
        # List conversion
        ("List", [1, "two", Decimal("3.0")], [1, "two", 3]),
        
        # Dict/Map conversion
        ("Map", {"key1": "value1", "key2": Decimal("100")}, {"key1": "value1", "key2": 100}),
        
        # Nested structure
        ("Nested Map", {
            "user": {
                "name": "John",
                "age": Decimal("30"),
                "scores": [Decimal("95.5"), Decimal("87"), Decimal("92.3")]
            }
        }, {
            "user": {
                "name": "John",
                "age": 30,
                "scores": [95.5, 87, 92.3]
            }
        }),
        
        # String types
        ("String", "Hello", "Hello"),
        ("Boolean", True, True),
        ("None", None, None),
        
        # Datetime string (converts to Unix timestamp)
        ("ISO Datetime", "2024-01-15T10:30:00Z", 1705314600),
        
        # Stringified JSON
        ("Stringified JSON", '{"nested": "value"}', {"nested": "value"}),
    ]
    
    passed = 0
    failed = 0
    
    for name, input_val, expected in test_cases:
        try:
            result = sanitize_dynamodb_value(input_val)

            # For sets, sort both for comparison
            if isinstance(result, list) and isinstance(expected, list):
                result_sorted = sorted(result, key=str)
                expected_sorted = sorted(expected, key=str)
                success = result_sorted == expected_sorted
            else:
                success = result == expected

            # Format input for display
            input_display = repr(input_val) if isinstance(input_val, Binary) else str(input_val)

            if success:
                print(f"✅ {name}: PASSED")
                print(f"   Input:    {input_display}")
                print(f"   Output:   {result}")
                passed += 1
            else:
                print(f"❌ {name}: FAILED")
                print(f"   Input:    {input_display}")
                print(f"   Expected: {expected}")
                print(f"   Got:      {result}")
                failed += 1
        except Exception as e:
            input_display = repr(input_val) if isinstance(input_val, Binary) else str(input_val)
            print(f"❌ {name}: ERROR - {e}")
            print(f"   Input:    {input_display}")
            failed += 1

        print()
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    return failed == 0

if __name__ == "__main__":
    success = test_conversion()
    exit(0 if success else 1)

