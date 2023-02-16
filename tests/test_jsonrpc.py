import json
import pytest
from src.jsonrpc import parse_request, ErrorCode


def test_parse_request_works():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "add", "params": [42, 13], "id": 1}"""
    )

    req = req.unwrap()
    assert req.id == 1
    assert req.jsonrpc == "2.0"
    assert req.method == "add"
    assert req.params == [42, 13]


def test_parse_request_errors_when_missing_jsonrpc_field():
    req = parse_request("""{"method": "add", "params": [42, 13], "id": 1}""")
    err = req.unwrap_err()
    assert err.code == ErrorCode.INVALID_REQUEST
    assert err.message == "Invalid Request"


def test_parse_request_works_when_using_null_and_str_ids():
    req = parse_request(
        """{"jsonrpc": "2.0","method": "add", "params": [42, 13], "id": "hello2"}"""
    ).unwrap()
    assert req.id == "hello2"

    req = parse_request(
        """{"jsonrpc": "2.0","method": "add", "params": [42, 13], "id": null}"""
    ).unwrap()
    assert req.id is None


def test_parse_request_fails_when_using_weird_ids():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "add", "params": [42, 13], "id": 2.1212}"""
    )
    err = req.unwrap_err()
    assert err.code == ErrorCode.INVALID_REQUEST
    assert err.message == "Invalid Request"


def test_parse_request_works_with_missing_params():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub", "id": 2}"""
    ).unwrap()

    assert req.params is None


def test_parse_request_fails_with_weirds_param_values():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": 2.121, "id": 2}"""
    )
    err = req.unwrap_err()
    assert err.code == ErrorCode.INVALID_REQUEST
    assert err.message == "Invalid Request"

    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": 1, "id": 2}"""
    )
    err = req.unwrap_err()
    assert err.code == ErrorCode.INVALID_REQUEST
    assert err.message == "Invalid Request"

    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": null, "id": 2}"""
    )
    err = req.unwrap_err()
    assert err.code == ErrorCode.INVALID_REQUEST
    assert err.message == "Invalid Request"

    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params": [], "id": 2}"""
    )
    err = req.unwrap_err()
    assert err.code == ErrorCode.INVALID_REQUEST
    assert err.message == "Invalid Request"


def test_parse_request_works_with_notifications():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub", "params": [42, 13]}"""
    ).unwrap()
    assert req.is_notification


def test_parse_request_works_with_notification_without_params():
    req = parse_request("""{"jsonrpc": "2.0", "method": "sub"}""").unwrap()
    assert req.is_notification
    assert req.params is None


def test_parse_request_works_with_named_params():
    req = parse_request(
        """{"jsonrpc": "2.0", "method": "sub","params":{"a": 21, "b": 23}, "id": 2}"""
    ).unwrap()

    assert req.params == {"a": 21, "b": 23}
