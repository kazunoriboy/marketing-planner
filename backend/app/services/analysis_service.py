"""
顧客分析サービス - Gemini 2.5 Flash-Lite版

CSVファイルから顧客データを分析し、AIによるインサイトを生成します。
"""

import pandas as pd
import json
from typing import Dict, Optional, Tuple
import re

from app.core.llm import get_llm_client
from app.services.base_csv_service import BaseCSVService


class AnalysisService(BaseCSVService):
    """
    顧客分析サービス（Gemini 2.5 Flash-Lite使用）
    
    BaseCSVServiceを継承し、CSV処理の共通機能を利用
    """
    
    def __init__(self):
        super().__init__()
        self.model_name = "gemini-2.5-flash-lite"
    
    # エンコーディング判別とCSV読み込みはBaseCSVServiceから継承
    async def infer_csv_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        AIによるCSVスキーマの推定（Smart Schema Inference）
        
        Args:
            df: pandasデータフレーム
        
        Returns:
            カラム名のマッピング辞書
        """
        # ヘッダーとサンプルデータを取得
        columns = df.columns.tolist()
        sample_rows = df.head(10).to_dict('records')
        
        # AIプロンプトを構築
        system_prompt = """あなたは宿泊予約データ分析の専門家です。
提示されたCSVデータから、以下の情報を表すカラム名を特定し、正確なJSON形式で返してください。

- booking_date (予約日・予約受付日・登録日・受信日など、予約が入った日)
- stay_date (宿泊日・チェックイン日・利用日・開始日など、実際に宿泊する日)
- plan_name (プラン名・企画名・商品名など)
- total_price (合計金額・請求金額・料金・ポイント割引後額・支払額など、実際の支払い金額)
- num_guests (宿泊人数・利用人数・人数・大人人数など)
- status (予約ステータス・区分・状態など - 「予約」「取消」「キャンセル」などの値を含むカラム)
- guest_area (予約者の住所・都道府県・居住地域・発信地など - 「東京都」「大阪府」「関東」「九州」などのエリア情報)

【重要な判断基準】
- booking_dateは「受信日」「登録日」「予約日」「受付日」などを優先
- stay_dateは「チェックイン」「宿泊日」「利用日」「開始日付」などを優先
- total_priceは「ポイント割引後額」「請求金額」「支払額」など実際の金額を優先
- statusは「区分」「予約状態」「ステータス」などで、値に「取消」「キャンセル」「予約」「確定」等が含まれるものを選ぶ

※データの中身（日付フォーマットや値の傾向）から文脈を読んで判断すること。
該当するカラムがない場合は null を返してください。"""
        
        user_prompt = f"""以下のCSVデータを解析してください。

【カラム名】
{columns}

【サンプルデータ（先頭10行）】
{json.dumps(sample_rows, ensure_ascii=False, indent=2, default=str)}

