import pytest
from src.verlib import VerLib, VerModule


@pytest.fixture
def verlib() -> VerLib:
    return VerLib("test_module")


@pytest.fixture
def vermodule() -> VerModule:
    return VerModule("test_module")


def test_verlib_created_normally(verlib: VerLib):
    assert verlib.name == "test_module"
    assert verlib._ver_module is not None
    assert verlib._ver_module.name == "main"


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
        match="A module with the name 'test_module' has already be registered to the library instance",
    ):
        verlib.declare_module(vermodule)
