"""
施設画像の保存・圧縮ヘルパー

1MB を超える画像はサーバ側でリサイズ・圧縮してから保存する。
"""
import os
import uuid
from io import BytesIO

# 1MB
FACILITY_IMAGE_MAX_BYTES = 1048576

# 圧縮時の長辺最大ピクセル
FACILITY_IMAGE_MAX_SIDE = 1920

# JPEG 圧縮品質
JPEG_QUALITY = 85


def _get_static_dir() -> str:
    """backend/static の絶対パスを返す"""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "static",
    )


def compress_image(content: bytes, ext: str) -> bytes:
    """
    画像をリサイズ・圧縮する。
    長辺を FACILITY_IMAGE_MAX_SIDE 以下にし、JPEG 品質 85 で保存する。
    """
    try:
        from PIL import Image
    except ImportError:
        return content

    try:
        img = Image.open(BytesIO(content)).convert("RGB")
    except Exception:
        return content

    w, h = img.size
    if w <= FACILITY_IMAGE_MAX_SIDE and h <= FACILITY_IMAGE_MAX_SIDE:
        out = BytesIO()
        img.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return out.getvalue()

    if w >= h:
        new_w = FACILITY_IMAGE_MAX_SIDE
        new_h = int(h * (FACILITY_IMAGE_MAX_SIDE / w))
    else:
        new_h = FACILITY_IMAGE_MAX_SIDE
        new_w = int(w * (FACILITY_IMAGE_MAX_SIDE / h))

    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


def save_facility_image(hotel_id: int, content: bytes, ext: str) -> tuple[str, str]:
    """
    施設画像を保存し、(key, url) を返す。

    - 1MB 超過時は圧縮してから保存する。
    - ext は ".jpg" などドット付きで渡す。圧縮時は .jpg で保存する。
    - key: 一意キー（削除時に使用）
    - url: 配信用 URL（例: /static/hotel_images/5/abc123.jpg）
    """
    if len(content) > FACILITY_IMAGE_MAX_BYTES:
        content = compress_image(content, ext)
        ext = ".jpg"

    key = uuid.uuid4().hex[:12]
    filename = f"{key}{ext}"
    static_dir = _get_static_dir()
    hotel_dir = os.path.join(static_dir, "hotel_images", str(hotel_id))
    os.makedirs(hotel_dir, exist_ok=True)
    filepath = os.path.join(hotel_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/static/hotel_images/{hotel_id}/{filename}"
    return (key, url)


def delete_facility_image_file(hotel_id: int, key: str, url: str) -> None:
    """
    施設画像の実ファイルを削除する。
    url からファイル名を抽出して削除する。存在しない場合は何もしない。
    """
    if not url or "/static/hotel_images/" not in url:
        return
    filename = url.split("/")[-1]
    if not filename or not filename.startswith(key):
        return
    static_dir = _get_static_dir()
    filepath = os.path.join(static_dir, "hotel_images", str(hotel_id), filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass
