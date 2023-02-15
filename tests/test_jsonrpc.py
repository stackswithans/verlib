import json
import pytest
from src.jsonrpc import parse_request


def test_parse_request_works():
    req = parse_request(
        json.dumps(
            {"jsonrpc": "2.0", "method": "add", "params": [42, 13], "id": 1}
        )
    )

    assert req != None
    assert req.id == 1
    assert req.jsonrpc == "2.0"
    assert req.method == "add"
    assert req.params == [42, 13]


def test_parse_request_errors_when_missing_jsonrpc_field():
    req = parse_request(
        json.dumps({"method": "add", "params": [42, 13], "id": 1})
    )

    assert req == None
