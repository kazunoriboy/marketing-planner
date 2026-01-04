"""
顧客分析機能のテストスクリプト

使用方法:
1. バックエンドを起動: docker compose up -d
2. テストを実行: docker compose exec backend python tests/test_analysis.py
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import random

from app.services.analysis_service import AnalysisService


def create_sample_csv() -> bytes:
    """テスト用のサンプルCSVデータを生成"""
    
    # サンプルデータを作成
    data = []
    base_date = datetime(2024, 1, 1)
    
    plans = [
        "素泊まりプラン",
        "朝食付きプラン",
        "夕朝食付きプラン",
        "特別ディナーコース",
        "ファミリープラン"
    ]
    
    statuses = ["確定", "確定", "確定", "確定", "キャンセル"]  # 20%キャンセル率
    
    # 予約者エリア（都道府県）
    prefectures = [
        "東京都", "東京都", "東京都",  # 多め
        "神奈川県", "神奈川県",
        "埼玉県", "千葉県",
        "大阪府", "京都府",
        "愛知県", "福岡県", "北海道"
    ]
    
    for i in range(100):
        # 宿泊日
        stay_date = base_date + timedelta(days=random.randint(0, 365))
        # 予約日（宿泊日の7〜60日前）
        booking_date = stay_date - timedelta(days=random.randint(7, 60))
        
        record = {
            "予約ID": f"B{i+1:04d}",
            "予約日": booking_date.strftime("%Y/%m/%d"),
            "宿泊日": stay_date.strftime("%Y/%m/%d"),
            "プラン名": random.choice(plans),
            "合計金額": random.randint(5000, 50000),
            "ステータス": random.choice(statuses),
            "宿泊人数": random.randint(1, 4),
            "都道府県": random.choice(prefectures)  # 予約者エリアを追加
        }
        data.append(record)
    
    # DataFrameを作成
    df = pd.DataFrame(data)
    
    # CSV文字列に変換
    csv_string = df.to_csv(index=False, encoding='utf-8')
    
    return csv_string.encode('utf-8')


async def test_analysis_service():
    """AnalysisServiceのテスト"""
    
    print("=" * 60)
    print("顧客分析機能テスト - Gemini 2.5 Flash-Lite版")
    print("=" * 60)
    print()
    
    # サンプルCSVを生成
    print("1. サンプルCSVデータを生成中...")
    csv_content = create_sample_csv()
    print(f"   ✓ {len(csv_content)} バイトのCSVデータを生成しました")
    print()
    
    # AnalysisServiceを初期化
    print("2. AnalysisServiceを初期化中...")
    service = AnalysisService()
    print(f"   ✓ 使用モデル: {service.model_name}")
    print()
    
    # エンコーディング検出のテスト
    print("3. エンコーディングを検出中...")
    encoding = service._detect_encoding(csv_content)
    print(f"   ✓ 検出されたエンコーディング: {encoding}")
    print()
    
    # CSVの読み込み
    print("4. CSVを読み込み中...")
    df = service._load_csv(csv_content)
    print(f"   ✓ {len(df)} 件のレコードを読み込みました")
    print(f"   ✓ カラム: {list(df.columns)}")
    print()
    
    # スキーマ推定（AI）
    print("5. AIによるスキーマ推定中...")
    print("   （Gemini 2.5 Flash-Liteで処理中...）")
    schema_map = await service.infer_csv_schema(df)
    print("   ✓ スキーママッピング:")
    for key, value in schema_map.items():
        print(f"     - {key}: {value}")
    print()
    
    # 統計計算
    print("6. 統計情報を計算中...")
    statistics = service.calculate_statistics(df, schema_map)
    print("   ✓ 統計情報:")
    print(f"     - 総レコード数: {statistics['total_records']}")
    
    if statistics.get('date_range'):
        print(f"     - 期間: {statistics['date_range'].get('start')} 〜 {statistics['date_range'].get('end')}")
    
    if statistics.get('cancellation_stats'):
        cs = statistics['cancellation_stats']
        print(f"     - キャンセル率: {cs.get('cancellation_rate_percent')}%")
        if cs.get('last_minute_cancellation_rate_percent'):
            print(f"     - 直前キャンセル率: {cs.get('last_minute_cancellation_rate_percent')}%")
    
    if statistics.get('average_lead_time'):
        print(f"     - 平均リードタイム: {statistics['average_lead_time']} 日")
    
    if statistics.get('top_plans'):
        print(f"     - 人気プランTop3:")
        for i, (plan, count) in enumerate(list(statistics['top_plans'].items())[:3], 1):
            print(f"       {i}. {plan}: {count}件")
    
    if statistics.get('guest_stats'):
        gs = statistics['guest_stats']
        print(f"     - 宿泊人数統計:")
        print(f"       - 平均: {gs.get('average')} 人")
        print(f"       - 総人数: {gs.get('total_guests'):,} 人")
        if gs.get('distribution'):
            print(f"       - 分布: {gs.get('distribution')}")
    
    if statistics.get('price_stats'):
        ps = statistics['price_stats']
        print(f"     - 価格統計:")
        if ps.get('per_guest_average'):
            print(f"       - 1人あたり平均: ¥{ps.get('per_guest_average'):,.0f}")
            print(f"       - 1人あたり中央値: ¥{ps.get('per_guest_median'):,.0f}")
        print(f"       - 合計金額平均: ¥{ps.get('total_average'):,.0f}")
        print(f"       - 合計金額最小: ¥{ps.get('total_min'):,.0f}")
        print(f"       - 合計金額最大: ¥{ps.get('total_max'):,.0f}")
    
    if statistics.get('guest_area_stats'):
        gas = statistics['guest_area_stats']
        print(f"     - 予約者エリア統計:")
        if gas.get('region_distribution'):
            print(f"       - 地方別分布:")
            for region, count in gas['region_distribution'].items():
                print(f"         - {region}: {count}件")
        if gas.get('top_areas'):
            print(f"       - エリア別Top5:")
            for i, (area, count) in enumerate(list(gas['top_areas'].items())[:5], 1):
                print(f"         {i}. {area}: {count}件")
        if gas.get('total_unique_areas'):
            print(f"       - ユニークエリア数: {gas['total_unique_areas']}")
    print()
    
    # AIインサイト生成
    print("7. AIマーケティングインサイトを生成中...")
    print("   （Gemini 2.5 Flash-Liteで処理中...）")
    insights = await service.generate_marketing_insights(statistics)
    print("   ✓ インサイト:")
    print()
    print("-" * 60)
    print(insights)
    print("-" * 60)
    print()
    
    # 一気通貫テスト
    print("8. 一気通貫分析テスト...")
    print("   （エンコーディング判別 → スキーマ推定 → 統計計算 → インサイト生成）")
    stats, insights_full = await service.analyze_csv(csv_content)
    print(f"   ✓ 完了！")
    print()
    
    print("=" * 60)
    print("テスト完了！")
    print("=" * 60)


# Shift_JISエンコーディングのテスト
def create_sample_csv_shift_jis() -> bytes:
    """Shift_JISエンコーディングのサンプルCSVを生成"""
    
    data = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(20):
        stay_date = base_date + timedelta(days=random.randint(0, 30))
        booking_date = stay_date - timedelta(days=random.randint(7, 30))
        
        record = {
            "予約番号": f"R{i+1:04d}",
            "予約受付日": booking_date.strftime("%Y/%m/%d"),
            "チェックイン日": stay_date.strftime("%Y/%m/%d"),
            "プラン": "温泉付き宿泊プラン",
            "料金": random.randint(8000, 30000),
            "状態": "予約確定" if random.random() > 0.2 else "キャンセル"
        }
        data.append(record)
    
    df = pd.DataFrame(data)
    csv_string = df.to_csv(index=False, encoding='shift_jis')
    
    return csv_string.encode('shift_jis')


async def test_shift_jis_encoding():
    """Shift_JISエンコーディングのテスト"""
    
    print()
    print("=" * 60)
    print("Shift_JISエンコーディングテスト")
    print("=" * 60)
    print()
    
    # Shift_JIS CSVを生成
    print("1. Shift_JIS形式のCSVを生成中...")
    csv_content = create_sample_csv_shift_jis()
    print(f"   ✓ {len(csv_content)} バイトのShift_JIS CSVを生成しました")
    print()
    
    # 分析実行
    service = AnalysisService()
    
    print("2. エンコーディング自動判別中...")
    encoding = service._detect_encoding(csv_content)
    print(f"   ✓ 検出されたエンコーディング: {encoding}")
    print()
    
    print("3. CSVを読み込み中...")
    df = service._load_csv(csv_content)
    print(f"   ✓ {len(df)} 件のレコードを読み込みました")
    print(f"   ✓ カラム: {list(df.columns)}")
    print()
    
    print("4. スキーマ推定 & 統計計算...")
    statistics, insights = await service.analyze_csv(csv_content)
    print(f"   ✓ 完了！総レコード数: {statistics['total_records']}")
    print()
    
    print("=" * 60)
    print("Shift_JISテスト完了！")
    print("=" * 60)


if __name__ == "__main__":
    # メインテスト
    asyncio.run(test_analysis_service())
    
    # Shift_JISテスト
    asyncio.run(test_shift_jis_encoding())

