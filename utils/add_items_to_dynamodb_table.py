import boto3
from itertools import product

# DynamoDB table name
table_name = "gabs-migrator-table"

# Base attributes for items
base_sort_keys = [f"sort-{chr(65 + i)}" for i in range(10)]  # A, B, C, ..., J
base_partition_keys = [f"item-{i}" for i in range(25)]  # item-0 to item-24

# Sample data for generating items
sample_data = {
    "simple_string": ["String A", "String B", "String C"],
    "simple_number": [10, 20, 30],
    "simple_bool": [True, False],
    "nested_map": {
        "inner_key1": ["Inner Value 1", "Inner Value 2"],
        "inner_key2": [100, 200],
        "inner_key3": [True, False],
    },
    "number_set": [[1, 2, 3], [4, 5, 6]],
    "string_set": [["SetValue1", "SetValue2"], ["SetValue3"]],
    "complex_list": [
        [{"S": "ListItem1"}, {"M": {"key": {"N": "123"}, "value": {"BOOL": True}}}],
        [{"S": "ListItem2"}, {"M": {"key": {"N": "456"}, "value": {"BOOL": False}}}],
    ],
    "binary_data": [
        "U29tZSBiaW5hcnkgZGF0YQ==",  # Base64 for "Some binary data"
        "RGF0YQ=="  # Base64 for "Data"
    ],
    "nested_list": [
        [{"S": "List Item 1"}, {"N": "123"}, {"M": {"key1": {"BOOL": True}, "key2": {"S": "Nested String"}}}],
        [{"S": "List Item 2"}, {"N": "456"}, {"M": {"key1": {"BOOL": False}, "key2": {"S": "Another Nested String"}}}],
    ],
    "binary_set": [
        ["QmluYXJ5MQ==", "QmluYXJ5Mg=="],  # Base64 for "Binary1" and "Binary2"
        ["QmluYXJ5Mw=="]  # Base64 for "Binary3"
    ],
}

# Generate deterministic and diverse items
def generate_items(partition_keys, sort_keys):
    items = []
    counter = 1
    for pk, sk in product(partition_keys, sort_keys):
        item = {
            "table_pk": {"S": pk},
            "sort_key": {"S": sk},
            "simple_string": {"S": sample_data["simple_string"][counter % len(sample_data["simple_string"])]},
            "simple_number": {"N": str(sample_data["simple_number"][counter % len(sample_data["simple_number"])] * counter)},
            "simple_bool": {"BOOL": sample_data["simple_bool"][counter % len(sample_data["simple_bool"])]},
            "nested_map": {
                "M": {
                    "inner_key1": {"S": sample_data["nested_map"]["inner_key1"][counter % len(sample_data["nested_map"]["inner_key1"])]},
                    "inner_key2": {"N": str(sample_data["nested_map"]["inner_key2"][counter % len(sample_data["nested_map"]["inner_key2"])] * counter)},
                    "inner_key3": {"BOOL": sample_data["nested_map"]["inner_key3"][counter % len(sample_data["nested_map"]["inner_key3"])]}
                }
            },
            "number_set": {"NS": [str(num) for num in sample_data["number_set"][counter % len(sample_data["number_set"])] ]},
            "string_set": {"SS": sample_data["string_set"][counter % len(sample_data["string_set"])]},
            "complex_list": {"L": sample_data["complex_list"][counter % len(sample_data["complex_list"])]},
            "binary_data": {"B": sample_data["binary_data"][counter % len(sample_data["binary_data"])]},
            "nested_list": {"L": sample_data["nested_list"][counter % len(sample_data["nested_list"])]},
            "binary_set": {"BS": sample_data["binary_set"][counter % len(sample_data["binary_set"])]}
        }
        items.append(item)
        counter += 1
    return items

# Load data into DynamoDB
def load_test_data(items):
    session = boto3.Session()
    dynamodb = session.client("dynamodb")

    for item in items:
        dynamodb.put_item(TableName=table_name, Item=item)
        print(f"Loaded item with table_pk={item['table_pk']['S']} sort_key={item['sort_key']['S']}")

if __name__ == "__main__":
    diverse_items = generate_items(base_partition_keys, base_sort_keys)
    load_test_data(diverse_items)