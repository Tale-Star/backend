"""Rutas de sesión y controles parentales MVP."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.identity_access.application.service import IdentityAccessService
from app.identity_access.domain.errors import EmailAlreadyRegistered, InvalidCredentials
from app.identity_access.domain.user import User
from app.identity_access.interfaces.dependencies import (
    get_current_user,
    get_identity_access_service,
)
from app.identity_access.interfaces.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    SetParentalPinRequest,
    UserResponse,
    ValidateParentalPinRequest,
    ValidateParentalPinResponse,
)
from app.shared.errors import AppError, ErrorResponse

router = APIRouter(
    prefix="/auth",
    tags=["identity-access"],
    responses={
        422: {"model": ErrorResponse, "description": "Request validation failed."},
    },
)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse, "description": "Account already exists."}},
)
def register(
    request: RegisterRequest,
    service: Annotated[IdentityAccessService, Depends(get_identity_access_service)],
) -> AuthResponse:
    try:
        user, token = service.register(
            str(request.email), request.display_name, request.password, request.parental_pin
        )
    except EmailAlreadyRegistered as error:
        raise AppError(
            "An account with this email already exists",
            code="email_already_registered",
            status_code=409,
        ) from error
    return AuthResponse(access_token=token, user=_user_response(user))


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse, "description": "Invalid credentials."}},
)
def login(
    request: LoginRequest,
    service: Annotated[IdentityAccessService, Depends(get_identity_access_service)],
) -> AuthResponse:
    try:
        user, token = service.login(str(request.email), request.password)
    except InvalidCredentials as error:
        raise AppError(
            "Email or password is incorrect", code="invalid_credentials", status_code=401
        ) from error
    return AuthResponse(access_token=token, user=_user_response(user))


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse, "description": "Authentication required."}},
)
def profile(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return _user_response(user)


@router.put(
    "/parental-pin",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse, "description": "Invalid password or access token."}},
)
def set_parental_pin(
    request: SetParentalPinRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[IdentityAccessService, Depends(get_identity_access_service)],
) -> UserResponse:
    try:
        updated = service.set_parental_pin(user.id, request.current_password, request.pin)
    except InvalidCredentials as error:
        raise AppError(
            "Email or password is incorrect", code="invalid_credentials", status_code=401
        ) from error
    return _user_response(updated)


@router.post(
    "/parental-pin/validate",
    response_model=ValidateParentalPinResponse,
    responses={401: {"model": ErrorResponse, "description": "Authentication required."}},
)
def validate_parental_pin(
    request: ValidateParentalPinRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[IdentityAccessService, Depends(get_identity_access_service)],
) -> ValidateParentalPinResponse:
    return ValidateParentalPinResponse(valid=service.validate_parental_pin(user.id, request.pin))


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        pin_configured=user.parental_pin_hash is not None,
        created_at=user.created_at,
    )
