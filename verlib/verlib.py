from __future__ import annotations
from dataclasses import dataclass, field
import inspect
from enum import Enum, IntEnum
from inspect import Signature, BoundArguments, Parameter
from typing import (
    TypedDict,
    Callable,
    ParamSpec,
    TypeVar,
    cast,
)
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
from verlib.auth import AccessLevel
from verlib.call import HttpHeaders, Context, ContextBuilder, AuthProvider
from utils.result import Err, Ok, Result

P = ParamSpec("P")
T = TypeVar("T", bound=JSONValues)


VerProc = Callable[P, T]
VerProcParams = JSONValues
DecoratedVerProc = Callable[..., VerProc[P, T]] | VerProc[P, T]

_empty_headers: HttpHeaders = HttpHeaders({})


class VerProcDesc(TypedDict):
    module: str | None
    name: str
    num_params: int


VerLibDesc = list[VerProcDesc]


@dataclass
class VerProcedure:
    name: str
    _fn: Callable[..., JSONValues]
    _signature: Signature
    access_level: AccessLevel = AccessLevel.public

    def _get_num_params(self) -> int:
        return len(
            tuple(
                filter(
                    lambda p: p.kind == Parameter.POSITIONAL_OR_KEYWORD,
                    self._signature.parameters.values(),
                )
            )
        )

    def get_proc_description(self, module: str) -> VerProcDesc:
        return {
            "module": module,
            "name": self.name,
            "num_params": self._get_num_params(),
        }

    def call(
        self,
        args: list[JSONValues] | dict[str, JSONValues],
        context: Context,
    ) -> Result[JSONValues, VerLibErr]:

        pos_params = tuple(
            filter(
                lambda p: p.kind == Parameter.POSITIONAL_OR_KEYWORD,
                self._signature.parameters.values(),
            )
        )

        # A procedure requires the request context if
        # the last positional parameter is annotated with the Context type
        proc_requires_context = (
            len(pos_params) > 0 and pos_params[-1].annotation == Context
        )

        # Account for context when getting argument len
        args_len = len(args) + 1 if proc_requires_context else len(args)

        if args_len != len(pos_params):
            return Err(VerLibErr(ErrKind.INVALID_PARAMS, ErrMsg.INVALID_PARAMS))

        pargs: list[JSONValues | Context] = []
        pkwargs: dict[str, JSONValues | Context] = {}
        match args:
            case list(pos_params):
                pargs = cast(list[JSONValues | Context], pos_params)
                if proc_requires_context:
                    pargs.append(context)

            case dict(dict_params):
                pkwargs = cast(dict[str, JSONValues | Context], dict_params)
                if proc_requires_context:
                    ctx_param = pos_params[-1]
                    pkwargs[ctx_param.name] = context

        # TODO: Add type checking for parameters
        try:
            ba = self._signature.bind(*pargs, **pkwargs)
        except TypeError:
            return Err(VerLibErr(ErrKind.INVALID_PARAMS, ErrMsg.INVALID_PARAMS))

        # TODO: Decide on the best way to deal with exceptions
        return Ok(self._fn(*ba.args, **ba.kwargs))


