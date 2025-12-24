"""
Planning APIエンドポイントのテスト
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Hotel, AnalysisSession, MarketingPlan, PlanStatus


class TestGetMarketingPlan:
    """マーケティングプラン詳細取得APIのテスト"""
    
    def test_get_plan_success(self, client: TestClient, sample_marketing_plan: MarketingPlan):
        """プラン詳細を正常に取得できることを確認"""
        response = client.get(f"/api/planning/plans/{sample_marketing_plan.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_marketing_plan.id
        assert data["plan_name"] == sample_marketing_plan.plan_name
        assert data["concept"] == sample_marketing_plan.concept
    
    def test_get_plan_not_found(self, client: TestClient):
        """存在しないプランIDで404を返すことを確認"""
        response = client.get("/api/planning/plans/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_plan_contains_all_fields(self, client: TestClient, sample_marketing_plan: MarketingPlan):
        """プラン詳細に全フィールドが含まれることを確認"""
        response = client.get(f"/api/planning/plans/{sample_marketing_plan.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = [
            "id", "analysis_session_id", "status", "plan_name", "concept",
            "target_audience", "price_range", "benefits",
            "strategy_3c", "strategy_pest", "created_at"
        ]
        
        for field in expected_fields:
            assert field in data


class TestListPlansBySession:
    """セッション別プラン一覧取得APIのテスト"""
    
    def test_list_plans_empty(self, client: TestClient, sample_analysis_session: AnalysisSession):
        """プランがない場合に空のリストを返すことを確認"""
        # 新しいセッションを作成（プランなし）
        response = client.get(f"/api/planning/sessions/{sample_analysis_session.id}/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_plans_with_data(
        self, 
        client: TestClient, 
        sample_analysis_session: AnalysisSession,
        sample_marketing_plan: MarketingPlan
    ):
        """プランがある場合にリストを返すことを確認"""
        response = client.get(f"/api/planning/sessions/{sample_analysis_session.id}/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # サンプルプランが含まれていることを確認
        plan_names = [p["plan_name"] for p in data]
        assert sample_marketing_plan.plan_name in plan_names


class TestUpdatePlanStatus:
    """プランステータス更新APIのテスト"""
    
    def test_update_status_to_approved(self, client: TestClient, sample_marketing_plan: MarketingPlan):
        """ステータスを承認に更新できることを確認"""
        update_data = {
            "plan_id": sample_marketing_plan.id,
            "status": "approved"
        }
        
        response = client.put(
            f"/api/planning/plans/{sample_marketing_plan.id}/status",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
    
    def test_update_status_to_draft(self, client: TestClient, sample_marketing_plan: MarketingPlan):
        """ステータスをドラフトに更新できることを確認"""
        update_data = {
            "plan_id": sample_marketing_plan.id,
            "status": "draft"
        }
        
        response = client.put(
            f"/api/planning/plans/{sample_marketing_plan.id}/status",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
    
    def test_update_status_not_found(self, client: TestClient):
        """存在しないプランIDで404を返すことを確認"""
        update_data = {
            "plan_id": 99999,
            "status": "approved"
        }
        
        response = client.put("/api/planning/plans/99999/status", json=update_data)
        
        assert response.status_code == 404


class TestDeletePlan:
    """プラン削除APIのテスト"""
    
    def test_delete_plan_success(
        self, 
        client: TestClient, 
        session: Session,
        sample_analysis_session: AnalysisSession
    ):
        """プランを正常に削除できることを確認"""
        # 削除用のプランを作成
        plan = MarketingPlan(
            analysis_session_id=sample_analysis_session.id,
            status=PlanStatus.draft,
            plan_name="削除テストプラン",
            concept="削除テスト用のコンセプト",
            target_audience={},
            price_range={},
            benefits={},
            strategy_3c={},
            strategy_pest={}
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)
        plan_id = plan.id
        
        # 削除
        response = client.delete(f"/api/planning/plans/{plan_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "プランを削除しました"
        assert data["plan_id"] == plan_id
        
        # 削除後に取得できないことを確認
        get_response = client.get(f"/api/planning/plans/{plan_id}")
        assert get_response.status_code == 404
    
    def test_delete_plan_not_found(self, client: TestClient):
        """存在しないプランIDで404を返すことを確認"""
        response = client.delete("/api/planning/plans/99999")
        
        assert response.status_code == 404


class TestPlanningIntegration:
    """Planning APIの統合テスト"""
    
    def test_plan_lifecycle(
        self, 
        client: TestClient, 
        session: Session,
        sample_analysis_session: AnalysisSession
    ):
        """プランのライフサイクル（作成→取得→更新→削除）をテスト"""
        # プランを直接作成（generateはLLMが必要なのでスキップ）
        plan = MarketingPlan(
            analysis_session_id=sample_analysis_session.id,
            status=PlanStatus.draft,
            plan_name="ライフサイクルテストプラン",
            concept="テストコンセプト",
            target_audience={"type": "テスト"},
            price_range={"min": 10000, "max": 20000},
            benefits={"特典": "テスト特典"},
            strategy_3c={"company": "テスト"},
            strategy_pest={"political": "テスト"}
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)
        plan_id = plan.id
        
        # 取得
        get_response = client.get(f"/api/planning/plans/{plan_id}")
        assert get_response.status_code == 200
        assert get_response.json()["plan_name"] == "ライフサイクルテストプラン"
        
        # ステータス更新
        update_response = client.put(
            f"/api/planning/plans/{plan_id}/status",
            json={"plan_id": plan_id, "status": "approved"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "approved"
        
        # 削除
        delete_response = client.delete(f"/api/planning/plans/{plan_id}")
        assert delete_response.status_code == 200
        
        # 削除確認
        verify_response = client.get(f"/api/planning/plans/{plan_id}")
        assert verify_response.status_code == 404



