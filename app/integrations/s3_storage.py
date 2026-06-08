import io
from uuid import uuid4
from pathlib import Path
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_s3 = None
_LOCAL_MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"


def _use_local() -> bool:
    return not settings.AWS_ACCESS_KEY_ID


def _get_s3():
    global _s3
    if _s3 is None:
        try:
            import boto3
        except ImportError:
            raise RuntimeError("boto3 n'est pas installé. Lancez: pip install boto3")
        _s3 = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return _s3


def _local_upload(file_data: bytes, folder: str, filename: str | None, content_type: str) -> str:
    ext = Path(filename).suffix if filename else ""
    relative = f"{folder}/{uuid4()}{ext}"
    dest = _LOCAL_MEDIA_DIR / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_data)
    logger.info("local_upload", path=str(dest), size=len(file_data))
    return f"/media/{relative}"


def upload_file(
    file_data: bytes,
    folder: str,
    filename: str | None = None,
    content_type: str = "application/octet-stream",
) -> str:
    if _use_local():
        return _local_upload(file_data, folder, filename, content_type)

    try:
        from botocore.exceptions import ClientError
    except ImportError:
        raise RuntimeError("boto3 n'est pas installé. Lancez: pip install boto3")

    ext = Path(filename).suffix if filename else ""
    key = f"{folder}/{uuid4()}{ext}"
    try:
        _get_s3().upload_fileobj(
            io.BytesIO(file_data),
            settings.AWS_S3_BUCKET,
            key,
            ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
        )
        url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        logger.info("s3_upload", key=key, size=len(file_data))
        return url
    except ClientError as e:
        logger.error("s3_upload_failed", key=key, error=str(e))
        raise


def delete_file(url: str) -> None:
    if url.startswith("/media/"):
        path = _LOCAL_MEDIA_DIR / url[len("/media/"):]
        if path.exists():
            path.unlink()
        return

    try:
        from botocore.exceptions import ClientError
    except ImportError:
        return

    prefix = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/"
    if not url.startswith(prefix):
        return
    key = url[len(prefix):]
    try:
        _get_s3().delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        logger.info("s3_delete", key=key)
    except ClientError as e:
        logger.error("s3_delete_failed", key=key, error=str(e))


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    return _get_s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )