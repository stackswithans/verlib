from __future__ import annotations
from typing_extensions import Self
from dataclasses import dataclass, field
from typing import ClassVar, Iterable


@dataclass
class AccessLevel:
    public: ClassVar[AccessLevel]
    private: ClassVar[AccessLevel]

    def __init__(self, acls_id: Iterable[int] | None = None):
        self._acls_ids: set[int] = set(acls_id) if acls_id else set((id(self),))

    def __or__(self, other: Self) -> Self:
        return AccessLevel(self._acls_ids.union(other._acls_ids))

    def clears(self, other: Self) -> bool:
        return self._acls_ids.issuperset(other._acls_ids)


AccessLevel.public = AccessLevel()
AccessLevel.private = AccessLevel.public | AccessLevel()
