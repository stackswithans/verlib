from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Any, cast
from schema import Schema, And, Or, Optional
from typing_extensions import Self
import json


JSONValues = int | str | float | list[Any] | dict[str, Any]
JSONRPCId = int | str | None

values_schema = Schema(Or(int, str, float, list, dict))

request_schema = Schema(
    {
        "jsonrpc": "2.0",
        Optional("id"): Or(int, str, lambda x: x is None),
        "method": str,
        Optional("params"): Or(
            {str: values_schema}, And([values_schema], lambda l: len(l) > 0)
        ),
    }
)


@dataclass(kw_only=True)
class Request:
    jsonrpc: Literal["2.0"]
    id: int | str | None = None
    method: str
    params: dict[str, JSONValues] | list[JSONValues] | None = None
    is_notification: bool = False

    @classmethod
    def from_dict(cls, req_dict: dict[str, Any]) -> Self:
        is_notification = req_dict.get("id") is None
        return cls(**req_dict, is_notification=is_notification)


def parse_request(req: str) -> Request | None:

    try:
        req_dict: dict[str, Any] = json.loads(req)
    except TypeError:
        return None

    is_valid_req = request_schema.is_valid(req_dict)
    # request_schema.validate(req_dict)

    if not is_valid_req:
        # Return appropriate error
        return None

    return Request.from_dict(req_dict)
