"""Errores del dominio IdentityAccess."""


class IdentityError(Exception):
    """Error base para fallos esperados de identidad."""


class EmailAlreadyRegistered(IdentityError):
    """El correo ya corresponde a una cuenta."""


class InvalidCredentials(IdentityError):
    """El correo o la contraseña no son válidos."""
