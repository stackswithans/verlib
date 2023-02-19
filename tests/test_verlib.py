import pytest
from src.verlib import VerLib, VerModule


@pytest.fixture
def verlib() -> VerLib:
    return VerLib("test_lib")


@pytest.fixture
def vermodule() -> VerModule:
    return VerModule("test_module")


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


def test_vermodule_created_normally(vermodule: VerModule):
    assert vermodule.name == "test_module"


def test_vermodule_verproc(
    vermodule: VerModule,
):
    @vermodule.verproc
    def test_proc() -> int:
        return 1

    assert vermodule.contains_proc("test_proc")

    proc = vermodule._procedures.get("test_proc")
    assert proc is not None


def test_vermodule_verproc_rename(
    vermodule: VerModule,
):
    @vermodule.verproc(name="test_proc_1")
    def test_proc() -> int:
        return 1

    assert vermodule.contains_proc("test_proc_1")

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
    assert vermodule.contains_proc("foo") == False

    @vermodule.verproc
    def foo():
        return 1

    assert vermodule.contains_proc("foo")
