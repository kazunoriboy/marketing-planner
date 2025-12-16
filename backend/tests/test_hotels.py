"""
Hotel APIエンドポイントのテスト
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Hotel


class TestCreateHotel:
    """ホテル作成APIのテスト"""
    
    def test_create_hotel_success(self, client: TestClient):
        """ホテルを正常に作成できることを確認"""
        hotel_data = {
            "name": "新規テスト旅館",
            "address": "東京都新宿区テスト町1-1-1",
            "postal_code": "160-0001",
            "phone": "03-9999-8888",
            "email": "new@example.com",
            "website": "https://new-ryokan.example.com",
            "features": {"温泉": "露天風呂"},
            "strengths": {"サービス": "24時間対応"}
        }
        
        response = client.post("/api/analysis/hotels", json=hotel_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == hotel_data["name"]
        assert data["address"] == hotel_data["address"]
        assert data["postal_code"] == hotel_data["postal_code"]
        assert "id" in data
        assert data["id"] is not None
    
    def test_create_hotel_minimal_data(self, client: TestClient):
        """最小限のデータでホテルを作成できることを確認"""
        hotel_data = {
            "name": "最小データ旅館",
            "address": "東京都千代田区"
        }
        
        response = client.post("/api/analysis/hotels", json=hotel_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == hotel_data["name"]
        assert data["address"] == hotel_data["address"]
        assert data["postal_code"] is None
        assert data["phone"] is None
    
    def test_create_hotel_missing_required_fields(self, client: TestClient):
        """必須フィールドが欠けている場合にエラーを返すことを確認"""
        # nameが欠けている
        hotel_data = {
            "address": "東京都千代田区"
        }
        
        response = client.post("/api/analysis/hotels", json=hotel_data)
        
        assert response.status_code == 422  # Validation Error
    
    def test_create_hotel_with_features(self, client: TestClient):
        """特徴情報を含むホテルを作成できることを確認"""
        hotel_data = {
            "name": "特徴付き旅館",
            "address": "京都府京都市",
            "features": {
                "温泉": "源泉かけ流し",
                "料理": "京料理",
                "部屋": "和室"
            },
            "strengths": {
                "立地": "観光地近く",
                "歴史": "創業100年"
            }
        }
        
        response = client.post("/api/analysis/hotels", json=hotel_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["features"]["温泉"] == "源泉かけ流し"
        assert data["strengths"]["歴史"] == "創業100年"


class TestListHotels:
    """ホテル一覧取得APIのテスト"""
    
    def test_list_hotels_empty(self, client: TestClient):
        """ホテルがない場合に空のリストを返すことを確認"""
        response = client.get("/api/analysis/hotels")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_hotels_with_data(self, client: TestClient, sample_hotel: Hotel):
        """ホテルがある場合にリストを返すことを確認"""
        response = client.get("/api/analysis/hotels")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # サンプルホテルが含まれていることを確認
        hotel_names = [h["name"] for h in data]
        assert sample_hotel.name in hotel_names
    
    def test_list_hotels_multiple(self, client: TestClient):
        """複数のホテルを作成して一覧取得できることを確認"""
        # 複数のホテルを作成
        for i in range(3):
            hotel_data = {
                "name": f"テスト旅館{i+1}",
                "address": f"東京都テスト区{i+1}"
            }
            client.post("/api/analysis/hotels", json=hotel_data)
        
        response = client.get("/api/analysis/hotels")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestGetHotel:
    """ホテル詳細取得APIのテスト"""
    
    def test_get_hotel_success(self, client: TestClient, sample_hotel: Hotel):
        """ホテル詳細を正常に取得できることを確認"""
        response = client.get(f"/api/analysis/hotels/{sample_hotel.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_hotel.id
        assert data["name"] == sample_hotel.name
        assert data["address"] == sample_hotel.address
    
    def test_get_hotel_not_found(self, client: TestClient):
        """存在しないホテルIDで404を返すことを確認"""
        response = client.get("/api/analysis/hotels/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_hotel_contains_all_fields(self, client: TestClient, sample_hotel: Hotel):
        """ホテル詳細に全フィールドが含まれることを確認"""
        response = client.get(f"/api/analysis/hotels/{sample_hotel.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = [
            "id", "name", "address", "postal_code", "phone",
            "email", "website", "features", "strengths", "created_at"
        ]
        
        for field in expected_fields:
            assert field in data


class TestHotelIntegration:
    """ホテルAPIの統合テスト"""
    
    def test_create_and_get_hotel(self, client: TestClient):
        """ホテルを作成して取得できることを確認"""
        # 作成
        hotel_data = {
            "name": "統合テスト旅館",
            "address": "大阪府大阪市"
        }
        create_response = client.post("/api/analysis/hotels", json=hotel_data)
        assert create_response.status_code == 200
        created_hotel = create_response.json()
        
        # 取得
        get_response = client.get(f"/api/analysis/hotels/{created_hotel['id']}")
        assert get_response.status_code == 200
        fetched_hotel = get_response.json()
        
        assert fetched_hotel["id"] == created_hotel["id"]
        assert fetched_hotel["name"] == hotel_data["name"]
    
    def test_create_multiple_and_list(self, client: TestClient):
        """複数ホテルを作成して一覧で確認できることを確認"""
        hotel_names = ["旅館A", "旅館B", "旅館C"]
        
        # 複数作成
        for name in hotel_names:
            client.post("/api/analysis/hotels", json={
                "name": name,
                "address": "テスト住所"
            })
        
        # 一覧取得
        response = client.get("/api/analysis/hotels")
        data = response.json()
        
        returned_names = [h["name"] for h in data]
        for name in hotel_names:
            assert name in returned_names


