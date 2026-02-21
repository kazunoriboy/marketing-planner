"""
施設画像の保存・圧縮ヘルパー

1MB を超える画像はサーバ側でリサイズ・圧縮してから S3 に保存する。
"""
import uuid
from io import BytesIO

from app.core.config import settings
from app.core.s3_client import get_s3_client

# 1MB
FACILITY_IMAGE_MAX_BYTES = 1048576

# 圧縮時の長辺最大ピクセル
FACILITY_IMAGE_MAX_SIDE = 1920

# WebP 圧縮品質
WEBP_QUALITY = 85


def _image_to_webp(img: "Image.Image", quality: int = WEBP_QUALITY) -> bytes:
    """PIL Image を WebP バイト列に変換する。透過は RGBA で保存する。"""
    out = BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
        img.save(out, "WEBP", quality=quality, method=6)
    else:
        img = img.convert("RGB")
        img.save(out, "WEBP", quality=quality, method=6)
    return out.getvalue()


def compress_image(content: bytes, ext: str) -> bytes:
    """
    画像をリサイズ・圧縮し、WebP バイト列で返す。
    長辺を FACILITY_IMAGE_MAX_SIDE 以下にする。透過は RGBA のまま WebP で保存する。
    """
    try:
        from PIL import Image
    except ImportError:
        return content

    try:
        img = Image.open(BytesIO(content))
    except Exception:
        return content

    w, h = img.size
    if w > FACILITY_IMAGE_MAX_SIDE or h > FACILITY_IMAGE_MAX_SIDE:
        if w >= h:
            new_w = FACILITY_IMAGE_MAX_SIDE
            new_h = int(h * (FACILITY_IMAGE_MAX_SIDE / w))
        else:
            new_h = FACILITY_IMAGE_MAX_SIDE
            new_w = int(w * (FACILITY_IMAGE_MAX_SIDE / h))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return _image_to_webp(img)


def _convert_to_webp(content: bytes, ext: str) -> bytes:
    """画像バイト列を WebP に変換する（リサイズなし）。"""
    try:
        from PIL import Image
    except ImportError:
        return content
    try:
        img = Image.open(BytesIO(content))
        return _image_to_webp(img)
    except Exception:
        return content


def save_facility_image(hotel_id: int, content: bytes, ext: str) -> tuple[str, str]:
    """
    施設画像を WebP 形式で S3 に保存し、(key, url) を返す。

    - 1MB 超過時はリサイズ・圧縮してから WebP で保存する。
    - 1MB 以下も WebP に変換して保存する。
    - ext は ".jpg" などドット付きで渡す（読み込み時の形式）。保存形式は常に .webp。
    - key: 一意キー（削除時に使用）
    - url: 配信用 URL（例: /static/hotel_images/5/abc123.webp）
    """
    if len(content) > FACILITY_IMAGE_MAX_BYTES:
        content = compress_image(content, ext)
    else:
        content = _convert_to_webp(content, ext)

    key = uuid.uuid4().hex[:12]
    filename = f"{key}.webp"
    s3_key = f"hotel_images/{hotel_id}/{filename}"

    client = get_s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=s3_key,
        Body=content,
        ContentType="image/webp",
    )

    url = f"/static/hotel_images/{hotel_id}/{filename}"
    return (key, url)


def delete_facility_image_file(hotel_id: int, key: str, url: str) -> None:
    """
    施設画像を S3 から削除する。
    url からファイル名を抽出して削除する。存在しない場合は何もしない。
    """
    if not url or "/static/hotel_images/" not in url:
        return
    filename = url.split("/")[-1]
    if not filename or not filename.startswith(key):
        return
    s3_key = f"hotel_images/{hotel_id}/{filename}"
    client = get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
