import pytest
from verlib.verlib import VerLib, VerModule
from verlib.verliberr import ErrKind
from verlib.jsonrpc import Request, Error
from typing import cast


@pytest.fixture
def verlib() -> VerLib:
    return VerLib("test_lib")


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

    return vermodule


@pytest.fixture
def test_lib(verlib: VerLib, test_module: VerModule) -> VerLib:
    @verlib.verproc
    def foo():
        return 1

    verlib.declare_module(test_module)

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
    assert len(result_data) == 5
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
