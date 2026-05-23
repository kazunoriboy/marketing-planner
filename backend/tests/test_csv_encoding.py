"""Shift_JIS CSV のエンコーディング判別・スキーマ推定の回帰テスト"""

import asyncio

import pandas as pd
import pytest

from app.services.analysis_service import AnalysisService
from app.services.base_csv_service import BaseCSVService


def _build_shift_jis_reservation_csv() -> bytes:
    df = pd.DataFrame([
        {
            "予約ID": 1,
            "予約区分": "予約",
            "チェックイン日": "2026/06/01",
            "申込日": "2026/05/01",
            "商品プラン名称": "【通年】スタンダードプラン",
            "部屋タイプ名称": "和洋室【禁煙】(1~3名)",
            "大人人数計": 2,
            "料金合計額": 43000,
            "住所1": "兵庫県芦屋市",
        },
        {
            "予約ID": 2,
            "予約区分": "キャンセル",
            "チェックイン日": "2026/07/01",
            "申込日": "2026/05/02",
            "商品プラン名称": "【通年】スタンダードプラン",
            "部屋タイプ名称": "和室１０畳【禁煙】(1~4名)",
            "大人人数計": 3,
            "料金合計額": 53000,
            "住所1": "大阪府大阪市",
        },
    ])
    return df.to_csv(index=False).encode("cp932")


def test_shift_jis_csv_is_not_decoded_as_utf8_ignore():
    content = _build_shift_jis_reservation_csv()
    service = BaseCSVService()
    df = service._load_csv(content)

    assert "予約区分" in df.columns
    assert "商品プラン名称" in df.columns
    assert df.loc[0, "商品プラン名称"] == "【通年】スタンダードプラン"
    assert df.loc[0, "部屋タイプ名称"] == "和洋室【禁煙】(1~3名)"


@pytest.mark.asyncio
async def test_rule_based_schema_and_cancellation_for_shift_jis_csv():
    content = _build_shift_jis_reservation_csv()
    service = AnalysisService()
    df = service._load_csv(content)
    schema = await service.infer_csv_schema(df)
    stats = service.calculate_statistics(df, schema)

    assert schema["status"] == "予約区分"
    assert schema["plan_name"] == "商品プラン名称"
    assert stats["cancellation_stats"]["cancelled_bookings"] == 1
    assert "【通年】スタンダードプラン" in stats["top_plans"]
