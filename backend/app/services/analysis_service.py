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

- booking_date (予約日)
- stay_date (宿泊日)
- plan_name (プラン名)
- total_price (合計金額)
- status (予約ステータス - キャンセル判定用)

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
  "status": "該当するカラム名またはnull"
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
            print(f"スキーマ推定エラー: {e}")
            print(f"LLMレスポンス: {response}")
            # デフォルトマッピング
            return {
                "booking_date": None,
                "stay_date": None,
                "plan_name": None,
                "total_price": None,
                "status": None
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
            "price_stats": {}
        }
        
        try:
            df_work = df.copy()
            
            # === 日付変換 ===
            booking_col = schema_map.get("booking_date")
            stay_col = schema_map.get("stay_date")
            
            if booking_col and booking_col in df_work.columns:
                df_work[booking_col] = pd.to_datetime(df_work[booking_col], errors='coerce')
            
            if stay_col and stay_col in df_work.columns:
                df_work[stay_col] = pd.to_datetime(df_work[stay_col], errors='coerce')
                stats["date_range"] = {
                    "start": df_work[stay_col].min().isoformat() if pd.notna(df_work[stay_col].min()) else None,
                    "end": df_work[stay_col].max().isoformat() if pd.notna(df_work[stay_col].max()) else None
                }
            
            # === キャンセル率計算 ===
            status_col = schema_map.get("status")
            if status_col and status_col in df_work.columns:
                # キャンセルを示すキーワード
                cancel_keywords = ['キャンセル', 'cancel', 'cancelled', 'canceled', '取消']
                df_work['is_cancelled'] = df_work[status_col].astype(str).str.contains(
                    '|'.join(cancel_keywords),
                    case=False,
                    na=False
                )
                
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
            
            # === プラン別予約数Top5 ===
            plan_col = schema_map.get("plan_name")
            if plan_col and plan_col in df_work.columns:
                top_plans = df_work[plan_col].value_counts().head(5).to_dict()
                stats["top_plans"] = {str(k): int(v) for k, v in top_plans.items()}
            
            # === 曜日別稼働率 ===
            if stay_col and stay_col in df_work.columns:
                df_work['weekday'] = df_work[stay_col].dt.day_name()
                weekday_counts = df_work['weekday'].value_counts().to_dict()
                stats["weekday_occupancy"] = {str(k): int(v) for k, v in weekday_counts.items()}
            
            # === 価格統計 ===
            price_col = schema_map.get("total_price")
            if price_col and price_col in df_work.columns:
                df_work[price_col] = pd.to_numeric(df_work[price_col], errors='coerce')
                stats["price_stats"] = {
                    "average": round(df_work[price_col].mean(), 0) if pd.notna(df_work[price_col].mean()) else None,
                    "min": round(df_work[price_col].min(), 0) if pd.notna(df_work[price_col].min()) else None,
                    "max": round(df_work[price_col].max(), 0) if pd.notna(df_work[price_col].max()) else None,
                    "median": round(df_work[price_col].median(), 0) if pd.notna(df_work[price_col].median()) else None
                }
        
        except Exception as e:
            print(f"統計計算エラー: {e}")
        
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

