"""
S3互換ストレージ（施設画像保存）用クライアント
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_s3_client():
    """設定から boto3 S3 クライアントを取得する（シングルトン）。"""
    global _client
    if _client is None:
        if not settings.S3_ENDPOINT_URL or not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
            raise RuntimeError(
                "S3 is not configured. Set S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY in .env"
            )
        import boto3
        from botocore.config import Config

        _client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _client


def ensure_bucket() -> None:
    """バケットが存在しなければ作成する。接続失敗時は例外を投げる。"""
    client = get_s3_client()
    bucket = settings.S3_BUCKET
    try:
        client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            try:
                client.create_bucket(Bucket=bucket)
                logger.info("S3 bucket created: %s", bucket)
            except Exception as create_err:
                logger.exception("Failed to create bucket %s: %s", bucket, create_err)
                raise
        else:
            raise
