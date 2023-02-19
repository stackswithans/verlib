from __future__ import annotations
import dataclasses
import abc
from dataclasses import dataclass
from typing import Literal, TypeAlias, Any, TypeVar, Generic, cast
from enum import Enum
import json
from schema import Schema, And, Or, Optional
from typing_extensions import Self
from utils.request import Result, Ok, Err


JSONValues = (
    int | str | float | list["JSONValues"] | dict[str, "JSONValues"] | None
)


JSONRPCId = int | str | None

V = TypeVar("V")

E = TypeVar("E")

values_schema = Schema(Or(int, str, float, list, dict, lambda x: x is None))

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


class ErrorMsg(Enum):
    METHOD_NOT_FOUND = "The procedure '{0}' was not found on the server."

    def format(self, *args: Any, **kwargs: Any) -> str:
        return self.value.format(args, kwargs)


@dataclass
class Error(Generic[E]):
    code: ErrorCode | int
    message: str
    data: E


@dataclass
class OkRes(Generic[V]):
    id: JSONRPCId
    result: V
    jsonrpc: Literal["2.0"] = "2.0"

    def __init__(self, id: JSONRPCId, result: V):
        self.id = id
        self.result = result

    def err_data(self) -> None:
        return None

    def result_data(self) -> V:
        return self.result

    def is_err(self) -> bool:
        return False

    def is_success(self) -> bool:
        return True

    def to_dict(self) -> dict[str, JSONValues]:
        return dataclasses.asdict(self)


@dataclass
class ErrRes(Generic[E]):
    id: JSONRPCId
    error: Error[E]
    jsonrpc: Literal["2.0"] = "2.0"

    def __init__(self, id: JSONRPCId, error: Error[E]):
        self.id = id
        if error.code in (ErrorCode.PARSE_ERROR, ErrorCode.INVALID_REQUEST):
            self.id = None
        self.error = error

    def err_data(self) -> Error[E]:
        return self.error

    def result_data(self) -> None:
        return None

    def is_err(self) -> bool:
        return True

    def is_success(self) -> bool:
        return False

    def to_dict(self) -> dict[str, JSONValues]:
        return dataclasses.asdict(self)


Response = OkRes[V] | ErrRes[E]


def parse_request(req: str) -> Result[Request, Error[None]]:

    try:
        req_dict: dict[str, Any] = json.loads(req)
    except TypeError:
        return Err(Error(ErrorCode.PARSE_ERROR, "Parse error", None))

    is_valid_req = request_schema.is_valid(req_dict)

    if not is_valid_req:
        return Err(Error(ErrorCode.INVALID_REQUEST, "Invalid Request", None))

    return Ok(Request.from_dict(req_dict))
