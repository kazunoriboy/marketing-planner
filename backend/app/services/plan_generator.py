import json
import re
from typing import List, Dict
from app.models import AnalysisSession


class PlanGenerator:
    """マーケティングプラン生成サービス"""
    
    def __init__(self):
        pass
    
    async def generate_plans(
        self,
        analysis_session: AnalysisSession,
        num_plans: int,
        llm_client
    ) -> List[Dict]:
        """
        分析結果からマーケティングプランを生成
        
        Args:
            analysis_session: 分析セッション
            num_plans: 生成するプラン数
            llm_client: LLMクライアント
        
        Returns:
            プラン情報のリスト
        """
        # 分析結果をまとめる
        analysis_summary = self._create_analysis_summary(analysis_session)
        
        # プラン生成プロンプトを作成
        prompt = self._create_plan_generation_prompt(analysis_summary, num_plans)
        
        # LLMでプランを生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_system_prompt(),
            max_tokens=8000
        )
        
        # JSONをパース
        plans = self._parse_plans_response(response)
        
        return plans
    
    def _create_analysis_summary(self, session: AnalysisSession) -> str:
        """分析結果をサマリー化"""
        summary_parts = []
        
        # CSV分析結果
        if session.csv_statistics:
            summary_parts.append("【顧客データ分析】")
            summary_parts.append(json.dumps(session.csv_statistics, ensure_ascii=False, indent=2))
            if session.csv_insights:
                summary_parts.append(f"\nインサイト: {session.csv_insights}")
        
        # 市場調査結果
        if session.competitors_list:
            summary_parts.append("\n【競合分析】")
            summary_parts.append(json.dumps(session.competitors_list, ensure_ascii=False, indent=2))
        
        if session.reviews_summary:
            summary_parts.append("\n【口コミ分析】")
            summary_parts.append(json.dumps(session.reviews_summary, ensure_ascii=False, indent=2))
        
        if session.regional_trends:
            summary_parts.append("\n【地域トレンド】")
            summary_parts.append(session.regional_trends)
        
        return "\n".join(summary_parts)
    
    def _create_plan_generation_prompt(self, analysis_summary: str, num_plans: int) -> str:
        """プラン生成プロンプトを作成"""
        return f"""
以下の分析結果に基づいて、{num_plans}つの具体的なマーケティングプランを提案してください。

{analysis_summary}

各プランについて、以下の項目を含むJSON形式で出力してください：

{{
    "plans": [
        {{
            "plan_name": "プラン名",
            "concept": "プランのコンセプト（200文字程度）",
            "target_audience": {{
                "age_range": "対象年齢層",
                "demographics": "デモグラフィック特性",
                "psychographics": "サイコグラフィック特性",
                "needs": ["ニーズ1", "ニーズ2"]
            }},
            "price_range": {{
                "min": 最低価格,
                "max": 最高価格,
                "recommended": 推奨価格,
                "rationale": "価格設定の根拠"
            }},
            "benefits": {{
                "main_benefits": ["特典1", "特典2", "特典3"],
                "unique_value": "独自の価値提案",
                "amenities": ["アメニティ1", "アメニティ2"]
            }},
            "strategy_3c": {{
                "customer": "顧客分析",
                "competitor": "競合分析",
                "company": "自社の強み"
            }},
            "strategy_pest": {{
                "political": "政治的要因",
                "economic": "経済的要因",
                "social": "社会的要因",
                "technological": "技術的要因"
            }}
        }}
    ]
}}

各プランは差別化され、異なるターゲット層や戦略を持つようにしてください。
"""
    
    def _get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは宿泊業界の経験豊富なマーケティングストラテジストです。
データに基づいた実践的で、すぐに実行可能なマーケティングプランを提案してください。
3C分析（Customer, Competitor, Company）とPEST分析（Political, Economic, Social, Technological）を
活用した戦略的なプランを作成してください。"""
    
    def _parse_plans_response(self, response: str) -> List[Dict]:
        """LLMのレスポンスからプラン情報を抽出"""
        try:
            # JSONを抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            plans = data.get("plans", [])
            
            # プランのバリデーション
            validated_plans = []
            for plan in plans:
                if self._validate_plan(plan):
                    validated_plans.append(plan)
            
            return validated_plans
        
        except Exception as e:
            print(f"プラン解析エラー: {e}")
            # デフォルトプランを返す
            return self._get_default_plans()
    
    def _validate_plan(self, plan: Dict) -> bool:
        """プランデータの妥当性を検証"""
        required_fields = [
            "plan_name",
            "concept",
            "target_audience",
            "price_range",
            "benefits",
            "strategy_3c",
            "strategy_pest"
        ]
        
        return all(field in plan for field in required_fields)
    
    def _get_default_plans(self) -> List[Dict]:
        """デフォルトプラン（エラー時のフォールバック）"""
        return [
            {
                "plan_name": "ベーシックプラン",
                "concept": "標準的な宿泊プランです。データ分析に基づいた価格設定で提供します。",
                "target_audience": {
                    "age_range": "30-50代",
                    "demographics": "ビジネス・観光客",
                    "psychographics": "価格重視",
                    "needs": ["快適な宿泊", "利便性"]
                },
                "price_range": {
                    "min": 8000,
                    "max": 15000,
                    "recommended": 10000,
                    "rationale": "市場平均価格"
                },
                "benefits": {
                    "main_benefits": ["朝食付き", "Wi-Fi無料", "駐車場無料"],
                    "unique_value": "コストパフォーマンス",
                    "amenities": ["基本アメニティ完備"]
                },
                "strategy_3c": {
                    "customer": "価格重視の顧客層",
                    "competitor": "同価格帯との競争",
                    "company": "立地と価格の優位性"
                },
                "strategy_pest": {
                    "political": "観光促進政策の活用",
                    "economic": "中価格帯の需要",
                    "social": "快適性重視トレンド",
                    "technological": "オンライン予約システム"
                }
            }
        ]


