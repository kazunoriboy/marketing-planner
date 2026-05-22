"""
宿・周辺情報の単体テスト

- リクエストモデル（HotelDetailUpdateRequest）のバリデーション
- LP生成プロンプトへの hotel_detail 組み込み
"""

import pytest
from pydantic import ValidationError

from app.api.facility_hotels import HotelDetailUpdateRequest
from app.models import MarketingPlan, PlanStatus
from app.services.creative_generator import CreativeGenerator


def _make_plan() -> MarketingPlan:
    """DB 不要な最小 MarketingPlan オブジェクト（プロンプト生成テスト用）"""
    return MarketingPlan(
        id=1,
        analysis_session_id=1,
        status=PlanStatus.draft,
        plan_name="テストプラン",
        concept="テストコンセプト",
        target_audience={},
        price_range={},
        benefits={},
        strategy_3c={},
        strategy_pest={},
    )


class TestHotelDetailUpdateRequest:
    """HotelDetailUpdateRequest の単体テスト"""

    def test_accepts_full_payload(self):
        request = HotelDetailUpdateRequest(
            story="創業昭和30年。山の麓に佇む老舗旅館です。",
            highlights=["源泉かけ流し", "地産地消料理", "貸切露天風呂"],
            surrounding={
                "description": "南アルプスの麓に位置する静かなエリアです。",
                "attractions": [
                    {"name": "○○温泉郷", "distance": "徒歩5分"},
                    {"name": "△△神社", "distance": "車10分"},
                ],
            },
            access="新宿駅から特急あずさで2時間。無料送迎あり（要予約）。",
        )

        assert request.story == "創業昭和30年。山の麓に佇む老舗旅館です。"
        assert request.highlights == ["源泉かけ流し", "地産地消料理", "貸切露天風呂"]
        assert request.surrounding is not None
        assert request.surrounding.description == "南アルプスの麓に位置する静かなエリアです。"
        assert len(request.surrounding.attractions) == 2
        assert request.surrounding.attractions[0].name == "○○温泉郷"
        assert request.surrounding.attractions[0].distance == "徒歩5分"
        assert request.access == "新宿駅から特急あずさで2時間。無料送迎あり（要予約）。"

    def test_accepts_partial_payload(self):
        request = HotelDetailUpdateRequest(highlights=["温泉", "料理"])
        assert request.story is None
        assert request.highlights == ["温泉", "料理"]
        assert request.surrounding is None
        assert request.access is None

    def test_rejects_invalid_highlights_type(self):
        with pytest.raises(ValidationError):
            HotelDetailUpdateRequest(highlights="温泉")


class TestLpPromptIncludesHotelDetail:
    """
    _create_lp_generation_prompt() に hotel_detail を渡したとき、
    各フィールドの内容がプロンプト文字列に含まれることを確認。
    （LLM 呼び出しなし・純粋なユニットテスト）
    """

    def test_story_appears_in_prompt(self):
        generator = CreativeGenerator()
        prompt = generator._create_lp_generation_prompt(
            plan=_make_plan(),
            hotel_detail={"story": "創業昭和30年の老舗旅館", "highlights": [], "surrounding": {}, "access": ""},
        )
        assert "創業昭和30年の老舗旅館" in prompt

    def test_highlights_appear_in_prompt(self):
        generator = CreativeGenerator()
        prompt = generator._create_lp_generation_prompt(
            plan=_make_plan(),
            hotel_detail={"story": "", "highlights": ["源泉かけ流し", "地産地消料理"], "surrounding": {}, "access": ""},
        )
        assert "源泉かけ流し" in prompt
        assert "地産地消料理" in prompt

    def test_surrounding_description_appears_in_prompt(self):
        generator = CreativeGenerator()
        prompt = generator._create_lp_generation_prompt(
            plan=_make_plan(),
            hotel_detail={
                "story": "",
                "highlights": [],
                "surrounding": {
                    "description": "南アルプスの麓のエリア",
                    "attractions": [],
                },
                "access": "",
            },
        )
        assert "南アルプスの麓のエリア" in prompt

    def test_attractions_appear_in_prompt(self):
        generator = CreativeGenerator()
        prompt = generator._create_lp_generation_prompt(
            plan=_make_plan(),
            hotel_detail={
                "story": "",
                "highlights": [],
                "surrounding": {
                    "description": "",
                    "attractions": [{"name": "○○温泉郷", "distance": "徒歩5分"}],
                },
                "access": "",
            },
        )
        assert "○○温泉郷" in prompt
        assert "徒歩5分" in prompt

    def test_access_appears_in_prompt(self):
        generator = CreativeGenerator()
        prompt = generator._create_lp_generation_prompt(
            plan=_make_plan(),
            hotel_detail={"story": "", "highlights": [], "surrounding": {}, "access": "新宿駅から特急で2時間"},
        )
        assert "新宿駅から特急で2時間" in prompt

    def test_empty_hotel_detail_adds_no_section(self):
        """hotel_detail が空・None の場合、宿情報セクションがプロンプトに含まれない"""
        generator = CreativeGenerator()
        for hotel_detail in ({}, None):
            prompt = generator._create_lp_generation_prompt(
                plan=_make_plan(),
                hotel_detail=hotel_detail,
            )
            assert "【宿のストーリー" not in prompt
            assert "【宿のハイライト】" not in prompt
