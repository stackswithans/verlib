from dataclasses import dataclass, field
import inspect
from enum import Enum, IntEnum
from inspect import Signature, BoundArguments, Parameter
from typing import Any, Callable, ParamSpec, TypeVar, Sized, cast
from verlib.verliberr import ErrKind, ErrMsg, VerLibErr
from verlib.jsonrpc import (
    Error,
    ErrorCode,
    ErrorMsg,
    JSONValues,
    Request,
    Response,
    OkRes,
    ErrRes,
)
from utils.result import Err, Ok, Result

P = ParamSpec("P")
T = TypeVar("T", bound=JSONValues)


VerProc = Callable[P, T]
VerProcParams = JSONValues


@dataclass
class VerProcedure:
    name: str
    _fn: Callable[..., JSONValues]
    _signature: Signature

    def call(
        self, params: list[JSONValues] | dict[str, JSONValues] | None
    ) -> Result[JSONValues, VerLibErr]:

        pos_params_len = len(
            tuple(
                filter(
                    lambda p: p.kind == Parameter.POSITIONAL_OR_KEYWORD,
                    self._signature.parameters.values(),
                )
            )
        )

        if params is None and pos_params_len > 0:
            return Err(VerLibErr(ErrKind.INVALID_PARAMS, ErrMsg.INVALID_PARAMS))

        if params is not None and len(params) < pos_params_len:
            return Err(VerLibErr(ErrKind.INVALID_PARAMS, ErrMsg.INVALID_PARAMS))

        # TODO: Make sure function can be called with 'null' arg
        if params is None or len(params) == 0:
            return Ok(self._fn())

        args, kwargs = ([], {})
        match params:
            case list(pos_params):
                args = pos_params
            case dict(dict_params):
                kwargs = dict_params
        # TODO: Add type checking for parameters
        try:
            ba = self._signature.bind(*args, **kwargs)
        except TypeError:
            return Err(VerLibErr(ErrKind.INVALID_PARAMS, ErrMsg.INVALID_PARAMS))

        # TODO: Decide on the best way to deal with exceptions
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

    def _contains_proc(self, name: str) -> bool:
        return name in self._procedures

    def _call_procedure(
        self,
        proc_name: str,
        params: list[JSONValues] | dict[str, JSONValues] | None,
    ) -> Result[JSONValues, VerLibErr]:
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
        if not module or not module._contains_proc(proc_name):
            return ErrRes(
                req.id,
                Error(
                    ErrorCode.METHOD_NOT_FOUND,
                    ErrorMsg.METHOD_NOT_FOUND.format(req.method),
                    None,
                ),
            )

        result: Result[JSONValues, VerLibErr] = module._call_procedure(
            proc_name, req.params
        )

        ignore_result: bool = req.is_notification
        if result.is_ok():
            return OkRes(req.id, result.unwrap() if not ignore_result else None)

        return result.unwrap_err().into_json_rpc_err(req.id)
