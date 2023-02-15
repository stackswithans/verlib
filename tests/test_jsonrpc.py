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
    req = parse_request(
        """{"jsonrpc": "2.0","method": "add", "params": [42, 13], "id": "hello2"}"""
    )
    assert req != None
    assert req.id == "hello2"
    req = parse_request(
        """{"jsonrpc": "2.0","method": "add", "params": [42, 13], "id": null}"""
    )
    assert req != None
    assert req.id is None


def test_parse_request_fails_when_using_weird_ids():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "add", "params": [42, 13], "id": 2.1212}"""
    )
    assert req is None


def test_parse_request_works_with_missing_params():
    req = parse_request("""{"jsonrpc": "2.0", "method": "sub", "id": 2}""")
    assert req != None
    assert req.params is None


def test_parse_request_fails_with_weirds_param_values():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": 2.121, "id": 2}"""
    )
    assert req is None

    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": 1, "id": 2}"""
    )
    assert req is None

    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": null, "id": 2}"""
    )
    assert req is None

    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": [], "id": 2}"""
    )
    assert req is None


def test_parse_request_works_with_notifications():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub", "params": [42, 13]}"""
    )
    assert req != None
    assert req.is_notification


def test_parse_request_works_with_notification_without_params():
    req = parse_request("""{"jsonrpc": "2.0", "method": "sub"}""")
    assert req != None
    assert req.is_notification
    assert req.params is None


def test_parse_request_works_with_named_params():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params":{"a": 21, "b": 23}, "id": 2}"""
    )
    assert req != None
    assert req.params == {"a": 21, "b": 23}
