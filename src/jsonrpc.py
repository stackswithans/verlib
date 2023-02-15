from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Any, cast
from schema import Schema, Or
from typing_extensions import Self
import json


JSONValues = int | str | float | list[Any] | dict[str, Any]
JSONRPCId = int | str | None

values_schema = Schema(Or(int, str, float, list, dict))

request_schema = Schema(
    {
        "jsonrpc": "2.0",
        "id": Or(int, str, lambda x: x is None),
        "method": str,
        "params": Or({str: values_schema}, [values_schema]),
    }
)


@dataclass
class Request:
    jsonrpc: Literal["2.0"]
    id: int | str | None
    method: str
    params: dict[str, JSONValues] | list[JSONValues]

    @classmethod
    def from_dict(cls, req_dict: dict[str, Any]) -> Self:
        return cls(
            req_dict["jsonrpc"],
            req_dict["id"],
            req_dict["method"],
            req_dict["params"],
        )


def parse_request(req: str) -> Request | None:

    try:
        req_dict: dict[str, Any] = json.loads(req)
    except TypeError:
        return None

    is_valid_req = request_schema.is_valid(req_dict)

    if not is_valid_req:
        # Return appropriate error
        return None

    return Request.from_dict(req_dict)
