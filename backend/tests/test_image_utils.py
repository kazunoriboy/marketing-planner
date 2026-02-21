"""
施設画像ヘルパー（image_utils）の単体テスト
"""
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

try:
    from PIL import Image  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from app.core.image_utils import (
    save_facility_image,
    delete_facility_image_file,
    compress_image,
    FACILITY_IMAGE_MAX_SIDE,
)


class TestSaveFacilityImage:
    """save_facility_image のテスト（S3 に保存）"""

    @pytest.mark.skipif(not HAS_PIL, reason="PIL not installed")
    def test_save_facility_image_returns_key_and_url(self):
        """保存成功で (key, url) が返り、put_object が呼ばれることを検証"""
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="red")
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
        content = buf.getvalue()

        mock_client = MagicMock()
        with patch("app.core.image_utils.get_s3_client", return_value=mock_client), patch(
            "app.core.image_utils.settings"
        ) as mock_settings:
            mock_settings.S3_BUCKET = "facility-images"
            key, url = save_facility_image(1, content, ".jpg")

        assert isinstance(key, str)
        assert len(key) == 12
        assert url == f"/static/hotel_images/1/{key}.webp"
        mock_client.put_object.assert_called_once()
        call_kw = mock_client.put_object.call_args.kwargs
        assert call_kw["Bucket"] == "facility-images"
        assert call_kw["Key"] == f"hotel_images/1/{key}.webp"
        assert call_kw["ContentType"] == "image/webp"
        body = call_kw["Body"]
        assert body.startswith(b"RIFF") and b"WEBP" in body[:20]

    @pytest.mark.skipif(not HAS_PIL, reason="PIL not installed")
    def test_save_facility_image_raises_on_s3_error(self):
        """S3 put_object が失敗した場合に例外が伝播することを検証"""
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="red")
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
        content = buf.getvalue()

        mock_client = MagicMock()
        mock_client.put_object.side_effect = Exception("connection failed")
        with patch("app.core.image_utils.get_s3_client", return_value=mock_client):
            with pytest.raises(Exception, match="connection failed"):
                save_facility_image(1, content, ".jpg")


class TestDeleteFacilityImageFile:
    """delete_facility_image_file のテスト（S3 から削除）"""

    def test_delete_calls_s3_delete_object(self):
        """正しい url の場合、delete_object が呼ばれることを検証"""
        key = "abc123"
        filename = f"{key}.webp"
        url = f"/static/hotel_images/1/{filename}"
        mock_client = MagicMock()
        with patch("app.core.image_utils.get_s3_client", return_value=mock_client), patch(
            "app.core.image_utils.settings"
        ) as mock_settings:
            mock_settings.S3_BUCKET = "facility-images"
            delete_facility_image_file(1, key, url)
        mock_client.delete_object.assert_called_once_with(
            Bucket="facility-images",
            Key=f"hotel_images/1/{filename}",
        )

    def test_delete_ignores_invalid_url(self):
        """url が /static/hotel_images/ を含まない場合は delete_object を呼ばない"""
        mock_client = MagicMock()
        with patch("app.core.image_utils.get_s3_client", return_value=mock_client):
            delete_facility_image_file(1, "abc123", "/other/path/image.webp")
        mock_client.delete_object.assert_not_called()

    def test_delete_ignores_empty_url(self):
        """url が空の場合は何もしない"""
        mock_client = MagicMock()
        with patch("app.core.image_utils.get_s3_client", return_value=mock_client):
            delete_facility_image_file(1, "abc", "")
            delete_facility_image_file(1, "abc", None)  # type: ignore
        mock_client.delete_object.assert_not_called()


class TestCompressImage:
    """compress_image のテスト（PIL がある場合のみ）"""

    @pytest.mark.skipif(not HAS_PIL, reason="PIL not installed")
    def test_compress_resizes_large_image(self):
        """長辺が FACILITY_IMAGE_MAX_SIDE を超える画像はリサイズされ、WebP で返る"""
        from PIL import Image

        img = Image.new("RGB", (2000, 1000), color="red")
        buf = BytesIO()
        img.save(buf, "JPEG", quality=90)
        content = buf.getvalue()
        result = compress_image(content, ".jpg")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b"RIFF") and b"WEBP" in result[:20]
        out_img = Image.open(BytesIO(result))
        w, h = out_img.size
        assert max(w, h) <= FACILITY_IMAGE_MAX_SIDE
