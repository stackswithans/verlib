from dataclasses import dataclass, field
from typing import Any, Callable, ParamSpec, TypeVar, cast
from src.jsonrpc import Request, Response, JSONValues

P = ParamSpec("P")
T = TypeVar("T")

VerProc = Callable[P, T]
VerProcParams = dict[str, JSONValues]


@dataclass
class VerModule:
    name: str
    _procedures: dict[str, VerProc] = field(default_factory=dict)

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

    def invoke(self, name: str, params: VerProcParams) -> Response[JSONValues]:
        return 0


@dataclass
class VerLib:
    name: str
    modules: dict[str, VerModule] = field(default_factory=dict)

    def __init__(self, name: str):
        self.name = name
        self._ver_module: VerModule = VerModule("main")

    def declare_module(self, module: VerModule):
        mod_name = module.name
        if self.modules[mod_name] in self.modules:
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

    def invoke(self, req: Request) -> Response[JSONValues]:
        return cast(Any, None)
