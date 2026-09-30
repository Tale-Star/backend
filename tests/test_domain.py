"""Pruebas de identidad de entidades de dominio."""

from uuid import UUID

from app.shared.domain.entity import Entity


class ExampleEntity(Entity):
    """Entidad mínima usada para comprobar la identidad por UUID."""


class OtherEntity(Entity):
    """Tipo distinto para comprobar la igualdad entre entidades."""


def test_entity_ids_are_uuids_and_identity_is_type_scoped() -> None:
    entity = ExampleEntity()
    same_identity = ExampleEntity(id=entity.id)
    other_type = OtherEntity(id=entity.id)

    assert isinstance(entity.id, UUID)
    assert entity == same_identity
    assert hash(entity) == hash(same_identity)
    assert entity != other_type

