from verlib.integrations.flask import FlaskVerLib
from verlib.jsonrpc import Request
from verlib import VerLib
from verlib.call import Context, HttpHeaders
from verlib.auth import AccessLevel

from flask import Flask
from flask.testing import FlaskClient
from typing import Any, cast
import pytest


@pytest.fixture
def test_lib(auth_key: str) -> VerLib:
    verlib = VerLib("Testlib")

    @verlib.verproc
    def foo():
        return 1

    @verlib.verproc
    def add(a: int, b: int) -> int:
        return a + b

    @verlib.private_access
    @verlib.verproc
    def double(a: int) -> int:
        return a * 2

    @verlib.context_builder
    def context_builder(headers: HttpHeaders, req: Request) -> Context:
        context = Context()
        context.is_authenticated = headers.get("X-API-KEY") == auth_key
        context.header_msg = headers.get("X-HEADER-MSG")
        return context

    @verlib.auth_provider
    def auth_provider(
        headers: HttpHeaders, req: Request, context: Context
    ) -> AccessLevel:
        return (
            AccessLevel.private
            if context.is_authenticated
            else AccessLevel.public
        )

    return verlib


@pytest.fixture
def auth_key() -> str:
    return "baz"


@pytest.fixture()
def jsonrpc_headers() -> dict:
    return {"id": 1, "jsonrpc": "2.0"}


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(
        {
            "TESTING": True,
        }
    )

    yield app


@pytest.fixture()
def test_app(app: Flask, test_lib: VerLib):
    flask_verlib = FlaskVerLib(test_lib)
    flask_verlib.init_app(app)

    return app


@pytest.fixture()
def client(test_app: Flask):
    return test_app.test_client()


@pytest.fixture()
def runner(app: Flask):
    return app.test_cli_runner()


def test_flask_verlib_initialized_correctly(app: Flask, test_lib: VerLib):
    flask_verlib = FlaskVerLib(test_lib)
    flask_verlib.init_app(app)

    assert any(map(lambda r: str(r) == "/verlib", app.url_map.iter_rules()))


def test_flask_verlib_sets_correct_endpoint(app: Flask, test_lib: VerLib):
    flask_verlib = FlaskVerLib(test_lib, "/api")
    flask_verlib.init_app(app)

    assert any(map(lambda r: str(r) == "/api", app.url_map.iter_rules()))


def test_succesful_rpc_request(
    client: FlaskClient, jsonrpc_headers: dict[str, Any]
):
    res = client.post(
        "/verlib",
        json={**jsonrpc_headers, "method": "add", "params": [42, 13]},
    )
    assert res.json == {"id": 1, "jsonrpc": "2.0", "result": 55}


def test_res_on_invalid_request_error(
    client: FlaskClient, jsonrpc_headers: dict[str, Any]
):
    res = client.post(
        "/verlib",
        json={"method": "add", "params": [42, 13]},
    )

    assert res.json == {
        "id": None,
        "jsonrpc": "2.0",
        "error": {"code": -32600, "message": "Invalid Request", "data": None},
    }


def test_res_on_invalid_params(
    client: FlaskClient, jsonrpc_headers: dict[str, Any]
):
    res = client.post(
        "/verlib",
        json={**jsonrpc_headers, "method": "add", "params": [13]},
    )

    assert res.json == {
        "id": 1,
        "jsonrpc": "2.0",
        "error": {
            "code": -32602,
            "message": "Invalid method parameter(s).",
            "data": None,
        },
    }


def test_res_on_exception(client: FlaskClient, jsonrpc_headers: dict[str, Any]):
    with pytest.raises(Exception):
        res = client.post(
            "/verlib",
            json={**jsonrpc_headers, "method": "add", "params": [None, 13]},
        )


def test_res_on_lib_import(client: FlaskClient):
    with pytest.raises(Exception):
        res = client.get("/verlib/import")
        lib_import: dict = cast(dict, res.json)

        assert lib_import["id"] == None
        assert lib_import["result"] is not None
        assert len(lib_import["result"]) == 3
        assert all(
            map(
                lambda p: "name" in p
                and "num_params" in p
                and p["module"] in ("_default_", "test_module"),
                lib_import["result"],
            )
        )


def test_cannot_access_private_method_without_auth(
    client: FlaskClient, jsonrpc_headers: dict[str, Any]
):
    res = client.post(
        "/verlib",
        json={**jsonrpc_headers, "method": "double", "params": [13]},
    )

    assert res.json == {
        "id": 1,
        "jsonrpc": "2.0",
        "error": {
            "code": -32501,
            "message": "Insufficient privileges to invoke procedure.",
            "data": None,
        },
    }


def test_can_access_private_method_with_auth(
    client: FlaskClient, jsonrpc_headers: dict[str, Any], auth_key: str
):
    res = client.post(
        "/verlib",
        json={**jsonrpc_headers, "method": "double", "params": [13]},
        headers={"X-API-KEY": auth_key},
    )

    assert res.json == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": 26,
    }
