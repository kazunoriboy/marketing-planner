import pandas as pd
import json
from typing import Dict, Optional, Tuple
from io import BytesIO
from datetime import datetime
import re


class CSVAnalyzer:
    """CSV分析サービス"""
    
    def __init__(self):
        pass
    
    async def detect_schema(self, df: pd.DataFrame, llm_client) -> Dict[str, Optional[str]]:
        """
        LLMを使用してCSVスキーマを推定
        
        Args:
            df: pandasデータフレーム
            llm_client: LLMクライアント
        
        Returns:
            カラム名のマッピング辞書
        """
        columns = df.columns.tolist()
        sample_data = df.head(3).to_dict('records')
        
        prompt = f"""
以下のCSVファイルのカラム情報とサンプルデータから、各カラムの役割を特定してください。

カラム名: {columns}

サンプルデータ:
{json.dumps(sample_data, ensure_ascii=False, indent=2)}

以下の項目に該当するカラム名を特定し、JSON形式で返してください：
- reservation_date: 予約日
- checkin_date: 宿泊日（チェックイン日）
- plan_name: プラン名
- is_cancelled: キャンセルフラグ（True/False または 1/0 など）
- guest_age: 宿泊者の年齢
- num_guests: 宿泊人数
- total_price: 合計金額

該当するカラムがない場合はnullを返してください。

出力形式:
{{
    "reservation_date": "カラム名またはnull",
    "checkin_date": "カラム名またはnull",
    "plan_name": "カラム名またはnull",
    "is_cancelled": "カラム名またはnull",
    "guest_age": "カラム名またはnull",
    "num_guests": "カラム名またはnull",
    "total_price": "カラム名またはnull"
}}
"""
        
        system_prompt = "あなたはデータ分析の専門家です。CSVファイルのスキーマを正確に解析してください。"
        
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt
        )
        
        # JSONをパース
        try:
            # レスポンスからJSONを抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                schema_mapping = json.loads(json_match.group())
            else:
                schema_mapping = json.loads(response)
            return schema_mapping
        except Exception as e:
            print(f"スキーマ解析エラー: {e}")
            # デフォルトのマッピングを返す
            return {
                "reservation_date": None,
                "checkin_date": None,
                "plan_name": None,
                "is_cancelled": None,
                "guest_age": None,
                "num_guests": None,
                "total_price": None
            }
    
    def calculate_statistics(
        self,
        df: pd.DataFrame,
        schema_mapping: Dict[str, Optional[str]]
    ) -> Dict:
        """
        統計情報を計算
        
        Args:
            df: pandasデータフレーム
            schema_mapping: カラム名マッピング
        
        Returns:
            統計情報の辞書
        """
        stats = {
            "total_records": len(df),
            "date_range": {},
            "cancellation_rate": None,
            "average_lead_time": None,
            "age_distribution": {},
            "popular_plans": {},
            "average_price": None
        }
        
        try:
            # 日付範囲
            if schema_mapping.get("checkin_date") and schema_mapping["checkin_date"] in df.columns:
                checkin_col = schema_mapping["checkin_date"]
                df[checkin_col] = pd.to_datetime(df[checkin_col], errors='coerce')
                stats["date_range"] = {
                    "start": df[checkin_col].min().isoformat() if pd.notna(df[checkin_col].min()) else None,
                    "end": df[checkin_col].max().isoformat() if pd.notna(df[checkin_col].max()) else None
                }
            
            # キャンセル率
            if schema_mapping.get("is_cancelled") and schema_mapping["is_cancelled"] in df.columns:
                cancel_col = schema_mapping["is_cancelled"]
                # キャンセルフラグを正規化
                df[cancel_col] = df[cancel_col].apply(
                    lambda x: True if x in [True, 1, "1", "true", "True", "yes", "Yes"] else False
                )
                cancellation_rate = df[cancel_col].sum() / len(df) * 100
                stats["cancellation_rate"] = round(cancellation_rate, 2)
            
            # リードタイム（予約日から宿泊日までの日数）
            if (schema_mapping.get("reservation_date") and 
                schema_mapping.get("checkin_date") and
                schema_mapping["reservation_date"] in df.columns and
                schema_mapping["checkin_date"] in df.columns):
                
                reserve_col = schema_mapping["reservation_date"]
                checkin_col = schema_mapping["checkin_date"]
                
                df[reserve_col] = pd.to_datetime(df[reserve_col], errors='coerce')
                df[checkin_col] = pd.to_datetime(df[checkin_col], errors='coerce')
                
                df['lead_time'] = (df[checkin_col] - df[reserve_col]).dt.days
                avg_lead_time = df['lead_time'].mean()
                stats["average_lead_time"] = round(avg_lead_time, 1) if pd.notna(avg_lead_time) else None
            
            # 年齢分布
            if schema_mapping.get("guest_age") and schema_mapping["guest_age"] in df.columns:
                age_col = schema_mapping["guest_age"]
                df[age_col] = pd.to_numeric(df[age_col], errors='coerce')
                
                # 年齢層に分類
                age_bins = [0, 20, 30, 40, 50, 60, 100]
                age_labels = ["~20代", "30代", "40代", "50代", "60代", "70代~"]
                df['age_group'] = pd.cut(df[age_col], bins=age_bins, labels=age_labels, right=False)
                
                age_dist = df['age_group'].value_counts().to_dict()
                stats["age_distribution"] = {str(k): int(v) for k, v in age_dist.items() if pd.notna(k)}
            
            # 人気プラン
            if schema_mapping.get("plan_name") and schema_mapping["plan_name"] in df.columns:
                plan_col = schema_mapping["plan_name"]
                plan_counts = df[plan_col].value_counts().head(10).to_dict()
                stats["popular_plans"] = {str(k): int(v) for k, v in plan_counts.items()}
            
            # 平均価格
            if schema_mapping.get("total_price") and schema_mapping["total_price"] in df.columns:
                price_col = schema_mapping["total_price"]
                df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
                avg_price = df[price_col].mean()
                stats["average_price"] = round(avg_price, 0) if pd.notna(avg_price) else None
        
        except Exception as e:
            print(f"統計計算エラー: {e}")
        
        return stats
    
    async def generate_insights(self, statistics: Dict, llm_client) -> str:
        """
        統計情報からインサイトを生成
        
        Args:
            statistics: 統計情報
            llm_client: LLMクライアント
        
        Returns:
            インサイト文章
        """
        prompt = f"""
以下の宿泊施設の顧客データ分析結果から、マーケティング施策に活かせるインサイトを日本語で生成してください。

【分析結果】
{json.dumps(statistics, ensure_ascii=False, indent=2)}

以下の観点から分析してください：
1. 顧客の予約行動パターン（リードタイムなど）
2. キャンセル傾向と対策
3. 人気プランの特徴
4. ターゲット層の特定
5. 価格設定の妥当性

具体的なマーケティング提案を含めて、800文字程度でまとめてください。
"""
        
        system_prompt = """あなたは宿泊業界に精通したマーケティングアナリストです。
データから実践的なインサイトを導き出し、具体的な施策を提案してください。"""
        
        insights = await llm_client.generate_text(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        return insights
    
    async def analyze_csv(
        self,
        file_content: bytes,
        llm_client
    ) -> Tuple[Dict, str]:
        """
        CSVファイルを分析
        
        Args:
            file_content: CSVファイルの内容
            llm_client: LLMクライアント
        
        Returns:
            (統計情報, インサイト文章) のタプル
        """
        # CSVを読み込み
        df = pd.read_csv(BytesIO(file_content))
        
        # スキーマを推定
        schema_mapping = await self.detect_schema(df, llm_client)
        
        # 統計を計算
        statistics = self.calculate_statistics(df, schema_mapping)
        statistics["schema_mapping"] = schema_mapping
        
        # インサイトを生成
        insights = await self.generate_insights(statistics, llm_client)
        
        return statistics, insights