出力形式（必ず以下のJSON形式で返してください）:
{{
  "booking_date": "該当するカラム名またはnull",
  "stay_date": "該当するカラム名またはnull",
  "plan_name": "該当するカラム名またはnull",
  "total_price": "該当するカラム名またはnull",
  "num_guests": "該当するカラム名またはnull",
  "status": "該当するカラム名またはnull",
  "guest_area": "該当するカラム名またはnull"
}}"""
        
        # Gemini 2.5 Flash-Liteでスキーマを推定
        llm_client = get_llm_client(model_name=self.model_name)
        response = await llm_client.generate_structured_output(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1024
        )
        
        # JSONをパース
        try:
            # マークダウンのコードブロックを除去
            json_text = re.sub(r'```json\s*', '', response)
            json_text = re.sub(r'```\s*', '', json_text)
            
            # JSON部分を抽出
            json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
            if json_match:
                schema_map = json.loads(json_match.group())
            else:
                schema_map = json.loads(json_text)
            
            return schema_map
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"スキーマ推定エラー: {e}")
            logger.debug(f"LLMレスポンス: {response}")
            # デフォルトマッピング
            return {
                "booking_date": None,
                "stay_date": None,
                "plan_name": None,
                "total_price": None,
                "num_guests": None,
                "status": None,
                "guest_area": None
            }
    
    # JSON変換はBaseCSVServiceから継承
    def calculate_statistics(
        self,
        df: pd.DataFrame,
        schema_map: Dict[str, Optional[str]]
    ) -> Dict:
        """
        データ正規化と統計計算（pandas使用）
        
        Args:
            df: pandasデータフレーム
            schema_map: スキーママッピング
        
        Returns:
            統計情報辞書
        """
        stats = {
            "total_records": int(len(df)),
            "schema_mapping": schema_map,
            "date_range": {},
            "cancellation_stats": {},
            "average_lead_time": None,
            "top_plans": {},
            "weekday_occupancy": {},
            "guest_stats": {},
            "price_stats": {},
            "guest_area_stats": {}  # 予約者の居住エリア統計
        }
        
        try:
            df_work = df.copy()
            
            # === 日付変換ヘルパー関数 ===
            def convert_date_column(series: pd.Series) -> pd.Series:
                """
                様々な日付フォーマットに対応した日付変換
                - 通常の日付文字列（2024-01-01, 2024/01/01, 01-01-2024等）
                - YYYYMMDD形式（20240101）
                - YYYYMMDD HH:MM:SS形式（20240101 12:30:45）
                - Excelシリアル値（45292 = 2024-01-01）
                - Unixタイムスタンプ（秒/ミリ秒）
                """
                # サンプル値を取得して形式を判別
                sample_values = series.dropna().head(5).astype(str).tolist()
                total_count = len(series.dropna())
                
                if not sample_values or total_count == 0:
                    return pd.to_datetime(series, errors='coerce')
                
                # まずYYYYMMDD形式かどうかをチェック（8桁の数字）
                # これを先にチェックしないと、pd.to_datetimeが誤って変換してしまう
                if re.match(r'^\d{8}$', sample_values[0].strip()):
                    return pd.to_datetime(series.astype(str).str.strip(), format='%Y%m%d', errors='coerce')
                
                # YYYYMMDD HH:MM:SS形式のチェック
                if re.match(r'^\d{8}\s+\d{1,2}:\d{2}:\d{2}', sample_values[0].strip()):
                    return pd.to_datetime(series.astype(str).str.strip(), format='%Y%m%d %H:%M:%S', errors='coerce')
                
                # 通常の日付変換を試みる
                result = pd.to_datetime(series, errors='coerce')
                
                # 変換成功率と日付の妥当性をチェック
                valid_count = result.notna().sum()
                
                # 変換された日付が妥当な範囲（1990年〜2100年）かチェック
                if valid_count > 0:
                    valid_dates = result.dropna()
                    min_year = valid_dates.dt.year.min()
                    max_year = valid_dates.dt.year.max()
                    
                    # 1970年付近の日付が多い場合は変換が間違っている可能性
                    dates_in_1970 = ((valid_dates.dt.year >= 1969) & (valid_dates.dt.year <= 1971)).sum()
                    if dates_in_1970 / len(valid_dates) > 0.5:
                        # 大半が1970年付近 = 変換が間違っている
                        valid_count = 0  # 他の形式を試す
                    elif min_year < 1990 or max_year > 2100:
                        # 日付が異常な範囲 = 変換が間違っている可能性
                        valid_count = 0
                
                if total_count > 0 and valid_count / total_count < 0.5:
                    # 50%以上が変換失敗した場合、他の形式を試す
                    
                    # 数値に変換できるかチェック
                    numeric_series = pd.to_numeric(series, errors='coerce')
                    numeric_valid = numeric_series.notna().sum()
                    
                    if numeric_valid / total_count > 0.5:
                        # 数値として有効な場合
                        sample_value = numeric_series.dropna().iloc[0] if len(numeric_series.dropna()) > 0 else 0
                        
                        if 20000101 <= sample_value <= 20991231:
                            # YYYYMMDD形式の数値（20240101）
                            result = pd.to_datetime(numeric_series.astype(int).astype(str), format='%Y%m%d', errors='coerce')
                        elif 40000 < sample_value < 60000:
                            # Excelシリアル値の可能性（40000=2009年、60000=2064年）
                            # Excelの基準日は1899-12-30
                            result = pd.to_datetime(numeric_series, unit='D', origin='1899-12-30', errors='coerce')
                        elif 1000000000 < sample_value < 2000000000:
                            # Unixタイムスタンプ（秒）の可能性
                            result = pd.to_datetime(numeric_series, unit='s', errors='coerce')
                        elif 1000000000000 < sample_value < 2000000000000:
                            # Unixタイムスタンプ（ミリ秒）の可能性
                            result = pd.to_datetime(numeric_series, unit='ms', errors='coerce')
                
                return result
            
            # === 日付変換 ===
            booking_col = schema_map.get("booking_date")
            stay_col = schema_map.get("stay_date")
            
            if booking_col and booking_col in df_work.columns:
                df_work[booking_col] = convert_date_column(df_work[booking_col])
            
            if stay_col and stay_col in df_work.columns:
                df_work[stay_col] = convert_date_column(df_work[stay_col])
                # 有効な日付のみで範囲を計算
                valid_dates = df_work[stay_col].dropna()
                if len(valid_dates) > 0:
                    stats["date_range"] = {
                        "start": valid_dates.min().isoformat() if pd.notna(valid_dates.min()) else None,
                        "end": valid_dates.max().isoformat() if pd.notna(valid_dates.max()) else None
                    }
            
            # === キャンセル率計算 ===
            status_col = schema_map.get("status")
            if status_col and status_col in df_work.columns:
                # キャンセルを示すキーワード（様々な表現に対応）
                # 部分一致で検索するパターン
                cancel_patterns = [
                    # 日本語（ひらがな・カタカナ・漢字）
                    'キャンセル', 'ｷｬﾝｾﾙ', 'きゃんせる',
                    '取消', '取り消し', '取りけし',
                    '無効', '中止', '削除',
                    # 英語（大文字・小文字両方）
                    'cancel', 'cancelled', 'canceled', 'cancellation',
                    # 略語・記号
                    'CXL', 'CX',
                ]
                
                # 完全一致で検索する値（ステータスが単一の値の場合）
                exact_cancel_values = [
                    'キャンセル', '取消', '取り消し', 'cancel', 'cancelled', 'canceled',
                    'CANCEL', 'CANCELLED', 'CANCELED', 'CXL', 'CX', '無効', '中止',
                    '×', '✕', 'X',
                ]
                
                status_values = df_work[status_col].astype(str).str.strip()
                
                # 完全一致チェック
                is_exact_match = status_values.str.lower().isin([v.lower() for v in exact_cancel_values])
                
                # 部分一致チェック（より広い検出）
                is_partial_match = status_values.str.contains(
                    '|'.join(cancel_patterns),
                    case=False,
                    na=False,
                    regex=True
                )
                
                # 完全一致または部分一致でキャンセル判定
                df_work['is_cancelled'] = is_exact_match | is_partial_match
                
                total_count = len(df_work)
                cancelled_count = df_work['is_cancelled'].sum()
                cancellation_rate = (cancelled_count / total_count * 100) if total_count > 0 else 0
                
                stats["cancellation_stats"] = {
                    "total_bookings": int(total_count),
                    "cancelled_bookings": int(cancelled_count),
                    "cancellation_rate_percent": round(cancellation_rate, 2)
                }
                
                # 直前キャンセル率（宿泊日の7日前以降のキャンセル）
                if booking_col and stay_col and booking_col in df_work.columns and stay_col in df_work.columns:
                    df_work['days_before_stay'] = (df_work[stay_col] - df_work[booking_col]).dt.days
                    last_minute_cancelled = df_work[
                        (df_work['is_cancelled']) & (df_work['days_before_stay'] <= 7)
                    ]
                    last_minute_rate = (len(last_minute_cancelled) / cancelled_count * 100) if cancelled_count > 0 else 0
                    stats["cancellation_stats"]["last_minute_cancellation_rate_percent"] = round(last_minute_rate, 2)
            
            # === 平均リードタイム ===
            if booking_col and stay_col and booking_col in df_work.columns and stay_col in df_work.columns:
                df_work['lead_time'] = (df_work[stay_col] - df_work[booking_col]).dt.days
                avg_lead_time = df_work['lead_time'].mean()
                stats["average_lead_time"] = round(avg_lead_time, 1) if pd.notna(avg_lead_time) else None
            
            # === キャンセルを除いた予約データを作成 ===
            # キャンセルフラグが設定されている場合、キャンセル以外の予約のみを抽出
            if 'is_cancelled' in df_work.columns:
                df_confirmed = df_work[~df_work['is_cancelled']].copy()
                confirmed_bookings_count = len(df_confirmed)
            else:
                df_confirmed = df_work.copy()
                confirmed_bookings_count = len(df_work)
            
            # === プラン別予約数Top5（キャンセルを除く） ===
            plan_col = schema_map.get("plan_name")
            if plan_col and plan_col in df_confirmed.columns:
                top_plans = df_confirmed[plan_col].value_counts().head(5).to_dict()
                stats["top_plans"] = {str(k): int(v) for k, v in top_plans.items()}
            
            # === 曜日別稼働率（キャンセルを除く） ===
            if stay_col and stay_col in df_confirmed.columns:
                df_confirmed['weekday'] = df_confirmed[stay_col].dt.day_name()
                weekday_counts = df_confirmed['weekday'].value_counts().to_dict()
                stats["weekday_occupancy"] = {str(k): int(v) for k, v in weekday_counts.items()}
            
            # === 宿泊人数統計（キャンセルを除く） ===
            guests_col = schema_map.get("num_guests")
            if guests_col and guests_col in df_confirmed.columns:
                df_confirmed[guests_col] = pd.to_numeric(df_confirmed[guests_col], errors='coerce')
                valid_guests = df_confirmed[df_confirmed[guests_col] > 0][guests_col]
                
                if len(valid_guests) > 0:
                    # 人数分布を計算（1人、2人、3人、4人、5人以上）
                    guest_distribution = {}
                    for n in [1, 2, 3, 4]:
                        count = len(valid_guests[valid_guests == n])
                        if count > 0:
                            guest_distribution[f"{n}人"] = int(count)
                    count_5_plus = len(valid_guests[valid_guests >= 5])
                    if count_5_plus > 0:
                        guest_distribution["5人以上"] = int(count_5_plus)
                    
                    stats["guest_stats"] = {
                        "average": round(valid_guests.mean(), 1) if pd.notna(valid_guests.mean()) else None,
                        "min": int(valid_guests.min()) if pd.notna(valid_guests.min()) else None,
                        "max": int(valid_guests.max()) if pd.notna(valid_guests.max()) else None,
                        "total_guests": int(valid_guests.sum()),
                        "distribution": guest_distribution,
                        "note": "キャンセルを除く確定予約のみ"
                    }
            
            # === 価格統計（キャンセルを除く、宿泊人数あたり単価） ===
            price_col = schema_map.get("total_price")
            if price_col and price_col in df_confirmed.columns:
                # 価格の文字列クリーニング（カンマ、円マーク、¥マークを除去）
                def clean_price(value):
                    if pd.isna(value):
                        return None
                    str_val = str(value).strip()
                    # 空文字列チェック
                    if not str_val:
                        return None
                    # 円マーク、¥マーク、カンマ、スペースを除去
                    str_val = re.sub(r'[¥￥円,、\s]', '', str_val)
                    # 数値以外の文字が残っている場合はNone
                    if not str_val or not re.match(r'^-?\d+\.?\d*$', str_val):
                        return None
                    return float(str_val)
                
                df_confirmed['_cleaned_price'] = df_confirmed[price_col].apply(clean_price)
                df_confirmed['_cleaned_price'] = pd.to_numeric(df_confirmed['_cleaned_price'], errors='coerce')
                # 0以下の値を除外
                valid_prices = df_confirmed[df_confirmed['_cleaned_price'] > 0]['_cleaned_price']
                
                if len(valid_prices) > 0:
                    # 基本の価格統計（合計金額）
                    stats["price_stats"] = {
                        "total_average": round(valid_prices.mean(), 0) if pd.notna(valid_prices.mean()) else None,
                        "total_min": round(valid_prices.min(), 0) if pd.notna(valid_prices.min()) else None,
                        "total_max": round(valid_prices.max(), 0) if pd.notna(valid_prices.max()) else None,
                        "total_median": round(valid_prices.median(), 0) if pd.notna(valid_prices.median()) else None,
                        "valid_count": int(len(valid_prices)),
                        "excluded_count": int(len(df_confirmed) - len(valid_prices)),
                        "note": "キャンセルを除く確定予約のみ"
                    }
                    
                    # 宿泊人数あたりの単価を計算
                    if guests_col and guests_col in df_confirmed.columns:
                        # 価格と人数の両方が有効なデータのみ抽出
                        valid_data = df_confirmed[(df_confirmed['_cleaned_price'] > 0) & (df_confirmed[guests_col] > 0)].copy()
                        if len(valid_data) > 0:
                            valid_data['price_per_guest'] = valid_data['_cleaned_price'] / valid_data[guests_col]
                            price_per_guest = valid_data['price_per_guest']
                            
                            stats["price_stats"]["per_guest_average"] = round(price_per_guest.mean(), 0) if pd.notna(price_per_guest.mean()) else None
                            stats["price_stats"]["per_guest_min"] = round(price_per_guest.min(), 0) if pd.notna(price_per_guest.min()) else None
                            stats["price_stats"]["per_guest_max"] = round(price_per_guest.max(), 0) if pd.notna(price_per_guest.max()) else None
                            stats["price_stats"]["per_guest_median"] = round(price_per_guest.median(), 0) if pd.notna(price_per_guest.median()) else None
            
            # === 予約者居住エリア統計（キャンセルを除く） ===
            area_col = schema_map.get("guest_area")
            if area_col and area_col in df_confirmed.columns:
                # 空白やNaNを除外して集計
                valid_areas = df_confirmed[df_confirmed[area_col].notna() & (df_confirmed[area_col].astype(str).str.strip() != '')]
                
                if len(valid_areas) > 0:
                    # 全エリア数
                    total_areas = valid_areas[area_col].nunique()
                    
                    # 地方別集計（都道府県を地方に変換）
                    region_mapping = {
                        '北海道': '北海道',
                        '青森県': '東北', '岩手県': '東北', '宮城県': '東北', '秋田県': '東北', '山形県': '東北', '福島県': '東北',
                        '茨城県': '関東', '栃木県': '関東', '群馬県': '関東', '埼玉県': '関東', '千葉県': '関東', '東京都': '関東', '神奈川県': '関東',
                        '新潟県': '中部', '富山県': '中部', '石川県': '中部', '福井県': '中部', '山梨県': '中部', '長野県': '中部', '岐阜県': '中部', '静岡県': '中部', '愛知県': '中部',
                        '三重県': '近畿', '滋賀県': '近畿', '京都府': '近畿', '大阪府': '近畿', '兵庫県': '近畿', '奈良県': '近畿', '和歌山県': '近畿',
                        '鳥取県': '中国', '島根県': '中国', '岡山県': '中国', '広島県': '中国', '山口県': '中国',
                        '徳島県': '四国', '香川県': '四国', '愛媛県': '四国', '高知県': '四国',
                        '福岡県': '九州', '佐賀県': '九州', '長崎県': '九州', '熊本県': '九州', '大分県': '九州', '宮崎県': '九州', '鹿児島県': '九州', '沖縄県': '九州'
                    }
                    
                    # 海外の国名パターン（よく使われる表記）
                    overseas_country_patterns = {
                        # アジア
                        '中国': '中国', 'china': '中国', '台湾': '台湾', 'taiwan': '台湾',
                        '韓国': '韓国', 'korea': '韓国', '香港': '香港', 'hongkong': '香港', 'hong kong': '香港',
                        'シンガポール': 'シンガポール', 'singapore': 'シンガポール',
                        'タイ': 'タイ', 'thailand': 'タイ', 'マレーシア': 'マレーシア', 'malaysia': 'マレーシア',
                        'インドネシア': 'インドネシア', 'indonesia': 'インドネシア',
                        'ベトナム': 'ベトナム', 'vietnam': 'ベトナム', 'フィリピン': 'フィリピン', 'philippines': 'フィリピン',
                        'インド': 'インド', 'india': 'インド',
                        # 北米
                        'アメリカ': 'アメリカ', 'america': 'アメリカ', 'usa': 'アメリカ', 'united states': 'アメリカ', '米国': 'アメリカ',
                        'カナダ': 'カナダ', 'canada': 'カナダ',
                        # 欧州
                        'イギリス': 'イギリス', 'uk': 'イギリス', 'england': 'イギリス', 'britain': 'イギリス', '英国': 'イギリス',
                        'フランス': 'フランス', 'france': 'フランス', 'ドイツ': 'ドイツ', 'germany': 'ドイツ',
                        'イタリア': 'イタリア', 'italy': 'イタリア', 'スペイン': 'スペイン', 'spain': 'スペイン',
                        'オランダ': 'オランダ', 'netherlands': 'オランダ', 'スイス': 'スイス', 'switzerland': 'スイス',
                        # オセアニア
                        'オーストラリア': 'オーストラリア', 'australia': 'オーストラリア', '豪州': 'オーストラリア',
                        'ニュージーランド': 'ニュージーランド', 'new zealand': 'ニュージーランド',
                    }
                    
                    # 都道府県から地方を抽出（部分一致で対応）、海外は国名を返す
                    def get_region_or_country(area_str):
                        area_str = str(area_str).strip()
                        area_lower = area_str.lower()
                        
                        # 日本の都道府県をチェック
                        for pref, region in region_mapping.items():
                            if pref in area_str:
                                return ('domestic', region)
                        
                        # 海外の国名をチェック
                        for pattern, country in overseas_country_patterns.items():
                            if pattern in area_lower or pattern in area_str:
                                return ('overseas', country)
                        
                        # どちらにも該当しない場合
                        return ('unknown', area_str)
                    
                    # 都道府県を抽出する関数
                    def extract_prefecture(area_str):
                        """エリア文字列から都道府県名を抽出"""
                        area_str = str(area_str).strip()
                        for pref in region_mapping.keys():
                            if pref in area_str:
                                return pref
                        return None
                    
                    valid_areas_copy = valid_areas.copy()
                    valid_areas_copy['area_type'], valid_areas_copy['region_or_country'] = zip(
                        *valid_areas_copy[area_col].apply(get_region_or_country)
                    )
                    
                    # 国内の地方別分布
                    domestic_data = valid_areas_copy[valid_areas_copy['area_type'] == 'domestic']
                    region_counts = domestic_data['region_or_country'].value_counts().to_dict()
                    region_distribution = {str(k): int(v) for k, v in region_counts.items()}
                    
                    # 国内の都道府県別分布を追加
                    domestic_data_copy = domestic_data.copy()
                    domestic_data_copy['prefecture'] = domestic_data_copy[area_col].apply(extract_prefecture)
                    prefecture_counts = domestic_data_copy['prefecture'].value_counts().to_dict()
                    prefecture_distribution = {str(k): int(v) for k, v in prefecture_counts.items() if k is not None}
                    
                    # 海外の国別分布
                    overseas_data = valid_areas_copy[valid_areas_copy['area_type'] == 'overseas']
                    country_counts = overseas_data['region_or_country'].value_counts().to_dict()
                    overseas_distribution = {str(k): int(v) for k, v in country_counts.items()}
                    
                    # 不明（国内でも海外でもないもの）の件数
                    unknown_count = len(valid_areas_copy[valid_areas_copy['area_type'] == 'unknown'])
                    
                    stats["guest_area_stats"] = {
                        "total_unique_areas": int(total_areas),
                        "total_records_with_area": int(len(valid_areas)),
                        "domestic_count": int(len(domestic_data)),
                        "overseas_count": int(len(overseas_data)),
                        "region_distribution": region_distribution,
                        "prefecture_distribution": prefecture_distribution,  # 都道府県別を追加
                        "overseas_distribution": overseas_distribution,
                        "note": "キャンセルを除く確定予約のみ"
                    }
                    
                    # 不明が多い場合は含める
                    if unknown_count > 0 and unknown_count > len(valid_areas) * 0.05:  # 5%以上の場合
                        stats["guest_area_stats"]["unknown_count"] = int(unknown_count)
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"統計計算エラー: {e}", exc_info=True)
        
        # すべての値をJSON serializable に変換
        stats = self._convert_to_json_serializable(stats)
        
        return stats
    
    async def generate_marketing_insights(self, stats: Dict) -> str:
        """
        AIマーケティングインサイト生成
        
        Args:
            stats: 統計情報辞書
        
        Returns:
            マーケティングインサイト（300文字程度）
        """
        system_prompt = """あなたは宿泊施設のマーケティング戦略コンサルタントです。
