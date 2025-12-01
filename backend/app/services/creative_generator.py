import json
import re
from typing import Dict, Optional, Tuple
from app.models import MarketingPlan


class CreativeGenerator:
    """クリエイティブアセット生成サービス"""
    
    def __init__(self):
        pass
    
    async def generate_landing_page(
        self,
        marketing_plan: MarketingPlan,
        llm_client
    ) -> Tuple[str, str]:
        """
        ランディングページのコードを生成
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
        
        Returns:
            (ソースコード, 生成プロンプト) のタプル
        """
        prompt = self._create_lp_generation_prompt(marketing_plan)
        
        system_prompt = """あなたは経験豊富なフロントエンドエンジニアです。
React + TypeScript + Tailwind CSSを使用して、モダンで美しいランディングページを作成してください。
コンポーネントは完全に動作し、すぐに使用できる状態で提供してください。"""
        
        response = await llm_client.generate_text(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=8000
        )
        
        # コードブロックを抽出
        code = self._extract_code_from_response(response)
        
        return code, prompt
    
    async def generate_ad_images(
        self,
        marketing_plan: MarketingPlan,
        llm_client
    ) -> Tuple[Dict, str]:
        """
        広告画像生成用のプロンプトを作成
        
        Note: 実際の画像生成はNano Banana Pro等の画像生成APIを呼び出す
        現時点ではプロンプトのみ生成
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
        
        Returns:
            (画像プロンプト辞書, 生成プロンプト) のタプル
        """
        prompt = self._create_image_generation_prompt(marketing_plan)
        
        system_prompt = """あなたは画像生成AIのプロンプトエンジニアです。
DALL-E、Midjourney、Stable Diffusionなどで使用できる高品質な画像生成プロンプトを
英語で作成してください。"""
        
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        # プロンプトを抽出
        image_prompts = self._parse_image_prompts(response)
        
        return image_prompts, prompt
    
    async def generate_ad_copy(
        self,
        marketing_plan: MarketingPlan,
        llm_client
    ) -> Tuple[Dict, str]:
        """
        広告コピーを生成
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
        
        Returns:
            (広告コピー辞書, 生成プロンプト) のタプル
        """
        prompt = self._create_ad_copy_generation_prompt(marketing_plan)
        
        system_prompt = """あなたは宿泊業界の経験豊富なコピーライターです。
魅力的で効果的な広告コピーを作成してください。"""
        
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        # コピーを抽出
        ad_copy = self._parse_ad_copy(response)
        
        return ad_copy, prompt
    
    def _create_lp_generation_prompt(self, plan: MarketingPlan) -> str:
        """LP生成プロンプトを作成"""
        return f"""
以下のマーケティングプランに基づいて、宿泊施設のランディングページを作成してください。

【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}

ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False, indent=2)}
価格帯: {json.dumps(plan.price_range, ensure_ascii=False, indent=2)}
特典: {json.dumps(plan.benefits, ensure_ascii=False, indent=2)}

【要件】
- React + TypeScript + Tailwind CSSで実装
- レスポンシブデザイン
- 以下のセクションを含める：
  1. ヒーローセクション（キャッチコピーとCTA）
  2. プランの特徴・特典
  3. 価格情報
  4. 予約フォーム
  5. フッター

完全に動作するReactコンポーネントのコードを生成してください。
"""
    
    def _create_image_generation_prompt(self, plan: MarketingPlan) -> str:
        """画像生成プロンプト作成用のプロンプトを作成"""
        return f"""
以下のマーケティングプランに基づいて、3種類の広告画像生成用プロンプトを英語で作成してください。

【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}
ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False)}

以下のJSON形式で出力してください：
{{
    "hero_image": {{
        "prompt": "メインビジュアル用のプロンプト（英語）",
        "style": "スタイル指定",
        "aspect_ratio": "16:9"
    }},
    "feature_image": {{
        "prompt": "特徴紹介用のプロンプト（英語）",
        "style": "スタイル指定",
        "aspect_ratio": "4:3"
    }},
    "social_ad_image": {{
        "prompt": "SNS広告用のプロンプト（英語）",
        "style": "スタイル指定",
        "aspect_ratio": "1:1"
    }}
}}
"""
    
    def _create_ad_copy_generation_prompt(self, plan: MarketingPlan) -> str:
        """広告コピー生成プロンプトを作成"""
        return f"""
以下のマーケティングプランに基づいて、複数の広告コピーを作成してください。

【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}
ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False)}
特典: {json.dumps(plan.benefits, ensure_ascii=False)}

以下のJSON形式で出力してください：
{{
    "headline": {{
        "main": "メインキャッチコピー（30文字以内）",
        "sub": "サブコピー（50文字以内）"
    }},
    "google_ads": {{
        "title_1": "Google広告タイトル1（30文字以内）",
        "title_2": "Google広告タイトル2（30文字以内）",
        "description": "説明文（90文字以内）"
    }},
    "facebook_ads": {{
        "primary_text": "Facebook広告メインテキスト（125文字以内）",
        "headline": "見出し（40文字以内）",
        "description": "説明文（30文字以内）"
    }},
    "instagram_caption": {{
        "main_text": "Instagram投稿テキスト（200文字程度）",
        "hashtags": ["#ハッシュタグ1", "#ハッシュタグ2", "#ハッシュタグ3"]
    }},
    "email_subject": "メール件名（30文字以内）"
}}
"""
    
    def _extract_code_from_response(self, response: str) -> str:
        """レスポンスからコードブロックを抽出"""
        # マークダウンのコードブロックを抽出
        code_match = re.search(r'```(?:tsx|typescript|jsx|javascript)?\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        # コードブロックがない場合はレスポンス全体を返す
        return response
    
    def _parse_image_prompts(self, response: str) -> Dict:
        """画像プロンプトをパース"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except Exception as e:
            print(f"画像プロンプト解析エラー: {e}")
            return {
                "hero_image": {
                    "prompt": "Luxury hotel room with ocean view, modern interior design, warm lighting",
                    "style": "photorealistic",
                    "aspect_ratio": "16:9"
                },
                "feature_image": {
                    "prompt": "Japanese ryokan hot spring, traditional architecture, peaceful atmosphere",
                    "style": "photorealistic",
                    "aspect_ratio": "4:3"
                },
                "social_ad_image": {
                    "prompt": "Cozy hotel bed with fluffy pillows, inviting atmosphere",
                    "style": "photorealistic",
                    "aspect_ratio": "1:1"
                }
            }
    
    def _parse_ad_copy(self, response: str) -> Dict:
        """広告コピーをパース"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except Exception as e:
            print(f"広告コピー解析エラー: {e}")
            return {
                "headline": {
                    "main": "特別なひとときを、あなたに",
                    "sub": "心に残る宿泊体験をお届けします"
                },
                "google_ads": {
                    "title_1": "今だけ特別プラン",
                    "title_2": "快適な宿泊をお約束",
                    "description": "ゆったりとした客室で、くつろぎのひとときを。特別な特典もご用意しております。"
                },
                "facebook_ads": {
                    "primary_text": "日常を忘れて、特別な時間を過ごしませんか？",
                    "headline": "今だけの特別プラン",
                    "description": "詳しくはこちら"
                },
                "instagram_caption": {
                    "main_text": "心に残る宿泊体験を。特別なひとときをお過ごしください。",
                    "hashtags": ["#宿泊", "#旅行", "#癒し"]
                },
                "email_subject": "【特別プラン】ご予約受付中"
            }


