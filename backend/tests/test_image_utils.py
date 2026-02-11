"""
施設画像ヘルパー（image_utils）の単体テスト
"""

import os
import tempfile
from unittest.mock import patch

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
    """save_facility_image のテスト"""

    def test_save_facility_image_returns_key_and_url(self):
        """保存成功で (key, url) が返り、ファイルが存在することを検証"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.core.image_utils._get_static_dir", return_value=tmpdir):
                # 最小限の JPEG 風バイト列（1バイトでも ext が .jpg なら保存される）
                content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
                key, url = save_facility_image(1, content, ".jpg")
                assert isinstance(key, str)
                assert len(key) == 12
                assert url == f"/static/hotel_images/1/{key}.jpg"
                hotel_dir = os.path.join(tmpdir, "hotel_images", "1")
                assert os.path.isdir(hotel_dir)
                filepath = os.path.join(hotel_dir, f"{key}.jpg")
                assert os.path.isfile(filepath)
                with open(filepath, "rb") as f:
                    assert f.read() == content


class TestDeleteFacilityImageFile:
    """delete_facility_image_file のテスト"""

    def test_delete_removes_file(self):
        """正しい url の場合、ファイルが削除されることを検証"""
        with tempfile.TemporaryDirectory() as tmpdir:
            hotel_dir = os.path.join(tmpdir, "hotel_images", "1")
            os.makedirs(hotel_dir, exist_ok=True)
            key = "abc123"
            filename = f"{key}.jpg"
            filepath = os.path.join(hotel_dir, filename)
            with open(filepath, "wb") as f:
                f.write(b"test")
            url = f"/static/hotel_images/1/{filename}"
            with patch("app.core.image_utils._get_static_dir", return_value=tmpdir):
                delete_facility_image_file(1, key, url)
            assert not os.path.isfile(filepath)

    def test_delete_ignores_invalid_url(self):
        """url が /static/hotel_images/ を含まない場合は削除されない"""
        with tempfile.TemporaryDirectory() as tmpdir:
            hotel_dir = os.path.join(tmpdir, "hotel_images", "1")
            os.makedirs(hotel_dir, exist_ok=True)
            key = "abc123"
            filename = f"{key}.jpg"
            filepath = os.path.join(hotel_dir, filename)
            with open(filepath, "wb") as f:
                f.write(b"test")
            with patch("app.core.image_utils._get_static_dir", return_value=tmpdir):
                delete_facility_image_file(1, key, "/other/path/image.jpg")
            assert os.path.isfile(filepath)

    def test_delete_ignores_empty_url(self):
        """url が空の場合は何もしない"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.core.image_utils._get_static_dir", return_value=tmpdir):
                delete_facility_image_file(1, "abc", "")
                delete_facility_image_file(1, "abc", None)  # type: ignore


class TestCompressImage:
    """compress_image のテスト（PIL がある場合のみ）"""

    @pytest.mark.skipif(not HAS_PIL, reason="PIL not installed")
    def test_compress_resizes_large_image(self):
        """長辺が FACILITY_IMAGE_MAX_SIDE を超える画像はリサイズされる"""
        from io import BytesIO

        from PIL import Image

        # 2000x1000 の画像を生成（長辺 2000 > 1920）
        img = Image.new("RGB", (2000, 1000), color="red")
        buf = BytesIO()
        img.save(buf, "JPEG", quality=90)
        content = buf.getvalue()
        result = compress_image(content, ".jpg")
        assert isinstance(result, bytes)
        assert len(result) > 0
        # リサイズ後は長辺が FACILITY_IMAGE_MAX_SIDE 以下
        out_img = Image.open(BytesIO(result))
        w, h = out_img.size
        assert max(w, h) <= FACILITY_IMAGE_MAX_SIDE
