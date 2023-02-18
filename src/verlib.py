from dataclasses import dataclass, field
from typing import Any, Callable, ParamSpec, TypeVar, cast
from typing_extensions import TypeVarTuple, Unpack
from src.jsonrpc import Request, Response, Error, JSONValues
from utils.request import Result, Ok, Err

P = ParamSpec("P")
T = TypeVar("T", bound=JSONValues)


VerProc = Callable[P, T]
VerProcParams = JSONValues


@dataclass
class VerModule:
    name: str
    _procedures: dict[str, Callable[..., JSONValues]] = field(
        default_factory=dict
    )

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

            self._procedures[proc_name] = procedure
            return procedure

        return verproc_decorator

    def invoke(
        self, name: str, params: VerProcParams
    ) -> Response[JSONValues, None]:
        return cast(Any, 0)


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

            self._ver_module._procedures[proc_name] = procedure
            return procedure

        return verproc_decorator

    def _resolve_method(self, name: str) -> VerProc | None:
        components = name.split(".")
        if len(components) == 1:
            return self._ver_module._procedures.get(name)
        elif len(components) == 2:
            return cast(
                VerModule, self._modules.get(components[0])
            )._procedures.get(name)
        else:
            return None

    def invoke(self, req: Request) -> Response[JSONValues, None]:
        # 1. Check if module and method both exist
        method = self._resolve_method(req.method)
        if not method:
            # Return METHOD_NOT_FOUND ERROR
            return cast(Any, None)
        # 2. Check params (arity, type and name)
        # 3. Return result of function invocation params (arity, type and name)

        return cast(Any, None)
