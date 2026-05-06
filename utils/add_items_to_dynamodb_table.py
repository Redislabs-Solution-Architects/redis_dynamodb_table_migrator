import boto3
from itertools import product

table_name = "gabs-migrator-table"

base_sort_keys = [f"sort-{chr(65 + i)}" for i in range(10)]  # A-J
base_partition_keys = [f"item-{i}" for i in range(25)]        # item-0 to item-24

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
        "U29tZSBiaW5hcnkgZGF0YQ==",  # "Some binary data"
        "RGF0YQ=="                    # "Data"
    ],
    "nested_list": [
        [{"S": "List Item 1"}, {"N": "123"}, {"M": {"key1": {"BOOL": True}, "key2": {"S": "Nested String"}}}],
        [{"S": "List Item 2"}, {"N": "456"}, {"M": {"key1": {"BOOL": False}, "key2": {"S": "Another Nested String"}}}],
    ],
    "binary_set": [
        ["QmluYXJ5MQ==", "QmluYXJ5Mg=="],
        ["QmluYXJ5Mw=="]
    ],
    "nullable_field": [True, False],
}


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
            "number_set": {"NS": [str(num) for num in sample_data["number_set"][counter % len(sample_data["number_set"])]]},
            "string_set": {"SS": sample_data["string_set"][counter % len(sample_data["string_set"])]},
            "complex_list": {"L": sample_data["complex_list"][counter % len(sample_data["complex_list"])]},
            "binary_data": {"B": sample_data["binary_data"][counter % len(sample_data["binary_data"])]},
            "nested_list": {"L": sample_data["nested_list"][counter % len(sample_data["nested_list"])]},
            "binary_set": {"BS": sample_data["binary_set"][counter % len(sample_data["binary_set"])]},
        }
        if sample_data["nullable_field"][counter % len(sample_data["nullable_field"])]:
            item["optional_null_field"] = {"NULL": True}
        items.append(item)
        counter += 1
    return items


def generate_edge_case_items():
    """Items that exercise every conversion edge case in sanitize_dynamodb_value."""
    return [
        # --- ISO datetime strings (should become Unix timestamps) ---
        {
            "table_pk": {"S": "edge-datetime"},
            "sort_key": {"S": "sort-1"},
            "ts_utc_z":       {"S": "2024-01-15T10:30:00Z"},
            "ts_with_millis": {"S": "2024-06-20T14:45:30.500Z"},
            "ts_space_sep":   {"S": "2023-12-31 23:59:59"},
            "ts_no_tz":       {"S": "2025-03-10T08:00:00"},
            "plain_string":   {"S": "not-a-date"},
            "label": {"S": "datetime edge cases"},
        },

        # --- Stringified JSON (should be unwrapped into real objects) ---
        {
            "table_pk": {"S": "edge-stringified-json"},
            "sort_key": {"S": "sort-1"},
            "config":            {"S": '{"theme": "dark", "timeout": 30, "features": ["search", "export"]}'},
            "nested_str_json":   {"S": '{"level1": {"level2": "deep value"}}'},
            "json_array_string": {"S": '[1, 2, 3, "four"]'},
            "label": {"S": "stringified json edge cases"},
        },

        # --- Float and edge-case numbers ---
        {
            "table_pk": {"S": "edge-floats"},
            "sort_key": {"S": "sort-1"},
            "price":          {"N": "19.99"},
            "tax_rate":       {"N": "0.075"},
            "pi":             {"N": "3.14159265358979"},
            "negative_float": {"N": "-273.15"},
            "zero":           {"N": "0"},
            "large_int":      {"N": "9999999999"},
            "whole_decimal":  {"N": "42.0"},
            "label": {"S": "float and number edge cases"},
        },

        # --- Empty collections ---
        {
            "table_pk": {"S": "edge-empty"},
            "sort_key": {"S": "sort-1"},
            "empty_list": {"L": []},
            "empty_map":  {"M": {}},
            "label": {"S": "empty collection edge cases"},
        },

        # --- Unicode and emoji ---
        {
            "table_pk": {"S": "edge-unicode"},
            "sort_key": {"S": "sort-1"},
            "emoji":    {"S": "Hello 🌍! Olá 🇧🇷 🎉"},
            "japanese": {"S": "日本語テスト"},
            "arabic":   {"S": "مرحبا بالعالم"},
            "mixed":    {"S": "Ñoño niño 中文 한국어 Ünïcödé"},
            "label": {"S": "unicode edge cases"},
        },

        # --- NULL type ---
        {
            "table_pk": {"S": "edge-null"},
            "sort_key": {"S": "sort-1"},
            "explicit_null":   {"NULL": True},
            "another_null":    {"NULL": True},
            "non_null_string": {"S": "I am not null"},
            "label": {"S": "null type edge cases"},
        },

        # --- Binary data: valid UTF-8 and non-UTF-8 (should base64-encode fallback) ---
        {
            "table_pk": {"S": "edge-binary"},
            "sort_key": {"S": "sort-1"},
            "utf8_binary":     {"B": b"Hello binary world"},
            "non_utf8_binary": {"B": bytes([0x80, 0x81, 0x82, 0xFF, 0xFE])},
            "label": {"S": "binary edge cases"},
        },

        # --- Deep nesting (5 levels) ---
        {
            "table_pk": {"S": "edge-deep-nested"},
            "sort_key": {"S": "sort-1"},
            "level1": {
                "M": {
                    "level2": {
                        "M": {
                            "level3": {
                                "M": {
                                    "level4": {
                                        "M": {
                                            "level5": {
                                                "M": {
                                                    "deep_value":  {"S": "I am deeply nested!"},
                                                    "deep_number": {"N": "42"},
                                                    "deep_bool":   {"BOOL": True},
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "label": {"S": "deep nesting edge cases"},
        },

        # --- Mixed-type list (string, number, bool, null, map, list) ---
        {
            "table_pk": {"S": "edge-mixed-list"},
            "sort_key": {"S": "sort-1"},
            "mixed_types_list": {
                "L": [
                    {"S": "a string"},
                    {"N": "42"},
                    {"BOOL": True},
                    {"NULL": True},
                    {"M": {"nested_key": {"S": "nested_val"}}},
                    {"L": [{"N": "1"}, {"N": "2"}, {"N": "3"}]},
                ]
            },
            "label": {"S": "mixed type list edge cases"},
        },

        # --- Number set and string set with multiple values ---
        {
            "table_pk": {"S": "edge-sets"},
            "sort_key": {"S": "sort-1"},
            "big_number_set": {"NS": ["1.5", "2.5", "3.14", "100", "0.001"]},
            "big_string_set": {"SS": ["alpha", "beta", "gamma", "delta", "epsilon"]},
            "binary_set":     {"BS": [b"bin1", b"bin2", b"\x00\x01\x02"]},
            "label": {"S": "sets edge cases"},
        },
    ]


def load_test_data(items, dynamodb_client):
    for item in items:
        dynamodb_client.put_item(TableName=table_name, Item=item)
        pk = item["table_pk"]["S"]
        sk = item["sort_key"]["S"]
        print(f"Loaded item: table_pk={pk}  sort_key={sk}")


if __name__ == "__main__":
    session = boto3.Session()
    client = session.client("dynamodb")

    print("=== Loading standard generated items ===")
    standard_items = generate_items(base_partition_keys, base_sort_keys)
    load_test_data(standard_items, client)

    print("\n=== Loading edge-case items ===")
    edge_items = generate_edge_case_items()
    load_test_data(edge_items, client)

    print(f"\nDone. Loaded {len(standard_items)} standard + {len(edge_items)} edge-case items.")
