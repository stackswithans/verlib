from src.verlib import VerLib
from src.jsonrpc import Request, ErrRes, OkRes
import src.jsonrpc as jsonrpc
import typing
from flask import Flask, request
import flask


class FlaskVerLib:
    def __init__(self, verlib: VerLib, api_url="/verlib"):
        self._verlib: VerLib = verlib
        self.api_url = api_url

    def init_app(self, app: Flask):
        self._dispatch_rpc_call = app.post(self.api_url)(
            self._dispatch_rpc_call
        )

    def _dispatch_rpc_call(self) -> flask.Response:

        req_json: dict = request.get_json()
        req_id = req_json.get("id")
        rpc_req = jsonrpc.into_rpc_request(request.get_json())

        if rpc_req.is_err():
            return flask.jsonify(ErrRes(req_id, rpc_req.unwrap_err()))

        rpc_call = rpc_req.unwrap()
        result = self._verlib.execute_rpc(rpc_call)

        if result.is_err():
            return flask.jsonify(
                ErrRes(rpc_call.id, typing.cast(ErrRes, result).err_data())
            )
        else:
            return flask.jsonify(OkRes(rpc_call.id, result.result_data()))
