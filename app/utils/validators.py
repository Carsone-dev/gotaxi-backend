import re


PHONE_PATTERN = re.compile(r"^\+229\d{10}$|^\+228\d{8}$")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def is_valid_phone(telephone: str) -> bool:
    return bool(PHONE_PATTERN.match(telephone))


def validate_image(content_type: str, size: int) -> None:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Type d'image non supporté : {content_type}. Utilisez JPEG, PNG ou WebP.")
    if size > MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image trop lourde ({size // 1024} Ko). Maximum 5 Mo.")