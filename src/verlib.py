from dataclasses import dataclass, field
import inspect
from enum import Enum
from inspect import Signature, BoundArguments
from typing import Any, Callable, ParamSpec, TypeVar, cast
from typing_extensions import TypeVarTuple, Unpack
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

        # No parameters, just call the function
        # TODO: Make sure function can be called with 'null' arg
        if params is None:
            return Ok(self._fn())

        args, kwargs = ([], {})
        match params:
            case list(pos_params):
                args = pos_params
            case dict(dict_params):
                kwargs = dict_params
        try:
            ba = self._signature.bind(*args, **kwargs)
            return Ok(self._fn(*ba.args, **ba.kwargs))
        except TypeError:
            return Err(VerProcErr.INVALID_PARAMS)


@dataclass
class VerModule:
    name: str
    _procedures: dict[str, VerProcedure] = field(default_factory=dict)

    def __init__(self, name: str):
        self.name = name

    def verproc(
        self, name: str = ""
    ) -> Callable[[VerProc[P, T]], VerProc[P, T]]:
        def verproc_decorator(procedure: VerProc[P, T]) -> VerProc[P, T]:
            proc_name = name if name != "" else procedure.__name__
            if proc_name in self._procedures:
                raise Exception(
                    f"A procedure with the name '{proc_name}' has already been registered to the module"
                )

            self.register_proc(
                VerProcedure(name, procedure, inspect.signature(procedure))
            )
            return procedure

        return verproc_decorator

    def get_proc(self, name: str) -> VerProcedure | None:
        return self._procedures.get(name)

    def register_proc(self, proc: VerProcedure):
        self._procedures[proc.name] = proc


@dataclass
class VerLib:
    name: str
    _modules: dict[str, VerModule] = field(default_factory=dict)

    def __init__(self, name: str):
        self.name = name
        self._ver_module: VerModule = VerModule("main")

    def declare_module(self, module: VerModule):
        mod_name = module.name
        if self._modules[mod_name] in self._modules:
            raise Exception(
                f"A module with the name '{mod_name}' has already be registered to the library instance"
            )

    def verproc(
        self, name: str = ""
    ) -> Callable[[VerProc[P, T]], VerProc[P, T]]:
        def verproc_decorator(procedure: VerProc[P, T]) -> VerProc[P, T]:
            proc_name = name if name != "" else procedure.__name__
            if proc_name in self._ver_module._procedures:
                raise Exception(
                    f"A procedure with the name '{proc_name}' has already been registered to the libray instance"
                )

            self._ver_module.register_proc(
                VerProcedure(name, procedure, inspect.signature(procedure))
            )
            return procedure

        return verproc_decorator

    def _find_procedure(self, name: str) -> VerProcedure | None:
        components = name.split(".")
        if len(components) == 1:
            return self._ver_module.get_proc(name)
        elif len(components) == 2:
            return cast(VerModule, self._modules.get(components[0])).get_proc(
                name
            )
        else:
            return None

    def invoke_proc(self, req: Request) -> Response[JSONValues, None]:
        # Check if module and method both exist
        proc = self._find_procedure(req.method)
        if not proc:
            return ErrRes(
                req.id,
                Error(
                    ErrorCode.METHOD_NOT_FOUND,
                    ErrorMsg.METHOD_NOT_FOUND.format(req.method),
                    None,
                ),
            )

        result: Result[JSONValues, VerProcErr] = proc.call(req.params)
        if result.is_ok():
            ignore_result: bool = req.is_notification
            return OkRes(req.id, result.unwrap() if not ignore_result else None)

        return ErrRes(req.id, Error(-1, "", None))