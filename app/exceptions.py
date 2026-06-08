from fastapi import Request
from fastapi.responses import JSONResponse
import uuid


class GoTaxiException(Exception):
    code: str = "INTERNAL_ERROR"
    message: str = "Erreur interne"
    status_code: int = 400

    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


class UserNotFoundException(GoTaxiException):
    code = "USER_NOT_FOUND"
    message = "Utilisateur introuvable"
    status_code = 404


class InvalidOTPException(GoTaxiException):
    code = "INVALID_OTP"
    message = "Code OTP invalide ou expiré"
    status_code = 400


class OTPMaxAttemptsException(GoTaxiException):
    code = "OTP_MAX_ATTEMPTS"
    message = "Trop de tentatives OTP, compte bloqué 30 min"
    status_code = 429


class InsufficientFundsException(GoTaxiException):
    code = "INSUFFICIENT_FUNDS"
    message = "Solde wallet insuffisant"
    status_code = 402


class VoyageFullException(GoTaxiException):
    code = "VOYAGE_FULL"
    message = "Plus de places disponibles sur ce voyage"
    status_code = 409


class VoyageNotFoundException(GoTaxiException):
    code = "VOYAGE_NOT_FOUND"
    message = "Voyage introuvable"
    status_code = 404


class ColisNotFoundException(GoTaxiException):
    code = "COLIS_NOT_FOUND"
    message = "Colis introuvable"
    status_code = 404


class PermissionDeniedException(GoTaxiException):
    code = "PERMISSION_DENIED"
    message = "Permission refusée"
    status_code = 403


class KYCNotValidatedException(GoTaxiException):
    code = "KYC_NOT_VALIDATED"
    message = "KYC non validé, veuillez contacter le support"
    status_code = 403


class InvalidCredentialsException(GoTaxiException):
    code = "INVALID_CREDENTIALS"
    message = "Identifiants invalides"
    status_code = 401


class AccountSuspendedException(GoTaxiException):
    code = "ACCOUNT_SUSPENDED"
    message = "Compte suspendu"
    status_code = 403


class PhoneAlreadyExistsException(GoTaxiException):
    code = "PHONE_ALREADY_EXISTS"
    message = "Ce numéro de téléphone est déjà enregistré"
    status_code = 409


class TokenInvalidException(GoTaxiException):
    code = "TOKEN_INVALID"
    message = "Token invalide ou révoqué"
    status_code = 401


async def gotaxi_exception_handler(request: Request, exc: GoTaxiException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": str(uuid.uuid4()),
            }
        },
    )