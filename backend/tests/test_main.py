"""
基本APIエンドポイントのテスト
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """ルートエンドポイントのテスト"""
    
    def test_root_returns_success(self, client: TestClient):
        """ルートエンドポイントが正常にレスポンスを返すことを確認"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
    
    def test_root_contains_expected_message(self, client: TestClient):
        """ルートエンドポイントのメッセージを確認"""
        response = client.get("/")
        data = response.json()
        
        assert "FastAPI Backend" in data["message"]
        assert "マーケティング" in data["message"]


class TestHealthEndpoint:
    """ヘルスチェックエンドポイントのテスト"""
    
    def test_health_returns_healthy(self, client: TestClient):
        """ヘルスチェックがhealthyを返すことを確認"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "marketing-planner-api"
    
    def test_health_contains_version(self, client: TestClient):
        """ヘルスチェックにバージョン情報が含まれることを確認"""
        response = client.get("/health")
        data = response.json()
        
        assert "version" in data


class TestApiTestEndpoint:
    """APIテストエンドポイントのテスト"""
    
    def test_api_test_returns_success(self, client: TestClient):
        """APIテストエンドポイントが正常にレスポンスを返すことを確認"""
        response = client.get("/api/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "API接続テスト成功"
    
    def test_api_test_contains_features(self, client: TestClient):
        """APIテストエンドポイントに機能一覧が含まれることを確認"""
        response = client.get("/api/test")
        data = response.json()
        
        assert "features" in data
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0
    
    def test_api_test_contains_ai_models(self, client: TestClient):
        """APIテストエンドポイントにAIモデル情報が含まれることを確認"""
        response = client.get("/api/test")
        data = response.json()
        
        assert "ai_models" in data
        assert isinstance(data["ai_models"], list)


class TestNonExistentEndpoint:
    """存在しないエンドポイントのテスト"""
    
    def test_non_existent_returns_404(self, client: TestClient):
        """存在しないエンドポイントが404を返すことを確認"""
        response = client.get("/non-existent-endpoint")
        
        assert response.status_code == 404


