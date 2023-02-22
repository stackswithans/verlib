from src.verlib import VerLib
from src.jsonrpc import Request, ErrRes, OkRes
import jsonrpc
import typing
from flask import Flask
import flask


class FlaskVerLib:
    def __init__(self, verlib: VerLib, api_url="api/"):
        self._verlib: VerLib = verlib
        self.api_url = api_url

    def init_app(self, app: Flask):
        app.route(self.api_url)(self._dispatch_rpc_call)

    def _dispatch_rpc_call(self, req: flask.Request) -> flask.Response:

        req_json: dict = req.get_json()
        req_id = req_json.get("id")
        rpc_req = jsonrpc.into_rpc_request(req.get_json())

        if rpc_req.is_err():
            return flask.jsonify(ErrRes(req_id, rpc_req.unwrap_err()).to_dict)

        rpc_call = rpc_req.unwrap()
        result = self._verlib.execute_rpc(rpc_call)

        if result.is_err():
            return flask.jsonify(
                ErrRes(rpc_call.id, typing.cast(ErrRes, result).err_data())
            )
        else:
            return flask.jsonify(OkRes(rpc_call.id, result.result_data()))
