import pytest
from verlib.verlib import VerLib, VerModule, HttpHeaders, Context
from verlib.verliberr import ErrKind
from verlib.auth import AccessLevel
from verlib.jsonrpc import Request, Error, ErrorCode
from typing import cast, Any


@pytest.fixture
def auth_key() -> str:
    return "baz"


@pytest.fixture
def verlib(auth_key: str) -> VerLib:
    verlib = VerLib("test_lib")

    @verlib.context_builder
    def context_builder(headers: HttpHeaders, req: Request) -> Context:
        context = Context()
        context.is_authenticated = headers.get("X-API-KEY") == auth_key
        context.header_msg = headers.get("X-HEADER-MSG")
        return context

    @verlib.auth_provider
    def auth_provider(
        headers: HttpHeaders, req: Request, context: Context
    ) -> AccessLevel:
        return (
            AccessLevel.private
            if context.is_authenticated
            else AccessLevel.public
        )

    return verlib


@pytest.fixture
def vermodule() -> VerModule:
    return VerModule("test_module")


@pytest.fixture
def test_module(vermodule: VerModule) -> VerModule:
    @vermodule.verproc
    def foo():
        return 1

    @vermodule.verproc
    def add(a: int, b: int) -> int:
        return a + b

    @vermodule.verproc
    def returns_list(a: int, b: int) -> list[int]:
        return []

    @vermodule.verproc
    def returns_dict(a: int, b: int) -> dict[str, float]:
        return dict({})

    @vermodule.private_access
    @vermodule.verproc
    def protected_proc() -> int:
        return 0

    return vermodule


@pytest.fixture
def ctx_module(vermodule: VerModule) -> VerModule:
    @vermodule.private_access
    @vermodule.verproc
    def echo(msg: str, ctx: Context) -> str:
        return f"{ctx.header_msg} {msg}"

    @vermodule.verproc
    def echo_2(ctx: Context) -> str:
        return f"{ctx.header_msg}"

    @vermodule.verproc
    def bad_echo(ctx: Context, msg: str) -> str:
        return f"{ctx.header_msg} {msg}"

    @vermodule.verproc
    def bad_echo_2(ctx) -> str:  # type:ignore
        return f"{ctx.header_msg}"

    return vermodule


@pytest.fixture
def test_lib(verlib: VerLib, test_module: VerModule) -> VerLib:
    @verlib.verproc
    def foo():
        return 1

    verlib.declare_module(test_module)

    return verlib


@pytest.fixture
def ctx_lib(verlib: VerLib, ctx_module: VerModule) -> VerLib:
    verlib.declare_module(ctx_module)
    return verlib


@pytest.fixture
def dummy_req() -> Request:
    return Request(id=1, method="foo")


def test_verlib_created_normally(verlib: VerLib):
    assert verlib.name == "test_lib"
    assert verlib._default_module is not None
    assert verlib._default_module.name == "_default_"


def test_verlib_declare_module_works(
    verlib: VerLib,
    vermodule: VerModule,
):
    verlib.declare_module(vermodule)
    assert verlib._modules.get("test_module")


def test_verlib_declare_module_fails_when_module_already_exists(
    verlib: VerLib,
    vermodule: VerModule,
):
    verlib.declare_module(vermodule)
    assert verlib._modules.get("test_module")

    with pytest.raises(
        TypeError,
        match="A module with the name 'test_module' has already been declared",
    ):
        verlib.declare_module(vermodule)


def test_verlib_verproc(
    verlib: VerLib,
):
    @verlib.verproc
    def test_proc() -> int:
        return 1

    proc = verlib._default_module._procedures.get("test_proc")
    assert proc is not None


def test_verlib_verproc_rename(
    verlib: VerLib,
):
    @verlib.verproc(name="test_proc_1")
    def test_proc() -> int:
        return 1

    assert "test_proc" not in verlib._default_module._procedures

    proc = verlib._default_module._procedures.get("test_proc_1")
    assert proc is not None


def test_verlib_verproc_error_on_redeclare(
    verlib: VerLib,
):
    @verlib.verproc
    def test_proc_1() -> int:
        return 1

    with pytest.raises(
        TypeError,
        match=f"A procedure with the name 'test_proc_1' has already been registered to the module '_default_'",
    ):

        @verlib.verproc(name="test_proc_1")
        def test_proc() -> int:
            return 1


def test_verlib_import(test_lib: VerLib):
    res = test_lib.import_lib()
    assert res.is_success()
    result_data = res.result_data()
    assert isinstance(result_data, list)
    assert len(result_data) == 6
    assert all(
        map(
            lambda p: "name" in p
            and "num_params" in p
            and p["module"] in ("_default_", "test_module"),
            result_data,
        )
    )


def test_vermodule_created_normally(vermodule: VerModule):
    assert vermodule.name == "test_module"


def test_vermodule_verproc(
    vermodule: VerModule,
):
    @vermodule.verproc
    def test_proc() -> int:
        return 1

    assert vermodule._contains_proc("test_proc")

    proc = vermodule._procedures.get("test_proc")
    assert proc is not None


