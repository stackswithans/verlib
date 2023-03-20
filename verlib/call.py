from typing import Callable, Any
from types import SimpleNamespace
from verlib.jsonrpc import Request
from verlib.auth import AccessLevel


class HttpHeaders(dict[str, Any]):
    def __init__(self, initial_data: dict[str, Any]):
        super().__init__(
            map(
                lambda item: (item[0].casefold(), item[1]), initial_data.items()
            )
        )

    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(key.casefold())

    def __contains__(self, key: str) -> bool:
        return super().__contains__(key.casefold())

    def get(self, key: str) -> str | None:
        return super().get(key.casefold())


Context = SimpleNamespace
ContextBuilder = Callable[[HttpHeaders, Request], Context]
AuthProvider = Callable[[HttpHeaders, Request, Context], AccessLevel]
