"""Identidad estable para entidades del dominio."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(eq=False, kw_only=True, slots=True)
class Entity:
    """Entidad cuya identidad de dominio es siempre un UUID."""

    id: UUID = field(default_factory=uuid4)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Entity) and type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
