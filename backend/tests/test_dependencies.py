"""
認証依存関係のユニットテスト
"""

import pytest
from sqlmodel import Session

from app.models import (
    FacilityAdmin,
    FacilityAdminHotel,
    FacilityAdminHotelRole,
    Hotel,
)
from app.auth.dependencies import check_hotel_permission
from app.auth.password import hash_password


@pytest.fixture(name="test_facility_admin")
def test_facility_admin_fixture(session: Session) -> FacilityAdmin:
    """テスト用施設管理者"""
    admin = FacilityAdmin(
        email="test_dep@example.com",
        password_hash=hash_password("TestPassword123"),
        name="依存テスト管理者",
        is_active=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture(name="test_hotel")
def test_hotel_fixture(session: Session) -> Hotel:
    """テスト用ホテル"""
    hotel = Hotel(
        name="依存テスト旅館",
        address="東京都テスト区1-1-1",
    )
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    return hotel


class TestCheckHotelPermission:
    """check_hotel_permission関数のテスト"""
    
    def test_no_permission(
        self,
        session: Session,
        test_facility_admin: FacilityAdmin,
        test_hotel: Hotel
    ):
        """権限がない場合にFalseを返すことを確認"""
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            required_roles=["owner", "editor", "viewer"],
            session=session
        )
        assert result is False
    
    def test_owner_permission(
        self,
        session: Session,
        test_facility_admin: FacilityAdmin,
        test_hotel: Hotel
    ):
        """オーナー権限がある場合にTrueを返すことを確認"""
        # 権限を追加
        permission = FacilityAdminHotel(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            role=FacilityAdminHotelRole.owner,
        )
        session.add(permission)
        session.commit()
        
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            required_roles=["owner"],
            session=session
        )
        assert result is True
    
    def test_editor_permission_for_owner_only(
        self,
        session: Session,
        test_facility_admin: FacilityAdmin,
        test_hotel: Hotel
    ):
        """編集者権限でオーナー専用操作ができないことを確認"""
        # 編集者権限を追加
        permission = FacilityAdminHotel(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            role=FacilityAdminHotelRole.editor,
        )
        session.add(permission)
        session.commit()
        
        # オーナー専用権限チェック
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            required_roles=["owner"],
            session=session
        )
        assert result is False
        
        # 編集者以上権限チェック
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            required_roles=["owner", "editor"],
            session=session
        )
        assert result is True
    
    def test_viewer_permission(
        self,
        session: Session,
        test_facility_admin: FacilityAdmin,
        test_hotel: Hotel
    ):
        """閲覧者権限のテスト"""
        # 閲覧者権限を追加
        permission = FacilityAdminHotel(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            role=FacilityAdminHotelRole.viewer,
        )
        session.add(permission)
        session.commit()
        
        # 閲覧者は読み取りできる
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            required_roles=["owner", "editor", "viewer"],
            session=session
        )
        assert result is True
        
        # 閲覧者は編集できない
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=test_hotel.id,
            required_roles=["owner", "editor"],
            session=session
        )
        assert result is False
    
    def test_nonexistent_hotel(
        self,
        session: Session,
        test_facility_admin: FacilityAdmin
    ):
        """存在しないホテルに対してFalseを返すことを確認"""
        result = check_hotel_permission(
            facility_admin_id=test_facility_admin.id,
            hotel_id=99999,
            required_roles=["owner", "editor", "viewer"],
            session=session
        )
        assert result is False
    
    def test_nonexistent_admin(
        self,
        session: Session,
        test_hotel: Hotel
    ):
        """存在しない管理者に対してFalseを返すことを確認"""
        result = check_hotel_permission(
            facility_admin_id=99999,
            hotel_id=test_hotel.id,
            required_roles=["owner", "editor", "viewer"],
            session=session
        )
        assert result is False


class TestPermissionRoles:
    """権限ロールの値テスト"""
    
    def test_role_values(self):
        """ロールの値が正しいことを確認"""
        assert FacilityAdminHotelRole.owner.value == "owner"
        assert FacilityAdminHotelRole.editor.value == "editor"
        assert FacilityAdminHotelRole.viewer.value == "viewer"
    
    def test_role_comparison(self):
        """ロールの比較が正しく動作することを確認"""
        owner = FacilityAdminHotelRole.owner
        editor = FacilityAdminHotelRole.editor
        viewer = FacilityAdminHotelRole.viewer
        
        assert owner.value in ["owner"]
        assert editor.value in ["owner", "editor"]
        assert viewer.value in ["owner", "editor", "viewer"]