データ分析結果から実践的なインサイトを導き出し、具体的なアクションプランを提案してください。

以下の観点を含めてください：
1. ターゲット層の特徴
2. 現状の課題（キャンセル率、リードタイムなど）
3. 推奨アクション（具体的な施策）
"""
        
        user_prompt = f"""以下の顧客データ分析結果から、マーケティング施策に活かせるインサイトを300文字程度で生成してください。

【分析結果】
{json.dumps(stats, ensure_ascii=False, indent=2, default=str)}

具体的で実践的な提案をお願いします。"""
        
        # Gemini 2.5 Flash-Liteでインサイトを生成
        llm_client = get_llm_client(model_name=self.model_name)
        insights = await llm_client.generate_text(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.7
        )
        
        return insights
    
    async def analyze_csv(
        self,
        file_content: bytes
    ) -> Tuple[Dict, str]:
        """
        CSV分析の一気通貫実行
        
        Args:
            file_content: CSVファイルの内容（バイト列）
        
        Returns:
            (統計情報, インサイト) のタプル
        """
        # 1. CSVを読み込み（エンコーディング自動判別）
        df = self._load_csv(file_content)
        
        # 2. スキーマを推定（AI）
        schema_map = await self.infer_csv_schema(df)
        
        # 3. 統計を計算（pandas）
        statistics = self.calculate_statistics(df, schema_map)
        
        # 4. インサイトを生成（AI）
        insights = await self.generate_marketing_insights(statistics)
        
        return statistics, insights

