import json
import pytest
from src.jsonrpc import parse_request


def test_parse_request_works():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "add", "params": [42, 13], "id": 1}"""
    )

    assert req != None
    assert req.id == 1
    assert req.jsonrpc == "2.0"
    assert req.method == "add"
    assert req.params == [42, 13]


def test_parse_request_errors_when_missing_jsonrpc_field():
    req = parse_request("""{"method": "add", "params": [42, 13], "id": 1}""")
    assert req == None


def test_parse_request_works_when_using_null_and_str_ids():
    req = parse_request("""{"method": "add", "params": [42, 13], "id": 1}""")
    assert req == None


def test_parse_request_fails_when_using_weird_ids():
    pass


def test_parse_request_works_with_missing_params():
    pass


def test_parse_request_works_with_missing_id():
    pass


def test_parse_request_works_with_named_params():
    pass


def test_parse_request_works_with_missing_id_and_params():
    pass
