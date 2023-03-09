from __future__ import annotations
from typing_extensions import Self
from dataclasses import dataclass, field


@dataclass
class AccessLevel:

    id: int | str
    _or_levels: list[AccessLevel] = field(default_factory=list)

    def __or__(self, other: Self) -> Self:
        self._or_levels.append(other)
        return self

    def clears(self, other: Self) -> bool:
        if self.id == other.id:
            return True
        # Check if other levels match
        return any(map(lambda a: a.id == self.id, other._or_levels))

    @classmethod
    def public(cls) -> Self:
        return cls("public")

    @classmethod
    def private(cls) -> Self:
        return cls.public() | cls("private")
