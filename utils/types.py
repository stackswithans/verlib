from typing import Protocol, TypeVar, Generic, cast, NoReturn
from dataclasses import dataclass

T = TypeVar("T")
E = TypeVar("E")


class Result(Generic[T, E]):
    _val: T | E

    def is_ok(self) -> bool:
        ...

    def is_err(self) -> bool:
        ...

    def unwrap(self) -> T:
        ...

    def unwrap_err(self) -> E:
        ...


@dataclass
class Ok(Result[T, NoReturn]):
    _val: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self._val

    def unwrap_err(self) -> NoReturn:
        raise TypeError("Result wraps an Ok!")


@dataclass
class Err(Result[NoReturn, E]):
    _val: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> NoReturn:
        raise TypeError("Result wraps an Err!")

    def unwrap_err(self) -> E:
        return self._val
