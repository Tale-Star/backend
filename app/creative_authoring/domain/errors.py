"""Errores de reglas de CreativeAuthoring."""


class CreativeResourceNotFound(Exception):
    """El recurso no existe o no pertenece al usuario autenticado."""


class DuplicatePageNumber(Exception):
    """Una historia no puede tener dos páginas con el mismo número."""
