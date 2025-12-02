import pandas as pd
import json
import chardet
from typing import Dict, Optional, Tuple
from io import BytesIO, StringIO
from datetime import datetime
import re


class CSVAnalyzer:
    """CSV分析サービス（Gemini 2.5 Flash-Lite対応）"""
    
    def __init__(self):
        self.model_name = "gemini-2.5-flash-lite"
    
    def _detect_encoding(self, file_content: bytes) -> str:
        """
        CSVファイルのエンコーディングを自動判別
        
        Args:
            file_content: ファイルの内容（バイト列）
        
        Returns:
            検出されたエンコーディング名
        """
        # chardetで検出を試みる
        detected = chardet.detect(file_content)
        encoding = detected.get('encoding', 'utf-8')
        
        # よくあるエンコーディングの優先順位リスト
        encodings_to_try = [
            encoding,  # 検出されたもの
            'utf-8',
            'shift_jis',
            'cp932',  # Windows版Shift_JIS
            'euc-jp',
            'iso-2022-jp'
        ]
        
        # 重複を除去
        encodings_to_try = list(dict.fromkeys(encodings_to_try))
        
        # 各エンコーディングで読み込みを試行
        for enc in encodings_to_try:
            try:
                file_content.decode(enc)
                return enc
            except (UnicodeDecodeError, AttributeError):
                continue
        
        # すべて失敗した場合はutf-8をデフォルトで返す
        return 'utf-8'
    
    def _load_csv_from_bytes(self, file_content: bytes) -> pd.DataFrame:
        """
        CSVファイルを読み込み（エンコーディング自動判別）
        
        Args:
            file_content: ファイルの内容（バイト列）
        
        Returns:
            pandasデータフレーム
        """
        # エンコーディングを検出
        encoding = self._detect_encoding(file_content)
        
        try:
            # 検出したエンコーディングで読み込み
            text_content = file_content.decode(encoding)
            df = pd.read_csv(StringIO(text_content))
            return df
        except Exception as e:
            # 失敗した場合、utf-8でリトライ（エラー無視）
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                df = pd.read_csv(StringIO(text_content))
                return df
            except Exception as e2:
                raise ValueError(f"CSVファイルの読み込みに失敗しました: {str(e2)}")
    
    async def detect_schema(self, df: pd.DataFrame, llm_client) -> Dict[str, Optional[str]]:
        """
        Gemini 2.5 Flash-Liteを使用してCSVスキーマを推定
        
        Args:
            df: pandasデータフレーム
            llm_client: LLMクライアント
        
        Returns:
            カラム名のマッピング辞書
        """
        columns = df.columns.tolist()
        sample_data = df.head(10).to_dict('records')
        
        system_prompt = """あなたは宿泊予約データ分析の専門家です。
提示されたCSVデータから、以下の情報を表すカラム名を特定し、正確なJSON形式で返してください。

- reservation_date (予約日)
- checkin_date (宿泊日・チェックイン日)
- plan_name (プラン名)
- total_price (合計金額)
- is_cancelled (キャンセルフラグまたはステータス)
- guest_age (宿泊者の年齢)
- num_guests (宿泊人数)

※データの中身（日付フォーマットや値の傾向）から文脈を読んで判断すること。
該当するカラムがない場合は null を返してください。"""
        
        user_prompt = f"""以下のCSVデータを解析してください。

【カラム名】
{columns}

【サンプルデータ（先頭10行）】
{json.dumps(sample_data, ensure_ascii=False, indent=2, default=str)}

出力形式（必ず以下のJSON形式で返してください）:
{{
    "reservation_date": "カラム名またはnull",
    "checkin_date": "カラム名またはnull",
    "plan_name": "カラム名またはnull",
    "is_cancelled": "カラム名またはnull",
    "guest_age": "カラム名またはnull",
    "num_guests": "カラム名またはnull",
    "total_price": "カラム名またはnull"
}}"""
        
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
            
            # レスポンスからJSONを抽出
            json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
            if json_match:
                schema_mapping = json.loads(json_match.group())
            else:
                schema_mapping = json.loads(json_text)
            return schema_mapping
        except Exception as e:
            print(f"スキーマ解析エラー: {e}")
            print(f"LLMレスポンス: {response}")
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
        統計情報からインサイトを生成（Gemini 2.5 Flash-Lite使用）
        
        Args:
            statistics: 統計情報
            llm_client: LLMクライアント
        
        Returns:
            インサイト文章
        """
        system_prompt = """あなたは宿泊業界に精通したマーケティングアナリストです。
データから実践的なインサイトを導き出し、具体的な施策を提案してください。

以下の観点を含めてください：
1. ターゲット層の特徴
2. 現状の課題（キャンセル率、リードタイムなど）
3. 推奨アクション（具体的なマーケティング施策）
"""
        
        user_prompt = f"""以下の宿泊施設の顧客データ分析結果から、マーケティング施策に活かせるインサイトを300文字程度で生成してください。

【分析結果】
{json.dumps(statistics, ensure_ascii=False, indent=2, default=str)}

具体的で実践的な提案をお願いします。"""
        
        insights = await llm_client.generate_text(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.7
        )
        
        return insights
    
    async def analyze_csv(
        self,
        file_content: bytes,
        llm_client
    ) -> Tuple[Dict, str]:
        """
        CSVファイルを分析（エンコーディング自動判別対応）
        
        Args:
            file_content: CSVファイルの内容（バイト列）
            llm_client: LLMクライアント
        
        Returns:
            (統計情報, インサイト文章) のタプル
        """
        # CSVを読み込み（エンコーディング自動判別）
        df = self._load_csv_from_bytes(file_content)
        
        # スキーマを推定（Gemini 2.5 Flash-Lite使用）
        schema_mapping = await self.detect_schema(df, llm_client)
        
        # 統計を計算
        statistics = self.calculate_statistics(df, schema_mapping)
        statistics["schema_mapping"] = schema_mapping
        
        # インサイトを生成（Gemini 2.5 Flash-Lite使用）
        insights = await self.generate_insights(statistics, llm_client)
        
        return statistics, insights


