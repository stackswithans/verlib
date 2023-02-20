from dataclasses import dataclass, field
import inspect
from enum import Enum
from inspect import Signature, BoundArguments, Parameter
from typing import Any, Callable, ParamSpec, TypeVar, Sized, cast
from src.jsonrpc import (
    Error,
    ErrorCode,
    ErrorMsg,
    JSONValues,
    Request,
    Response,
    OkRes,
    ErrRes,
)
from utils.request import Err, Ok, Result

P = ParamSpec("P")
T = TypeVar("T", bound=JSONValues)


VerProc = Callable[P, T]
VerProcParams = JSONValues


class VerProcErr(Enum):
    INVALID_PARAMS = 0


@dataclass
class VerProcedure:
    name: str
    _fn: Callable[..., JSONValues]
    _signature: Signature

    def call(
        self, params: list[JSONValues] | dict[str, JSONValues] | None
    ) -> Result[JSONValues, VerProcErr]:

        pos_params_len = len(
            tuple(
                filter(
                    lambda p: p.kind == Parameter.POSITIONAL_OR_KEYWORD,
                    self._signature.parameters.values(),
                )
            )
        )

        if params is None and pos_params_len > 0:
            return Err(VerProcErr.INVALID_PARAMS)

        if params is not None and len(params) < pos_params_len:
            return Err(VerProcErr.INVALID_PARAMS)

        # No parameters, just call the function
        # TODO: Make sure function can be called with 'null' arg
        if params is None or len(params) == 0:
            return Ok(self._fn())

        args, kwargs = ([], {})
        match params:
            case list(pos_params):
                args = pos_params
            case dict(dict_params):
                kwargs = dict_params
        try:
            ba = self._signature.bind(*args, **kwargs)
        except TypeError:
            return Err(VerProcErr.INVALID_PARAMS)
        return Ok(self._fn(*ba.args, **ba.kwargs))


@dataclass
class VerModule:
    name: str
    _procedures: dict[str, VerProcedure]

    def __init__(self, name: str):
        self.name = name
        self._procedures = {}

    def _register_proc(self, proc: VerProcedure):
        self._procedures[proc.name] = proc

    def verproc(
        self, fn: VerProc[P, T] | None = None, *, name: str = ""
    ) -> Callable[[VerProc[P, T]], VerProc[P, T]] | VerProc[P, T]:
        def verproc_decorator(procedure: VerProc[P, T]) -> VerProc[P, T]:
            proc_name = name if name != "" else procedure.__name__
            if proc_name in self._procedures:
                raise TypeError(
                    f"A procedure with the name '{proc_name}' has already been registered to the module '{self.name}'"
                )

            self._register_proc(
                VerProcedure(proc_name, procedure, inspect.signature(procedure))
            )
            return procedure

        if fn is None:
            return verproc_decorator
        else:
            return verproc_decorator(fn)

    def contains_proc(self, name: str) -> bool:
        return name in self._procedures

    def call_procedure(
        self,
        proc_name: str,
        params: list[JSONValues] | dict[str, JSONValues] | None,
    ) -> Result[JSONValues, VerProcErr]:
        return self._procedures[proc_name].call(params)


@dataclass
class VerLib:
    name: str
    _modules: dict[str, VerModule]

    def __init__(self, name: str):
        self.name = name
        self._default_module: VerModule = VerModule("_default_")
        self._modules = {}

    def declare_module(self, module: VerModule):
        mod_name = module.name
        if mod_name in self._modules:
            raise TypeError(
                f"A module with the name '{mod_name}' has already been declared"
            )
        self._modules[mod_name] = module

    def verproc(
        self, fn: VerProc[P, T] | None = None, *, name: str = ""
    ) -> Callable[[VerProc[P, T]], VerProc[P, T]] | VerProc[P, T]:

        return self._default_module.verproc(fn, name=name)

    def _resolve_proc(self, name: str) -> tuple[VerModule | None, str]:
        components = name.split(".")
        if len(components) == 1:
            return (self._default_module, components[0])
        elif len(components) == 2:
            return (
                self._modules.get(components[0]),
                components[1],
            )
        else:
            return (None, "")

    def execute_rpc(self, req: Request) -> Response[JSONValues, None]:
        # Check if module and method both exist
        module, proc_name = self._resolve_proc(req.method)
        if not module or not module.contains_proc(proc_name):
            return ErrRes(
                req.id,
                Error(
                    ErrorCode.METHOD_NOT_FOUND,
                    ErrorMsg.METHOD_NOT_FOUND.format(req.method),
                    None,
                ),
            )

        result: Result[JSONValues, VerProcErr] = module.call_procedure(
            proc_name, req.params
        )

        ignore_result: bool = req.is_notification
        if result.is_ok():
            return OkRes(req.id, result.unwrap() if not ignore_result else None)

        match result.unwrap_err():
            case VerProcErr.INVALID_PARAMS:
                return ErrRes(
                    req.id,
                    Error(
                        ErrorCode.INVALID_PARAMS,
                        ErrorMsg.INVALID_PARAMS.value,
                        None,
                    ),
                )

        return ErrRes(req.id, Error(-1, "", None))
