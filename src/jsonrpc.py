from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Any, TypeVar, Generic, cast
from enum import Enum
import json
from schema import Schema, And, Or, Optional
from typing_extensions import Self
from utils.request import Result, Ok, Err


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


class ErrorCode(Enum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


T = TypeVar("T", bound=JSONValues | None)


@dataclass
class Error(Generic[T]):
    code: ErrorCode | int
    message: str
    data: T


def parse_request(req: str) -> Result[Request, Error[None]]:

    try:
        req_dict: dict[str, Any] = json.loads(req)
    except TypeError:
        return Err(Error(ErrorCode.PARSE_ERROR, "Parse error", None))

    is_valid_req = request_schema.is_valid(req_dict)

    if not is_valid_req:
        return Err(Error(ErrorCode.INVALID_REQUEST, "Invalid Request", None))

    return Ok(Request.from_dict(req_dict))
