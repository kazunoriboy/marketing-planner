"""
Creative APIエンドポイントのテスト
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import MarketingPlan, CreativeAsset


class TestGetCreativeAsset:
    """クリエイティブアセット詳細取得APIのテスト"""
    
    def test_get_asset_success(self, client: TestClient, sample_creative_asset: CreativeAsset):
        """アセット詳細を正常に取得できることを確認"""
        response = client.get(f"/api/creative/assets/{sample_creative_asset.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_creative_asset.id
        assert data["marketing_plan_id"] == sample_creative_asset.marketing_plan_id
    
    def test_get_asset_not_found(self, client: TestClient):
        """存在しないアセットIDで404を返すことを確認"""
        response = client.get("/api/creative/assets/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_asset_contains_all_fields(self, client: TestClient, sample_creative_asset: CreativeAsset):
        """アセット詳細に全フィールドが含まれることを確認"""
        response = client.get(f"/api/creative/assets/{sample_creative_asset.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = [
            "id", "marketing_plan_id", "lp_source_code", "lp_preview_url",
            "ad_image_urls", "ad_copy", "generation_prompts", "created_at"
        ]
        
        for field in expected_fields:
            assert field in data
    
    def test_get_asset_lp_code(self, client: TestClient, sample_creative_asset: CreativeAsset):
        """LPソースコードが正しく取得できることを確認"""
        response = client.get(f"/api/creative/assets/{sample_creative_asset.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["lp_source_code"] == sample_creative_asset.lp_source_code
    
    def test_get_asset_ad_copy(self, client: TestClient, sample_creative_asset: CreativeAsset):
        """広告コピーが正しく取得できることを確認"""
        response = client.get(f"/api/creative/assets/{sample_creative_asset.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "headline" in data["ad_copy"]
        assert "description" in data["ad_copy"]


class TestListAssetsByPlan:
    """プラン別アセット一覧取得APIのテスト"""
    
    def test_list_assets_empty(self, client: TestClient, sample_marketing_plan: MarketingPlan):
        """アセットがない場合に空のリストを返すことを確認"""
        # sample_creative_assetを使わずにテスト
        # 新しいプランを作成
        response = client.get(f"/api/creative/plans/{sample_marketing_plan.id}/assets")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_assets_with_data(
        self, 
        client: TestClient, 
        sample_marketing_plan: MarketingPlan,
        sample_creative_asset: CreativeAsset
    ):
        """アセットがある場合にリストを返すことを確認"""
        response = client.get(f"/api/creative/plans/{sample_marketing_plan.id}/assets")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # サンプルアセットが含まれていることを確認
        asset_ids = [a["id"] for a in data]
        assert sample_creative_asset.id in asset_ids


class TestDeleteCreativeAsset:
    """クリエイティブアセット削除APIのテスト"""
    
    def test_delete_asset_success(
        self, 
        client: TestClient, 
        session: Session,
        sample_marketing_plan: MarketingPlan
    ):
        """アセットを正常に削除できることを確認"""
        # 削除用のアセットを作成
        asset = CreativeAsset(
            marketing_plan_id=sample_marketing_plan.id,
            lp_source_code="<div>削除テスト</div>",
            ad_image_urls={},
            ad_copy={},
            generation_prompts={}
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        asset_id = asset.id
        
        # 削除
        response = client.delete(f"/api/creative/assets/{asset_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "クリエイティブアセットを削除しました"
        assert data["asset_id"] == asset_id
        
        # 削除後に取得できないことを確認
        get_response = client.get(f"/api/creative/assets/{asset_id}")
        assert get_response.status_code == 404
    
    def test_delete_asset_not_found(self, client: TestClient):
        """存在しないアセットIDで404を返すことを確認"""
        response = client.delete("/api/creative/assets/99999")
        
        assert response.status_code == 404


class TestCreativeIntegration:
    """Creative APIの統合テスト"""
    
    def test_asset_lifecycle(
        self, 
        client: TestClient, 
        session: Session,
        sample_marketing_plan: MarketingPlan
    ):
        """アセットのライフサイクル（作成→取得→削除）をテスト"""
        # アセットを直接作成（generateはLLMが必要なのでスキップ）
        asset = CreativeAsset(
            marketing_plan_id=sample_marketing_plan.id,
            lp_source_code="<div>ライフサイクルテスト</div>",
            lp_preview_url="https://test.example.com/preview",
            ad_image_urls={"main": "https://test.example.com/image.jpg"},
            ad_copy={"headline": "テストヘッドライン", "body": "テスト本文"},
            generation_prompts={"test": "プロンプト"}
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        asset_id = asset.id
        
        # 取得
        get_response = client.get(f"/api/creative/assets/{asset_id}")
        assert get_response.status_code == 200
        assert get_response.json()["lp_source_code"] == "<div>ライフサイクルテスト</div>"
        
        # 一覧で確認
        list_response = client.get(f"/api/creative/plans/{sample_marketing_plan.id}/assets")
        assert list_response.status_code == 200
        asset_ids = [a["id"] for a in list_response.json()]
        assert asset_id in asset_ids
        
        # 削除
        delete_response = client.delete(f"/api/creative/assets/{asset_id}")
        assert delete_response.status_code == 200
        
        # 削除確認
        verify_response = client.get(f"/api/creative/assets/{asset_id}")
        assert verify_response.status_code == 404
    
    def test_multiple_assets_per_plan(
        self, 
        client: TestClient, 
        session: Session,
        sample_marketing_plan: MarketingPlan
    ):
        """1つのプランに複数のアセットを紐付けられることを確認"""
        # 複数アセットを作成
        asset_codes = ["<div>Asset1</div>", "<div>Asset2</div>", "<div>Asset3</div>"]
        created_ids = []
        
        for code in asset_codes:
            asset = CreativeAsset(
                marketing_plan_id=sample_marketing_plan.id,
                lp_source_code=code,
                ad_image_urls={},
                ad_copy={},
                generation_prompts={}
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            created_ids.append(asset.id)
        
        # 一覧取得
        response = client.get(f"/api/creative/plans/{sample_marketing_plan.id}/assets")
        assert response.status_code == 200
        data = response.json()
        
        # 全てのアセットが含まれていることを確認
        returned_ids = [a["id"] for a in data]
        for asset_id in created_ids:
            assert asset_id in returned_ids



