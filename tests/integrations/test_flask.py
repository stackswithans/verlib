from src.integrations.flask import FlaskVerLib
from flask import Flask
from flask.testing import FlaskClient
from src.verlib import VerLib
from typing import Any
import pytest


@pytest.fixture
def test_lib() -> VerLib:
    verlib = VerLib("Testlib")

    @verlib.verproc
    def foo():
        return 1

    @verlib.verproc
    def add(a: int, b: int) -> int:
        return a + b

    return verlib


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
