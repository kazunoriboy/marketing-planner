"""
マルチテナント マーケティングAPI認証テスト

施設ごとのアクセス権限チェックをテストします。
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from typing import Generator

from app.models import (
    Hotel,
    FacilityAdmin,
    FacilityAdminHotel,
    FacilityAdminHotelRole,
    AnalysisSession,
    MarketingPlan,
    PlanStatus,
)
from app.auth.jwt import create_access_token
from app.auth.schemas import UserType
from app.auth.password import hash_password


# ============================================
# フィクスチャ
# ============================================

@pytest.fixture(name="facility_admin")
def facility_admin_fixture(session: Session) -> FacilityAdmin:
    """テスト用の施設管理者を作成"""
    admin = FacilityAdmin(
        email="facility@example.com",
        password_hash=hash_password("TestPassword123"),
        name="テスト施設管理者",
        is_active=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture(name="facility_admin_token")
def facility_admin_token_fixture(facility_admin: FacilityAdmin) -> str:
    """施設管理者用のアクセストークンを生成"""
    return create_access_token(facility_admin.id, UserType.facility)


@pytest.fixture(name="other_facility_admin")
def other_facility_admin_fixture(session: Session) -> FacilityAdmin:
    """別の施設管理者を作成（権限なしテスト用）"""
    admin = FacilityAdmin(
        email="other@example.com",
        password_hash=hash_password("TestPassword123"),
        name="他の施設管理者",
        is_active=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture(name="other_facility_admin_token")
def other_facility_admin_token_fixture(other_facility_admin: FacilityAdmin) -> str:
    """別の施設管理者用のアクセストークン"""
    return create_access_token(other_facility_admin.id, UserType.facility)


@pytest.fixture(name="hotel_with_permission")
def hotel_with_permission_fixture(
    session: Session,
    sample_hotel: Hotel,
    facility_admin: FacilityAdmin
) -> Hotel:
    """施設管理者に権限を付与したホテル"""
    permission = FacilityAdminHotel(
        facility_admin_id=facility_admin.id,
        hotel_id=sample_hotel.id,
        role=FacilityAdminHotelRole.owner,
    )
    session.add(permission)
    session.commit()
    return sample_hotel


@pytest.fixture(name="viewer_permission_hotel")
def viewer_permission_hotel_fixture(
    session: Session,
    facility_admin: FacilityAdmin
) -> Hotel:
    """閲覧者権限のみのホテル"""
    hotel = Hotel(
        name="閲覧専用旅館",
        address="東京都港区テスト1-1-1",
    )
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    permission = FacilityAdminHotel(
        facility_admin_id=facility_admin.id,
        hotel_id=hotel.id,
        role=FacilityAdminHotelRole.viewer,
    )
    session.add(permission)
    session.commit()
    
    return hotel


@pytest.fixture(name="hotel_with_analysis")
def hotel_with_analysis_fixture(
    session: Session,
    hotel_with_permission: Hotel
) -> tuple[Hotel, AnalysisSession]:
    """分析セッション付きホテル"""
    analysis_session = AnalysisSession(
        hotel_id=hotel_with_permission.id,
        csv_statistics={
            "total_records": 100,
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
        },
        csv_insights="テストインサイト",
        competitors_list={
            "area_type": "温泉地",
            "estimated_competitors": "10",
        },
    )
    session.add(analysis_session)
    session.commit()
    session.refresh(analysis_session)
    return hotel_with_permission, analysis_session


@pytest.fixture(name="hotel_with_plan")
def hotel_with_plan_fixture(
    session: Session,
    hotel_with_analysis: tuple[Hotel, AnalysisSession]
) -> tuple[Hotel, AnalysisSession, MarketingPlan]:
    """マーケティングプラン付きホテル"""
    hotel, analysis_session = hotel_with_analysis
    
    marketing_plan = MarketingPlan(
        analysis_session_id=analysis_session.id,
        status=PlanStatus.draft,
        plan_name="テストプラン",
        concept="テストコンセプト",
        target_audience={"type": "夫婦"},
        price_range={"min": 10000, "max": 30000},
        benefits={"特典": "テスト特典"},
        strategy_3c={"company": "テスト"},
        strategy_pest={"political": "テスト"},
    )
    session.add(marketing_plan)
    session.commit()
    session.refresh(marketing_plan)
    
    return hotel, analysis_session, marketing_plan


# ============================================
# 認証なしでのアクセステスト
# ============================================

class TestUnauthenticatedAccess:
    """認証なしでのアクセスをテスト"""
    
    def test_get_session_without_auth(self, client: TestClient, sample_hotel: Hotel):
        """認証なしで分析セッション取得が401を返すことを確認"""
        response = client.get(f"/api/analysis/hotels/{sample_hotel.id}/session")
        assert response.status_code == 401  # HTTPBearer returns 401 without token
    
    def test_market_analysis_without_auth(self, client: TestClient, sample_hotel: Hotel):
        """認証なしで市場分析が401を返すことを確認"""
        response = client.post(f"/api/analysis/hotels/{sample_hotel.id}/market")
        assert response.status_code == 401
    
    def test_list_plans_without_auth(self, client: TestClient, sample_hotel: Hotel):
        """認証なしでプラン一覧取得が401を返すことを確認"""
        response = client.get(f"/api/planning/hotels/{sample_hotel.id}/plans")
        assert response.status_code == 401


# ============================================
# 権限なしでのアクセステスト
# ============================================

class TestUnauthorizedAccess:
    """権限のない施設へのアクセスをテスト"""
    
    def test_get_session_without_permission(
        self,
        client: TestClient,
        sample_hotel: Hotel,
        other_facility_admin_token: str
    ):
        """権限のない施設の分析セッション取得が403を返すことを確認"""
        response = client.get(
            f"/api/analysis/hotels/{sample_hotel.id}/session",
            headers={"Authorization": f"Bearer {other_facility_admin_token}"}
        )
        assert response.status_code == 403
        assert "アクセス権限がありません" in response.json()["detail"]
    
    def test_market_analysis_without_permission(
        self,
        client: TestClient,
        sample_hotel: Hotel,
        other_facility_admin_token: str
    ):
        """権限のない施設の市場分析が403を返すことを確認"""
        response = client.post(
            f"/api/analysis/hotels/{sample_hotel.id}/market",
            headers={"Authorization": f"Bearer {other_facility_admin_token}"}
        )
        assert response.status_code == 403
    
    def test_list_plans_without_permission(
        self,
        client: TestClient,
        sample_hotel: Hotel,
        other_facility_admin_token: str
    ):
        """権限のない施設のプラン一覧取得が403を返すことを確認"""
        response = client.get(
            f"/api/planning/hotels/{sample_hotel.id}/plans",
            headers={"Authorization": f"Bearer {other_facility_admin_token}"}
        )
        assert response.status_code == 403


# ============================================
# 権限ありでのアクセステスト
# ============================================

class TestAuthorizedAccess:
    """権限のある施設へのアクセスをテスト"""
    
    def test_get_session_with_permission(
        self,
        client: TestClient,
        hotel_with_permission: Hotel,
        facility_admin_token: str
    ):
        """権限のある施設の分析セッション取得が成功することを確認"""
        response = client.get(
            f"/api/analysis/hotels/{hotel_with_permission.id}/session",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # セッションがない場合はsession_idがNone
        assert "session_id" in data
    
    def test_get_session_with_data(
        self,
        client: TestClient,
        hotel_with_analysis: tuple[Hotel, AnalysisSession],
        facility_admin_token: str
    ):
        """分析データがある施設のセッション取得を確認"""
        hotel, analysis_session = hotel_with_analysis
        response = client.get(
            f"/api/analysis/hotels/{hotel.id}/session",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == analysis_session.id
        assert data["csv_statistics"]["total_records"] == 100
        assert data["csv_insights"] == "テストインサイト"
    
    def test_list_plans_with_permission(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        facility_admin_token: str
    ):
        """権限のある施設のプラン一覧取得が成功することを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        response = client.get(
            f"/api/planning/hotels/{hotel.id}/plans",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == marketing_plan.id
        assert data[0]["plan_name"] == "テストプラン"
    
    def test_get_plan_detail_with_permission(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        facility_admin_token: str
    ):
        """権限のある施設のプラン詳細取得が成功することを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        response = client.get(
            f"/api/planning/hotels/{hotel.id}/plans/{marketing_plan.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == marketing_plan.id
        assert data["concept"] == "テストコンセプト"


# ============================================
# 権限レベルのテスト
# ============================================

class TestPermissionLevels:
    """権限レベル（owner/editor/viewer）のテスト"""
    
    def test_viewer_can_read(
        self,
        client: TestClient,
        viewer_permission_hotel: Hotel,
        facility_admin_token: str
    ):
        """閲覧者権限で読み取りができることを確認"""
        response = client.get(
            f"/api/analysis/hotels/{viewer_permission_hotel.id}/session",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
    
    def test_viewer_can_view_plans(
        self,
        client: TestClient,
        viewer_permission_hotel: Hotel,
        facility_admin_token: str
    ):
        """閲覧者権限でプラン一覧を見れることを確認"""
        response = client.get(
            f"/api/planning/hotels/{viewer_permission_hotel.id}/plans",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200


# ============================================
# 存在しない施設へのアクセステスト
# ============================================

class TestNonExistentHotel:
    """存在しない施設へのアクセスをテスト"""
    
    def test_get_session_nonexistent_hotel(
        self,
        client: TestClient,
        facility_admin_token: str
    ):
        """存在しない施設への分析セッション取得が403を返すことを確認"""
        # 権限チェックが先に走るので403になる
        response = client.get(
            "/api/analysis/hotels/99999/session",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 403
    
    def test_list_plans_nonexistent_hotel(
        self,
        client: TestClient,
        facility_admin_token: str
    ):
        """存在しない施設へのプラン一覧取得が403を返すことを確認"""
        response = client.get(
            "/api/planning/hotels/99999/plans",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 403


# ============================================
# プラン操作のテスト
# ============================================

class TestPlanOperations:
    """プラン操作のテスト"""
    
    def test_update_plan_status(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        facility_admin_token: str
    ):
        """プランステータス更新が成功することを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        response = client.put(
            f"/api/planning/hotels/{hotel.id}/plans/{marketing_plan.id}/status",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"plan_id": marketing_plan.id, "status": "approved"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
    
    def test_delete_plan(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        facility_admin_token: str
    ):
        """プラン削除が成功することを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        response = client.delete(
            f"/api/planning/hotels/{hotel.id}/plans/{marketing_plan.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        
        # 削除後に取得しようとすると404
        get_response = client.get(
            f"/api/planning/hotels/{hotel.id}/plans/{marketing_plan.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert get_response.status_code == 404
    
    def test_delete_plan_wrong_hotel(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        viewer_permission_hotel: Hotel,
        facility_admin_token: str
    ):
        """閲覧者権限で削除しようとすると403を返すことを確認"""
        _, _, marketing_plan = hotel_with_plan
        # viewer_permission_hotelは閲覧者権限のみなので削除できない
        response = client.delete(
            f"/api/planning/hotels/{viewer_permission_hotel.id}/plans/{marketing_plan.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        # 削除には編集者以上の権限が必要なので403
        assert response.status_code == 403


# ============================================
# クリエイティブAPIのテスト
# ============================================

class TestCreativeAccess:
    """クリエイティブAPIのアクセステスト"""
    
    def test_list_creative_assets_with_permission(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        facility_admin_token: str
    ):
        """権限のある施設のクリエイティブアセット一覧取得が成功することを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        response = client.get(
            f"/api/creative/hotels/{hotel.id}/plans/{marketing_plan.id}/assets",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_creative_assets_without_permission(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        other_facility_admin_token: str
    ):
        """権限のない施設のクリエイティブアセット一覧取得が403を返すことを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        response = client.get(
            f"/api/creative/hotels/{hotel.id}/plans/{marketing_plan.id}/assets",
            headers={"Authorization": f"Bearer {other_facility_admin_token}"}
        )
        assert response.status_code == 403


# ============================================
# 統合テスト
# ============================================

class TestIntegration:
    """統合テスト"""
    
    def test_full_marketing_flow(
        self,
        client: TestClient,
        hotel_with_analysis: tuple[Hotel, AnalysisSession],
        facility_admin_token: str
    ):
        """マーケティングフルフローのテスト"""
        hotel, analysis_session = hotel_with_analysis
        
        # 1. 分析セッションを取得
        session_response = client.get(
            f"/api/analysis/hotels/{hotel.id}/session",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert session_data["session_id"] == analysis_session.id
        
        # 2. プラン一覧を取得（まだ空）
        plans_response = client.get(
            f"/api/planning/hotels/{hotel.id}/plans",
            headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert plans_response.status_code == 200
        assert plans_response.json() == []
    
    def test_cross_hotel_access_denied(
        self,
        client: TestClient,
        hotel_with_plan: tuple[Hotel, AnalysisSession, MarketingPlan],
        other_facility_admin: FacilityAdmin,
        other_facility_admin_token: str,
        session: Session
    ):
        """別の施設管理者からのクロスアクセスが拒否されることを確認"""
        hotel, _, marketing_plan = hotel_with_plan
        
        # 別のホテルを作成して other_facility_admin に権限を付与
        other_hotel = Hotel(
            name="他の旅館",
            address="大阪府大阪市テスト1-1-1",
        )
        session.add(other_hotel)
        session.commit()
        session.refresh(other_hotel)
        
        other_permission = FacilityAdminHotel(
            facility_admin_id=other_facility_admin.id,
            hotel_id=other_hotel.id,
            role=FacilityAdminHotelRole.owner,
        )
        session.add(other_permission)
        session.commit()
        
        # other_facility_admin は other_hotel にはアクセスできる
        other_response = client.get(
            f"/api/analysis/hotels/{other_hotel.id}/session",
            headers={"Authorization": f"Bearer {other_facility_admin_token}"}
        )
        assert other_response.status_code == 200
        
        # しかし hotel にはアクセスできない
        original_response = client.get(
            f"/api/analysis/hotels/{hotel.id}/session",
            headers={"Authorization": f"Bearer {other_facility_admin_token}"}
        )
        assert original_response.status_code == 403

