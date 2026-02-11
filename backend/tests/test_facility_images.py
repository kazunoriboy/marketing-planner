"""
施設画像API（POST/DELETE/PUT /facility/hotels/{id}/images）のテスト
"""

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Hotel, FacilityAdmin, FacilityAdminHotel, FacilityAdminHotelRole
from app.auth.password import hash_password


# テスト用の最小 JPEG バイト列
MINIMAL_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


@pytest.fixture(name="facility_admin_viewer")
def facility_admin_viewer_fixture(session: Session, sample_hotel: Hotel) -> FacilityAdmin:
    """viewer ロールの施設管理者（編集不可）"""
    admin = FacilityAdmin(
        email="viewer@facility.com",
        password_hash=hash_password("viewerpass"),
        name="Viewer",
        is_active=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    permission = FacilityAdminHotel(
        facility_admin_id=admin.id,
        hotel_id=sample_hotel.id,
        role=FacilityAdminHotelRole.viewer,
    )
    session.add(permission)
    session.commit()
    return admin


@pytest.fixture(name="viewer_auth_headers")
def viewer_auth_headers_fixture(client: TestClient, facility_admin_viewer: FacilityAdmin) -> dict:
    """viewer の認証ヘッダー"""
    response = client.post(
        "/facility/auth/login",
        json={"email": "viewer@facility.com", "password": "viewerpass"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="other_hotel_and_admin")
def other_hotel_and_admin_fixture(session: Session) -> tuple[Hotel, FacilityAdmin]:
    """別施設とその owner 管理者（sample_hotel には権限なし）"""
    hotel = Hotel(
        name="他施設",
        address="他住所",
    )
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    admin = FacilityAdmin(
        email="other@facility.com",
        password_hash=hash_password("otherpass"),
        name="Other",
        is_active=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    permission = FacilityAdminHotel(
        facility_admin_id=admin.id,
        hotel_id=hotel.id,
        role=FacilityAdminHotelRole.owner,
    )
    session.add(permission)
    session.commit()
    return hotel, admin


@pytest.fixture(name="other_auth_headers")
def other_auth_headers_fixture(client: TestClient, other_hotel_and_admin: tuple[Hotel, FacilityAdmin]) -> dict:
    """別施設管理者の認証ヘッダー"""
    _, admin = other_hotel_and_admin
    response = client.post(
        "/facility/auth/login",
        json={"email": "other@facility.com", "password": "otherpass"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="hotel_with_10_images")
def hotel_with_10_images_fixture(session: Session, sample_hotel: Hotel) -> Hotel:
    """施設画像が10枚のホテル（アップロード上限テスト用）"""
    from sqlalchemy.orm.attributes import flag_modified

    images = [
        {
            "key": f"img{i:03d}",
            "url": f"/static/hotel_images/{sample_hotel.id}/img{i:03d}.jpg",
            "description": "",
            "type": "exterior",
            "order": i,
        }
        for i in range(10)
    ]
    sample_hotel.facility_images = images
    flag_modified(sample_hotel, "facility_images")
    session.add(sample_hotel)
    session.commit()
    session.refresh(sample_hotel)
    return sample_hotel


class TestUploadFacilityImage:
    """POST /facility/hotels/{hotel_id}/images のテスト"""

    @patch("app.api.facility_hotels.save_facility_image")
    def test_upload_success(
        self,
        mock_save: object,
        client: TestClient,
        auth_headers: dict,
        sample_hotel: Hotel,
    ) -> None:
        """owner がアップロードすると 201 と FacilityImageItemResponse が返る"""
        mock_save.return_value = ("mockkey123", f"/static/hotel_images/{sample_hotel.id}/mockkey123.jpg")
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/images",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "exterior", "description": "テスト説明"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "mockkey123"
        assert "mockkey123" in data["url"]
        assert data["type"] == "exterior"
        assert data["description"] == "テスト説明"
        assert "order" in data
        mock_save.assert_called_once()

    def test_upload_403_no_auth(
        self,
        client: TestClient,
        sample_hotel: Hotel,
    ) -> None:
        """未認証では 401（認証エンドポイントが先に返す）"""
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/images",
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "exterior"},
        )
        assert response.status_code == 401

    def test_upload_403_other_hotel(
        self,
        client: TestClient,
        sample_hotel: Hotel,
        other_auth_headers: dict,
    ) -> None:
        """他施設のみ権限がある管理者が sample_hotel にアップロードすると 403"""
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/images",
            headers=other_auth_headers,
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "exterior"},
        )
        assert response.status_code == 403
        assert "アクセス権限" in response.json().get("detail", "")

    def test_upload_403_viewer(
        self,
        client: TestClient,
        sample_hotel: Hotel,
        viewer_auth_headers: dict,
    ) -> None:
        """viewer ロールでは 403"""
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/images",
            headers=viewer_auth_headers,
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "exterior"},
        )
        assert response.status_code == 403
        assert "編集権限" in response.json().get("detail", "")

    def test_upload_404_hotel(
        self,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        """存在しない hotel_id では 403（権限チェックが先に「アクセス権限なし」を返す）"""
        response = client.post(
            "/facility/hotels/99999/images",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "exterior"},
        )
        assert response.status_code == 403

    @patch("app.api.facility_hotels.save_facility_image")
    def test_upload_400_max_count(
        self,
        mock_save: object,
        client: TestClient,
        auth_headers: dict,
        hotel_with_10_images: Hotel,
    ) -> None:
        """画像が10枚の施設に追加すると 400"""
        response = client.post(
            f"/facility/hotels/{hotel_with_10_images.id}/images",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "exterior"},
        )
        assert response.status_code == 400
        assert "最大" in response.json().get("detail", "")
        mock_save.assert_not_called()

    @patch("app.api.facility_hotels.save_facility_image")
    def test_upload_400_invalid_type(
        self,
        mock_save: object,
        client: TestClient,
        auth_headers: dict,
        sample_hotel: Hotel,
    ) -> None:
        """無効な type では 400"""
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/images",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(MINIMAL_JPEG), "image/jpeg")},
            data={"type": "invalid_type"},
        )
        assert response.status_code == 400
        assert "種別" in response.json().get("detail", "")
        mock_save.assert_not_called()

    @patch("app.api.facility_hotels.save_facility_image")
    def test_upload_400_invalid_extension(
        self,
        mock_save: object,
        client: TestClient,
        auth_headers: dict,
        sample_hotel: Hotel,
    ) -> None:
        """無効な拡張子では 400"""
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/images",
            headers=auth_headers,
            files={"file": ("test.txt", BytesIO(b"not an image"), "text/plain")},
            data={"type": "exterior"},
        )
        assert response.status_code == 400
        assert "ファイル形式" in response.json().get("detail", "")
        mock_save.assert_not_called()


