"""Errores de aplicación y manejadores HTTP centralizados."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Error esperado que puede traducirse a una respuesta HTTP estable."""

    def __init__(self, message: str, *, code: str = "application_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def _error_response(status_code: int, code: str, message: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": jsonable_encoder(message)}},
    )


def install_exception_handlers(application: FastAPI) -> None:
    """Registra respuestas uniformes para errores esperados e inesperados."""

    @application.exception_handler(AppError)
    async def handle_app_error(_request: Request, error: AppError) -> JSONResponse:
        return _error_response(error.status_code, error.code, error.message)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return _error_response(422, "validation_error", error.errors())

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        return _error_response(error.status_code, f"http_{error.status_code}", error.detail)

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "Error no controlado en %s %s",
            request.method,
            request.url.path,
            exc_info=(type(error), error, error.__traceback__),
        )
        return _error_response(500, "internal_error", "Internal server error")
