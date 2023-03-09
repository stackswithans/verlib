from enum import IntEnum, Enum
from dataclasses import dataclass
from verlib.jsonrpc import (
    ErrRes,
    JSONRPCId,
    ErrorCode as JErrorCode,
    ErrorMsg as JErrorMsg,
    Error as JError,
)
import verlib.jsonrpc as jsonrpc


class ErrKind(IntEnum):
    INVALID_PARAMS = 0
    PROCEDURE_RAISED_EXCEPTION = -32500
    NOT_AUTHORIZED = -32501


class ErrMsg(Enum):
    INVALID_PARAMS = "Invalid procedure parameter(s)."
    PROCEDURE_RAISED_EXCEPTION = (
        "An error occurred during the execution of the procedure."
    )
    NOT_AUTHORIZED = "Insufficient privileges to invoke procedure."

    def __str__(self) -> str:
        return self.value


@dataclass
class VerLibErr:
    err_kind: ErrKind
    msg: ErrMsg
    exc: Exception | None = None

    def into_json_rpc_err(
        self,
        req_id: JSONRPCId,
    ) -> ErrRes:
        match self.err_kind:
            case ErrKind.INVALID_PARAMS:
                return ErrRes(
                    req_id,
                    JError(
                        JErrorCode.INVALID_PARAMS,
                        JErrorMsg.INVALID_PARAMS.value,
                        None,
                    ),
                )
            case ErrKind.PROCEDURE_RAISED_EXCEPTION:
                # TODO: Design error treatment flow
                assert isinstance(self.exc, Exception)
                raise self.exc
            case _:
                return ErrRes(req_id, JError(-1, "", None))