class TestDeleteFacilityImage:
    """DELETE /facility/hotels/{hotel_id}/images/{image_key} のテスト"""

    @patch("app.api.facility_hotels.delete_facility_image_file")
    def test_delete_success(
        self,
        mock_delete: object,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """削除成功で 204"""
        response = client.delete(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
            headers=auth_headers,
        )
        assert response.status_code == 204
        mock_delete.assert_called_once()

    def test_delete_403_no_auth(
        self,
        client: TestClient,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """未認証では 401（認証エンドポイントが先に返す）"""
        response = client.delete(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
        )
        assert response.status_code == 401

    def test_delete_404_hotel(
        self,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        """存在しない hotel_id では 403（権限チェックが先に「アクセス権限なし」を返す）"""
        response = client.delete(
            "/facility/hotels/99999/images/img001",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_delete_404_image_key(
        self,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """存在しない image_key では 404"""
        response = client.delete(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "画像が見つかりません" in response.json().get("detail", "")


class TestUpdateFacilityImage:
    """PUT /facility/hotels/{hotel_id}/images/{image_key} のテスト"""

    def test_update_success_type_only(
        self,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """type のみ更新で 200 と更新後のレスポンス"""
        response = client.put(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
            headers=auth_headers,
            json={"type": "interior"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "interior"
        assert data["key"] == "img001"
        assert data["description"] == "テスト画像"

    def test_update_success_description_only(
        self,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """description のみ更新で 200"""
        response = client.put(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
            headers=auth_headers,
            json={"description": "更新後の説明"},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "更新後の説明"

    def test_update_success_both(
        self,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """type と description 両方更新で 200"""
        response = client.put(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
            headers=auth_headers,
            json={"type": "room", "description": "部屋写真"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "room"
        assert data["description"] == "部屋写真"

    def test_update_403_no_auth(
        self,
        client: TestClient,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """未認証では 401（認証エンドポイントが先に返す）"""
        response = client.put(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
            json={"type": "interior"},
        )
        assert response.status_code == 401

    def test_update_404_hotel(
        self,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        """存在しない hotel_id では 403（権限チェックが先に「アクセス権限なし」を返す）"""
        response = client.put(
            "/facility/hotels/99999/images/img001",
            headers=auth_headers,
            json={"type": "interior"},
        )
        assert response.status_code == 403

    def test_update_404_image_key(
        self,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """存在しない image_key では 404"""
        response = client.put(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/nonexistent",
            headers=auth_headers,
            json={"type": "interior"},
        )
        assert response.status_code == 404

    def test_update_400_invalid_type(
        self,
        client: TestClient,
        auth_headers: dict,
        hotel_with_facility_images: Hotel,
    ) -> None:
        """無効な type では 400"""
        response = client.put(
            f"/facility/hotels/{hotel_with_facility_images.id}/images/img001",
            headers=auth_headers,
            json={"type": "invalid_type"},
        )
        assert response.status_code == 400
        assert "種別" in response.json().get("detail", "")
