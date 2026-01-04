"""
ペルソナ機能のテスト

テスト対象:
- ペルソナ生成API
- ペルソナ取得API
- ペルソナ修正API
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch, AsyncMock

from app.models import Hotel, AnalysisSession, FacilityAdmin, FacilityAdminHotel, FacilityAdminHotelRole
from app.auth.password import hash_password


# ============================================
# フィクスチャ
# ============================================

@pytest.fixture(name="facility_admin_with_hotel")
def facility_admin_with_hotel_fixture(session: Session, sample_hotel: Hotel):
    """施設管理者と施設の紐付けを作成"""
    # 施設管理者を作成
    admin = FacilityAdmin(
        email="test@facility.com",
        password_hash=hash_password("testpassword"),
        name="テスト施設管理者",
        is_active=True
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    
    # 施設との紐付けを作成
    permission = FacilityAdminHotel(
        facility_admin_id=admin.id,
        hotel_id=sample_hotel.id,
        role=FacilityAdminHotelRole.owner
    )
    session.add(permission)
    session.commit()
    
    return admin


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, facility_admin_with_hotel: FacilityAdmin):
    """認証済みヘッダーを取得"""
    response = client.post(
        "/facility/auth/login",
        json={"email": "test@facility.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================
# ペルソナ取得テスト
# ============================================

def test_get_personas_empty(
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    sample_analysis_session: AnalysisSession
):
    """ペルソナが空の状態で取得"""
    response = client.get(
        f"/api/analysis/hotels/{sample_hotel.id}/personas",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sample_analysis_session.id
    assert data["personas"] == []


def test_get_personas_with_data(
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    session: Session
):
    """ペルソナがある状態で取得"""
    # ペルソナ付きの分析セッションを作成
    analysis_session = AnalysisSession(
        hotel_id=sample_hotel.id,
        csv_statistics={"total_records": 100},
        personas=[
            {
                "name": "田中花子",
                "age_range": "30代",
                "gender": "女性",
                "location": "東京都",
                "occupation": "会社員",
                "travel_purpose": "リフレッシュ",
                "values": ["温泉"],
                "budget_range": "2万円",
                "information_source": ["じゃらん"],
                "needs": ["清潔感"],
                "pain_points": ["忙しい"],
                "description": "テスト"
            }
        ]
    )
    session.add(analysis_session)
    session.commit()
    session.refresh(analysis_session)
    
    response = client.get(
        f"/api/analysis/hotels/{sample_hotel.id}/personas",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["personas"]) == 1
    assert data["personas"][0]["name"] == "田中花子"
    assert data["personas"][0]["location"] == "東京都"


# ============================================
# ペルソナ生成テスト
# ============================================

def test_generate_personas_no_analysis_data(
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel
):
    """分析データがない状態でペルソナ生成を試みる"""
    response = client.post(
        f"/api/analysis/hotels/{sample_hotel.id}/personas/generate",
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "分析データがありません" in response.json()["detail"]


@patch("app.api.analysis._generate_personas_with_llm")
def test_generate_personas_success(
    mock_generate: AsyncMock,
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    sample_analysis_session: AnalysisSession
):
    """ペルソナ生成成功"""
    # モックのレスポンスを設定
    mock_generate.return_value = [
        {
            "name": "田中花子",
            "age_range": "30代後半",
            "gender": "女性",
            "location": "東京都世田谷区",
            "occupation": "会社員",
            "travel_purpose": "リフレッシュ",
            "values": ["温泉", "美食"],
            "budget_range": "2万〜3万円",
            "information_source": ["じゃらん", "Instagram"],
            "needs": ["清潔感", "おもてなし"],
            "pain_points": ["平日は忙しい"],
            "description": "テストペルソナ"
        },
        {
            "name": "佐藤太郎",
            "age_range": "50代",
            "gender": "男性",
            "location": "神奈川県横浜市",
            "occupation": "会社役員",
            "travel_purpose": "夫婦旅行",
            "values": ["静けさ", "上質"],
            "budget_range": "3万〜5万円",
            "information_source": ["楽天トラベル"],
            "needs": ["プライベート感"],
            "pain_points": ["混雑を避けたい"],
            "description": "テストペルソナ2"
        },
        {
            "name": "山田美咲",
            "age_range": "20代後半",
            "gender": "女性",
            "location": "埼玉県さいたま市",
            "occupation": "看護師",
            "travel_purpose": "女子旅",
            "values": ["コスパ", "SNS映え"],
            "budget_range": "1万〜1.5万円",
            "information_source": ["Instagram", "TikTok"],
            "needs": ["フォトスポット"],
            "pain_points": ["シフト制"],
            "description": "テストペルソナ3"
        }
    ]
    
    response = client.post(
        f"/api/analysis/hotels/{sample_hotel.id}/personas/generate?num_personas=3",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["personas"]) == 3
    assert data["personas"][0]["name"] == "田中花子"
    assert data["personas"][0]["location"] == "東京都世田谷区"
    assert "generated_at" in data


# ============================================
# ペルソナ修正テスト
# ============================================

def test_edit_persona_not_found(
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    sample_analysis_session: AnalysisSession
):
    """存在しないペルソナを修正しようとする"""
    response = client.put(
        f"/api/analysis/hotels/{sample_hotel.id}/personas/0",
        headers=auth_headers,
        json={"persona_index": 0, "instruction": "若くして"}
    )
    assert response.status_code == 404
    assert "ペルソナが見つかりません" in response.json()["detail"]


def test_edit_persona_invalid_index(
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    session: Session
):
    """無効なインデックスでペルソナを修正しようとする"""
    # ペルソナ付きの分析セッションを作成
    analysis_session = AnalysisSession(
        hotel_id=sample_hotel.id,
        csv_statistics={"total_records": 100},
        personas=[
            {
                "name": "田中花子",
                "age_range": "30代",
                "gender": "女性",
                "location": "東京都",
                "occupation": "会社員",
                "travel_purpose": "リフレッシュ",
                "values": ["温泉"],
                "budget_range": "2万円",
                "information_source": ["じゃらん"],
                "needs": ["清潔感"],
                "pain_points": ["忙しい"],
                "description": "テスト"
            }
        ]
    )
    session.add(analysis_session)
    session.commit()
    
    response = client.put(
        f"/api/analysis/hotels/{sample_hotel.id}/personas/5",
        headers=auth_headers,
        json={"persona_index": 5, "instruction": "若くして"}
    )
    assert response.status_code == 400
    assert "インデックスが不正" in response.json()["detail"]


@patch("app.api.analysis._edit_persona_with_llm")
def test_edit_persona_success(
    mock_edit: AsyncMock,
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    session: Session
):
    """ペルソナ修正成功"""
    # ペルソナ付きの分析セッションを作成
    analysis_session = AnalysisSession(
        hotel_id=sample_hotel.id,
        csv_statistics={"total_records": 100},
        personas=[
            {
                "name": "田中花子",
                "age_range": "30代後半",
                "gender": "女性",
                "location": "東京都",
                "occupation": "会社員",
                "travel_purpose": "リフレッシュ",
                "values": ["温泉"],
                "budget_range": "2万円",
                "information_source": ["じゃらん"],
                "needs": ["清潔感"],
                "pain_points": ["忙しい"],
                "description": "テスト"
            }
        ]
    )
    session.add(analysis_session)
    session.commit()
    
    # モックのレスポンスを設定（年齢を変更）
    mock_edit.return_value = {
        "name": "田中花子",
        "age_range": "20代前半",
        "gender": "女性",
        "location": "東京都",
        "occupation": "大学生",
        "travel_purpose": "女子旅",
        "values": ["SNS映え", "コスパ"],
        "budget_range": "1万円",
        "information_source": ["Instagram"],
        "needs": ["フォトスポット"],
        "pain_points": ["予算が限られている"],
        "description": "若い世代に変更されたペルソナ"
    }
    
    response = client.put(
        f"/api/analysis/hotels/{sample_hotel.id}/personas/0",
        headers=auth_headers,
        json={"persona_index": 0, "instruction": "もっと若い世代（20代前半の大学生）にしてほしい"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["persona"]["age_range"] == "20代前半"
    assert data["persona"]["occupation"] == "大学生"
    assert data["persona_index"] == 0


# ============================================
# 統合テスト
# ============================================

def test_persona_lifecycle(
    client: TestClient,
    auth_headers: dict,
    sample_hotel: Hotel,
    sample_analysis_session: AnalysisSession
):
    """ペルソナのライフサイクル（取得→生成確認）"""
    # 1. 初期状態でペルソナを取得（空であることを確認）
    response = client.get(
        f"/api/analysis/hotels/{sample_hotel.id}/personas",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["personas"] == []
    
    # 2. 分析セッションが存在することを確認
    response = client.get(
        f"/api/analysis/hotels/{sample_hotel.id}/session",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["session_id"] is not None


# ============================================
# スキーマバリデーションテスト
# ============================================

def test_persona_schema():
    """Personaスキーマのバリデーション"""
    from app.schemas.analysis import Persona
    
    # 正常なデータ
    valid_persona = Persona(
        name="田中花子",
        age_range="30代",
        gender="女性",
        location="東京都世田谷区",
        occupation="会社員",
        travel_purpose="リフレッシュ",
        values=["温泉", "美食"],
        budget_range="2万円",
        information_source=["じゃらん"],
        needs=["清潔感"],
        pain_points=["忙しい"],
        description="テスト"
    )
    assert valid_persona.name == "田中花子"
    assert valid_persona.location == "東京都世田谷区"


def test_persona_edit_request_schema():
    """PersonaEditRequestスキーマのバリデーション"""
    from app.schemas.analysis import PersonaEditRequest
    
    # 正常なリクエスト
    request = PersonaEditRequest(
        persona_index=0,
        instruction="もっと若くしてほしい"
    )
    assert request.persona_index == 0
    assert request.instruction == "もっと若くしてほしい"