@dataclass
class VerModule:
    name: str
    _procedures: dict[str, VerProcedure]
    default_access_level: AccessLevel

    def __init__(self, name: str, *, access_level=AccessLevel.public):
        self.name = name
        self._procedures = {}
        self.default_access_level = access_level

    def _register_proc(self, proc: VerProcedure):
        self._procedures[proc.name] = proc
        proc._fn._vermodule = self.name
        proc._fn._verproc_name = proc.name

    @property
    def module_description(self) -> VerLibDesc:
        return list(
            map(
                lambda p: p.get_proc_description(self.name),
                self._procedures.values(),
            )
        )

    def verproc(
        self,
        fn: VerProc[P, T] | None = None,
        *,
        name: str = "",
        access_level: AccessLevel | None = None,
    ) -> DecoratedVerProc[P, T]:
        def verproc_decorator(procedure: VerProc[P, T]) -> VerProc[P, T]:
            proc_name = name if name != "" else procedure.__name__
            if proc_name in self._procedures:
                raise TypeError(
                    f"A procedure with the name '{proc_name}' has already been registered to the module '{self.name}'"
                )

            self._register_proc(
                VerProcedure(
                    proc_name,
                    procedure,
                    inspect.signature(procedure),
                    access_level
                    if access_level is not None
                    else self.default_access_level,
                )
            )
            return procedure

        if fn is None:
            return verproc_decorator
        else:
            return verproc_decorator(fn)

    def access_level(
        self, fn: DecoratedVerProc[P, T], access_level: AccessLevel
    ) -> DecoratedVerProc[P, T]:

        # Verproc has not been registered
        if (
            getattr(fn, "_vermodule") is None
            or getattr(fn, "_verproc_name") is None
        ):
            raise TypeError(f"Function is not a VerProcedure.")
        # Verproc not registered to this module
        proc_name: str = fn._verproc_name
        if proc_name not in self._procedures:
            raise TypeError(
                f"Procedure '{proc_name}' is not registered to the module '{self.name}'"
            )

        self._procedures[proc_name].access_level = access_level
        return fn

    def public_access(
        self, fn: DecoratedVerProc[P, T]
    ) -> DecoratedVerProc[P, T]:
        return self.access_level(fn, access_level=AccessLevel.public)

    def private_access(
        self, fn: DecoratedVerProc[P, T]
    ) -> DecoratedVerProc[P, T]:
        return self.access_level(fn, access_level=AccessLevel.private)

    def _contains_proc(self, name: str) -> bool:
        return name in self._procedures

    def check_procedure_access(
        self, procedure: str, access_level: AccessLevel
    ) -> bool:

        if procedure not in self._procedures:
            return False
        return access_level.clears(self._procedures[procedure].access_level)

    def _call_procedure(
        self,
        proc_name: str,
        params: list[JSONValues] | dict[str, JSONValues],
        context: Context,
    ) -> Result[JSONValues, VerLibErr]:
        return self._procedures[proc_name].call(params, context)


@dataclass
class VerLib:
    name: str
    _modules: dict[str, VerModule]
    _context_builder: ContextBuilder | None
    _auth_provider: AuthProvider | None

    def __init__(self, name: str):
        self.name = name
        self._default_module: VerModule = VerModule("_default_")
        self._context_builder = None
        self._auth_provider = None
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
    ) -> DecoratedVerProc[P, T]:

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

    def import_lib(self) -> Response[VerLibDesc, None]:
        verlib_desc = self._default_module.module_description
        for module in self._modules.values():
            verlib_desc = [*verlib_desc, *module.module_description]

        return OkRes(None, verlib_desc)

    def context_builder(self, f: ContextBuilder) -> ContextBuilder:
        self._context_builder = f
        return f

    def access_level(
        self, fn: DecoratedVerProc[P, T], access_level: AccessLevel
    ) -> DecoratedVerProc[P, T]:
        return self._default_module.access_level(fn, access_level)

    def public_access(
        self, fn: DecoratedVerProc[P, T]
    ) -> DecoratedVerProc[P, T]:
        return self._default_module.public_access(fn)

    def private_access(
        self, fn: DecoratedVerProc[P, T]
    ) -> DecoratedVerProc[P, T]:
        return self._default_module.private_access(fn)

    def auth_provider(self, f: AuthProvider) -> AuthProvider:
        self._auth_provider = f
        return f

    def execute_rpc(
        self, req: Request, http_headers: HttpHeaders = _empty_headers
    ) -> Response[JSONValues, None]:
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

        context = (
            self._context_builder(http_headers, req)
            if self._context_builder
            else Context()
        )

        access_level = (
            self._auth_provider(http_headers, req, context)
            if self._auth_provider
            else AccessLevel.public
        )

        if not module.check_procedure_access(proc_name, access_level):
            return ErrRes(
                req.id,
                Error(
                    ErrKind.NOT_AUTHORIZED,
                    str(ErrMsg.NOT_AUTHORIZED),
                    None,
                ),
            )

        params = req.params if req.params != None else []

        result: Result[JSONValues, VerLibErr] = module._call_procedure(
            proc_name, params, context
        )

        ignore_result: bool = req.is_notification
        if result.is_ok():
            return OkRes(req.id, result.unwrap() if not ignore_result else None)

        return result.unwrap_err().into_json_rpc_err(req.id)
