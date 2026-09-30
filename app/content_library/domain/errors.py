"""Errores de dominio de ContentLibrary."""


class LibraryResourceNotFound(Exception):
    """La referencia no existe o no pertenece al usuario."""


class LibraryItemAlreadySaved(Exception):
    """El usuario ya guardó esta referencia en su biblioteca."""
