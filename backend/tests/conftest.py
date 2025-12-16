"""
pytest用の共通設定とフィクスチャ
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from typing import Generator

from app.main import app
from app.core.database import get_session
from app.models import Hotel, AnalysisSession, MarketingPlan, CreativeAsset, PlanStatus


# テスト用のインメモリSQLiteデータベース
@pytest.fixture(name="engine")
def engine_fixture():
    """テスト用のデータベースエンジンを作成"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """テスト用のデータベースセッションを作成"""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine) -> Generator[TestClient, None, None]:
    """テスト用のFastAPIクライアントを作成"""
    
    def get_session_override():
        with Session(engine) as session:
            yield session
    
    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


# サンプルデータ用のフィクスチャ
@pytest.fixture(name="sample_hotel")
def sample_hotel_fixture(session: Session) -> Hotel:
    """テスト用のサンプルホテルを作成"""
    hotel = Hotel(
        name="テスト旅館",
        address="東京都渋谷区テスト1-2-3",
        postal_code="150-0001",
        phone="03-1234-5678",
        email="test@example.com",
        website="https://test-ryokan.example.com",
        features={"温泉": "源泉かけ流し", "料理": "和食懐石"},
        strengths={"立地": "駅から徒歩5分", "サービス": "おもてなし"}
    )
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    return hotel


@pytest.fixture(name="sample_analysis_session")
def sample_analysis_session_fixture(session: Session, sample_hotel: Hotel) -> AnalysisSession:
    """テスト用のサンプル分析セッションを作成"""
    analysis_session = AnalysisSession(
        hotel_id=sample_hotel.id,
        csv_statistics={
            "total_records": 100,
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "cancellation_stats": {"cancellation_rate_percent": 15.0}
        },
        csv_insights="テスト用のインサイトです。",
        competitors_list={
            "area_type": "温泉地",
            "estimated_competitors": "10",
            "price_range": {"low": 8000, "average": 15000, "high": 30000}
        },
        reviews_summary={
            "positive_themes": ["温泉が良い", "料理が美味しい"],
            "negative_themes": ["駐車場が狭い"]
        },
        regional_trends="テスト用の地域トレンド分析です。"
    )
    session.add(analysis_session)
    session.commit()
    session.refresh(analysis_session)
    return analysis_session


@pytest.fixture(name="sample_marketing_plan")
def sample_marketing_plan_fixture(session: Session, sample_analysis_session: AnalysisSession) -> MarketingPlan:
    """テスト用のサンプルマーケティングプランを作成"""
    marketing_plan = MarketingPlan(
        analysis_session_id=sample_analysis_session.id,
        status=PlanStatus.draft,
        plan_name="春の温泉プラン",
        concept="春の訪れを感じながら、ゆったりとした時間を過ごす",
        target_audience={
            "age_range": "30-50代",
            "type": "夫婦・カップル",
            "interests": ["温泉", "グルメ", "リラックス"]
        },
        price_range={
            "min": 15000,
            "max": 25000,
            "average": 20000
        },
        benefits={
            "特典1": "ウェルカムドリンク",
            "特典2": "レイトチェックアウト"
        },
        strategy_3c={
            "company": "温泉の質と料理に強み",
            "customer": "リピート率が高い",
            "competitor": "価格競争力あり"
        },
        strategy_pest={
            "political": "観光支援策",
            "economic": "インバウンド需要回復",
            "social": "ワーケーション需要",
            "technological": "オンライン予約増加"
        }
    )
    session.add(marketing_plan)
    session.commit()
    session.refresh(marketing_plan)
    return marketing_plan


@pytest.fixture(name="sample_creative_asset")
def sample_creative_asset_fixture(session: Session, sample_marketing_plan: MarketingPlan) -> CreativeAsset:
    """テスト用のサンプルクリエイティブアセットを作成"""
    creative_asset = CreativeAsset(
        marketing_plan_id=sample_marketing_plan.id,
        lp_source_code="<div>テスト用LP</div>",
        lp_preview_url="https://example.com/preview",
        ad_image_urls={
            "main": "https://example.com/images/main.jpg",
            "sub": "https://example.com/images/sub.jpg"
        },
        ad_copy={
            "headline": "春の温泉旅行",
            "description": "ゆったりとした時間を過ごしませんか"
        },
        generation_prompts={
            "lp_prompt": "テスト用LPプロンプト",
            "image_prompt": "テスト用画像プロンプト"
        }
    )
    session.add(creative_asset)
    session.commit()
    session.refresh(creative_asset)
    return creative_asset


