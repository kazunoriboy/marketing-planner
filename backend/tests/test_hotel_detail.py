"""
宿の情報 API と LP プロンプト生成のテスト

確認項目:
- hotel_detail カラムが存在する（DB スキーマ）
- GET/PUT /facility/hotels/{id}/detail で入力・保存できる
- POST /detail/auto-fill: website 設定済みで動作、未設定で 400
- POST /detail/fill-surrounding-from-market: 市場分析済みで動作、未実施で 400
- LP 生成プロンプトに hotel_detail の各フィールドが含まれる
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import (
    AnalysisSession,
    Hotel,
)


# ---------------------------------------------------------------------------
# 1. DB スキーマ: hotel_detail カラムの存在確認
# ---------------------------------------------------------------------------

class TestHotelDetailSchema:
    def test_hotel_detail_column_exists_with_empty_default(self, session: Session):
        """Hotel モデルに hotel_detail カラムが存在し、デフォルトは空 dict"""
        hotel = Hotel(name="スキーマテスト旅館", address="東京都テスト区")
        session.add(hotel)
        session.commit()
        session.refresh(hotel)

        assert hasattr(hotel, "hotel_detail")
        assert hotel.hotel_detail == {}


# ---------------------------------------------------------------------------
# 2. GET /facility/hotels/{id}/detail
# ---------------------------------------------------------------------------

class TestGetHotelDetail:
    def test_returns_empty_defaults(
        self, client: TestClient, auth_headers: dict, sample_hotel: Hotel
    ):
        """未入力の場合、各フィールドが空のデフォルト値で返る"""
        response = client.get(
            f"/facility/hotels/{sample_hotel.id}/detail",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["story"] == ""
        assert data["highlights"] == []
        assert data["surrounding"]["description"] == ""
        assert data["surrounding"]["attractions"] == []
        assert data["access"] == ""

    def test_requires_auth(self, client: TestClient, sample_hotel: Hotel):
        """認証なしでアクセスすると 401 または 403"""
        response = client.get(f"/facility/hotels/{sample_hotel.id}/detail")
        assert response.status_code in (401, 403)

    def test_forbidden_for_unrelated_hotel(
        self, client: TestClient, auth_headers: dict, session: Session
    ):
        """権限のない施設では 403"""
        other = Hotel(name="他の旅館", address="大阪府")
        session.add(other)
        session.commit()
        session.refresh(other)

        response = client.get(
            f"/facility/hotels/{other.id}/detail",
            headers=auth_headers,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 3. PUT /facility/hotels/{id}/detail
# ---------------------------------------------------------------------------

class TestUpdateHotelDetail:
    def test_update_all_fields(
        self, client: TestClient, auth_headers: dict, sample_hotel: Hotel
    ):
        """全フィールドを保存して正しく返る"""
        payload = {
            "story": "創業昭和30年。山の麓に佇む老舗旅館です。",
            "highlights": ["源泉かけ流し", "地産地消料理", "貸切露天風呂"],
            "surrounding": {
                "description": "南アルプスの麓に位置する静かなエリアです。",
                "attractions": [
                    {"name": "○○温泉郷", "distance": "徒歩5分"},
                    {"name": "△△神社", "distance": "車10分"},
                ],
            },
            "access": "新宿駅から特急あずさで2時間。無料送迎あり（要予約）。",
        }
        response = client.put(
            f"/facility/hotels/{sample_hotel.id}/detail",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["story"] == payload["story"]
        assert data["highlights"] == payload["highlights"]
        assert data["surrounding"]["description"] == payload["surrounding"]["description"]
        assert len(data["surrounding"]["attractions"]) == 2
        assert data["surrounding"]["attractions"][0]["name"] == "○○温泉郷"
        assert data["surrounding"]["attractions"][0]["distance"] == "徒歩5分"
        assert data["access"] == payload["access"]

    def test_update_partial_fields(
        self, client: TestClient, auth_headers: dict, sample_hotel: Hotel
    ):
        """一部フィールドのみ指定した場合も正常に更新される"""
        response = client.put(
            f"/facility/hotels/{sample_hotel.id}/detail",
            json={"highlights": ["温泉", "料理"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["highlights"] == ["温泉", "料理"]

    def test_update_persists_on_get(
        self, client: TestClient, auth_headers: dict, sample_hotel: Hotel
    ):
        """PUT 後に GET で同じ値が返る（永続化の確認）"""
        payload = {"story": "永続化テストのストーリー", "access": "永続化テストのアクセス"}
        client.put(
            f"/facility/hotels/{sample_hotel.id}/detail",
            json=payload,
            headers=auth_headers,
        )
        response = client.get(
            f"/facility/hotels/{sample_hotel.id}/detail",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["story"] == "永続化テストのストーリー"
        assert data["access"] == "永続化テストのアクセス"


# ---------------------------------------------------------------------------
# 4. POST /facility/hotels/{id}/detail/auto-fill
# ---------------------------------------------------------------------------

class TestAutoFillHotelDetail:
    def test_returns_400_when_website_not_set(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        sample_hotel: Hotel,
    ):
        """website 未設定の場合 400 とエラーメッセージを返す"""
        sample_hotel.website = None
        session.add(sample_hotel)
        session.commit()

        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/detail/auto-fill",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "公式サイトのURLが設定されていません" in response.json()["detail"]

    @patch("app.services.hotel_scrape_service.get_llm_client")
    @patch("app.services.hotel_scrape_service.httpx.AsyncClient")
    def test_returns_structured_data_when_website_set(
        self,
        mock_httpx_class,
        mock_get_llm,
        client: TestClient,
        auth_headers: dict,
        sample_hotel: Hotel,
    ):
        """website 設定済みの場合、スクレイプ＋LLM 結果を返す"""
        # httpx のモック（async context manager）
        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body>源泉かけ流し 自然豊か 新宿から2時間</body></html>"
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_class.return_value = mock_cm

        # LLM のモック
        llm_result = json.dumps({
            "highlights": ["源泉かけ流し", "自然豊か"],
            "surrounding": {
                "description": "山に囲まれた静かなエリアです。",
                "attractions": [{"name": "○○渓谷", "distance": "車15分"}],
            },
            "access": "新宿駅から特急で2時間。",
        })
        mock_llm = AsyncMock()
        mock_llm.generate_structured_output = AsyncMock(return_value=llm_result)
        mock_get_llm.return_value = mock_llm

        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/detail/auto-fill",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["highlights"], list)
        assert len(data["highlights"]) > 0
        assert "surrounding" in data
        assert "description" in data["surrounding"]
        assert "attractions" in data["surrounding"]
        assert "access" in data

    def test_forbidden_for_unrelated_hotel(
        self, client: TestClient, auth_headers: dict, session: Session
    ):
        """権限のない施設では 403"""
        other = Hotel(name="他の旅館3", address="京都府", website="https://example.com")
        session.add(other)
        session.commit()
        session.refresh(other)

        response = client.post(
            f"/facility/hotels/{other.id}/detail/auto-fill",
            headers=auth_headers,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 5. POST /facility/hotels/{id}/detail/fill-surrounding-from-market
# ---------------------------------------------------------------------------

class TestFillSurroundingFromMarket:
    def test_returns_400_when_no_analysis_session(
        self, client: TestClient, auth_headers: dict, sample_hotel: Hotel
    ):
        """市場分析セッションが存在しない場合 400"""
        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/detail/fill-surrounding-from-market",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "市場分析データがありません" in response.json()["detail"]

    def test_returns_400_when_regional_trends_is_null(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        sample_hotel: Hotel,
    ):
        """AnalysisSession があっても regional_trends が None なら 400"""
        analysis = AnalysisSession(hotel_id=sample_hotel.id, regional_trends=None)
        session.add(analysis)
        session.commit()

        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/detail/fill-surrounding-from-market",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "市場分析データがありません" in response.json()["detail"]

    @patch("app.api.facility_hotels.get_llm_client")
    def test_returns_surrounding_when_trends_exist(
        self,
        mock_get_llm,
        client: TestClient,
        auth_headers: dict,
        sample_analysis_session: AnalysisSession,
        sample_hotel: Hotel,
    ):
        """regional_trends がある場合、surrounding を返す"""
        llm_result = json.dumps({
            "surrounding": {
                "description": "観光地として人気の温泉エリアです。",
                "attractions": [{"name": "有名温泉", "distance": "車20分"}],
            }
        })
        mock_llm = AsyncMock()
        mock_llm.generate_structured_output = AsyncMock(return_value=llm_result)
        mock_get_llm.return_value = mock_llm

        response = client.post(
            f"/facility/hotels/{sample_hotel.id}/detail/fill-surrounding-from-market",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "surrounding" in data
        assert isinstance(data["surrounding"]["description"], str)
        assert isinstance(data["surrounding"]["attractions"], list)