def test_vermodule_verproc_rename(
    vermodule: VerModule,
):
    @vermodule.verproc(name="test_proc_1")
    def test_proc() -> int:
        return 1

    assert vermodule._contains_proc("test_proc_1")

    assert "test_proc" not in vermodule._procedures
    proc = vermodule._procedures.get("test_proc_1")
    assert proc is not None


def test_vermodule_verproc_error_on_redeclare(
    vermodule: VerModule,
):
    @vermodule.verproc
    def test_proc_1() -> int:
        return 1

    with pytest.raises(
        TypeError,
        match=f"A procedure with the name 'test_proc_1' has already been registered to the module 'test_module'",
    ):

        @vermodule.verproc(name="test_proc_1")
        def test_proc() -> int:
            return 1


def test_vermodule_contains_proc(vermodule: VerModule):
    assert vermodule._contains_proc("foo") == False

    @vermodule.verproc
    def foo():
        return 1

    assert vermodule._contains_proc("foo")


def test_verlib_execute_rpc(test_lib: VerLib, dummy_req: Request):
    res = test_lib.execute_rpc(dummy_req)
    assert res.is_success()
    assert res.id == 1
    assert res.jsonrpc == "2.0"
    assert res.result_data() == 1


def test_verlib_module_proc_call(test_lib: VerLib):
    res = test_lib.execute_rpc(Request(method="test_module.foo", id=1))
    assert res.is_success()
    assert res.result_data() == 1

    res = test_lib.execute_rpc(
        Request(method="test_module.add", id=1, params=[2, 2])
    )
    assert res.is_success()
    assert res.result_data() == 4


def test_verlib_module_proc_call_with_invalid_params(test_lib: VerLib):
    res = test_lib.execute_rpc(Request(method="test_module.add", id=1))
    assert res.is_err()
    err: Error[None] = cast(Error, res.err_data())
    assert err.code == -32602
    assert err.message == "Invalid method parameter(s)."


def test_verlib_err_on_non_existing_method(test_lib: VerLib):
    res = test_lib.execute_rpc(Request(method="baz", id=1))
    assert res.is_err()
    err: Error[None] = cast(Error, res.err_data())
    assert err.code == -32601
    assert err.message == "The procedure 'baz' was not found on the server."


def test_verlib_proc_call_notification(test_lib: VerLib):
    res = test_lib.execute_rpc(Request(method="foo"))
    assert res.is_success()
    assert res.result_data() is None


def test_verlib_module_proc_call_propagates_error(test_lib: VerLib):
    with pytest.raises(TypeError):
        test_lib.execute_rpc(
            Request(method="test_module.add", id=1, params=[None, None])
        )


def test_verlib_module_allows_unauthenticated_request(test_lib: VerLib):
    res = test_lib.execute_rpc(Request(method="test_module.foo", id=1))
    assert res.is_success()
    assert res.result_data() == 1


def test_verlib_module_disallows_call_to_method_without_correct_access_level(
    test_lib: VerLib,
):
    res = test_lib.execute_rpc(
        Request(method="test_module.protected_proc", id=1)
    )
    assert res.is_err()
    err: Error[None] = cast(Error, res.err_data())
    assert err.code == -32501
    assert err.message == "Insufficient privileges to invoke procedure."


def test_verlib_module_allows_call_to_method_auth(
    test_lib: VerLib, auth_key: str
):
    res = test_lib.execute_rpc(
        Request(method="test_module.protected_proc", id=1),
        http_headers={"X-API-KEY": auth_key},
    )
    assert res.is_success()
    assert res.result_data() == 0


def test_verlib_module_proc_context_works(ctx_lib: VerLib, auth_key: str):
    res = ctx_lib.execute_rpc(
        Request(method="test_module.echo", id=1, params=["World!"]),
        http_headers={"X-API-KEY": auth_key, "X-HEADER-MSG": "Hello"},
    )
    assert res.is_success()
    assert res.result_data() == "Hello World!"


def test_verlib_module_proc_context_works_only_argument(
    ctx_lib: VerLib, auth_key: str
):
    res = ctx_lib.execute_rpc(
        Request(method="test_module.echo_2", id=1),
        http_headers={"X-API-KEY": auth_key, "X-HEADER-MSG": "Hello World!"},
    )
    assert res.is_success()
    assert res.result_data() == "Hello World!"


def test_verlib_module_proc_context_fails_if_not_last_arg(ctx_lib: VerLib):
    res = ctx_lib.execute_rpc(
        Request(method="test_module.bad_echo", id=1, params=["World!"]),
        http_headers={"X-HEADER-MSG": "Hello"},
    )
    assert res.is_err()
    err: Error[None] = cast(Error, res.err_data())
    assert err.code == ErrorCode.INVALID_PARAMS


def test_verlib_module_proc_context_fails_if_not_annotated(ctx_lib: VerLib):
    res = ctx_lib.execute_rpc(
        Request(method="test_module.bad_echo_2", id=1),
        http_headers={"X-HEADER-MSG": "Hello"},
    )
    assert res.is_err()
    err: Error[None] = cast(Error, res.err_data())
    assert err.code == ErrorCode.INVALID_PARAMS
