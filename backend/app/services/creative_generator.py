import json
import re
import os
import uuid
from typing import Dict, Optional, Tuple
from app.models import MarketingPlan


class CreativeGenerator:
    """クリエイティブアセット生成サービス"""
    
    def __init__(self):
        self.static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    
    def save_lp_to_file(
        self,
        lp_source_code: str,
        hotel_id: int,
        asset_id: int,
        image_urls: Dict[str, str] = None
    ) -> str:
        """
        LPのHTMLをファイルとして保存
        
        Args:
            lp_source_code: LPのソースコード
            hotel_id: ホテルID
            asset_id: アセットID
            image_urls: 画像URL辞書（ad_image_urls）
        
        Returns:
            プレビューURL（相対パス）
        """
        # LPディレクトリを作成
        lp_dir = os.path.join(self.static_dir, "lp", str(hotel_id))
        os.makedirs(lp_dir, exist_ok=True)
        
        # 画像パスを相対パスに変換
        processed_code = self._convert_image_paths_to_relative(
            lp_source_code, hotel_id, image_urls
        )
        
        # HTMLファイルを保存
        filename = f"lp_{asset_id}.html"
        filepath = os.path.join(lp_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(processed_code)
        
        # プレビューURL（静的ファイルとしてアクセス可能なパス）
        preview_url = f"/static/lp/{hotel_id}/{filename}"
        return preview_url
    
    def _convert_image_paths_to_relative(
        self,
        html_code: str,
        hotel_id: int,
        image_urls: Dict[str, str] = None
    ) -> str:
        """
        HTML内の画像パスを相対パスに変換
        
        Args:
            html_code: HTMLソースコード
            hotel_id: ホテルID
            image_urls: 画像URL辞書
        
        Returns:
            変換後のHTMLコード
        """
        if not image_urls:
            return html_code
        
        processed_code = html_code
        
        # 各画像URLを相対パスに変換
        for image_type, url in image_urls.items():
            if isinstance(url, str) and url.startswith("/static/"):
                # /static/generated_images/5/hero_image_xxx.png
                # -> ../generated_images/5/hero_image_xxx.png
                relative_path = ".." + url.replace("/static/", "/")
                
                # 絶対URLパターンも置換（http://localhost:8000/static/...）
                processed_code = processed_code.replace(
                    f"http://localhost:8000{url}", relative_path
                )
                processed_code = processed_code.replace(url, relative_path)
        
        return processed_code
    
    async def generate_landing_page(
        self,
        marketing_plan: MarketingPlan,
        llm_client,
        cv_url: str = None
    ) -> Tuple[str, str]:
        """
        ランディングページのコードを生成
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            cv_url: コンバージョン用URL（予約リンク）
        
        Returns:
            (ソースコード, 生成プロンプト) のタプル
        """
        prompt = self._create_lp_generation_prompt(marketing_plan, cv_url)
        
        system_prompt = """あなたは経験豊富なフロントエンドエンジニアです。
HTML + CSS + JavaScript のシングルファイルで、モダンで美しいランディングページを作成してください。
すべてのスタイルとスクリプトは1つのHTMLファイルに含めてください（<style>タグと<script>タグを使用）。
外部ライブラリやフレームワークを使用せず、純粋なHTML/CSS/JavaScriptで実装してください。
完全に動作し、そのままウェブサーバーにデプロイできる状態で提供してください。"""
        
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
        llm_client,
        hotel_id: int
    ) -> Tuple[Dict, str]:
        """
        広告画像を生成（Gemini 2.5 Flash Image / Nano Banana）
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            hotel_id: ホテルID（画像保存パス用）
        
        Returns:
            (画像URL辞書, 生成プロンプト) のタプル
        """
        # 画像保存ディレクトリを作成
        image_dir = os.path.join("static", "generated_images", str(hotel_id))
        os.makedirs(image_dir, exist_ok=True)
        
        # 各用途の画像プロンプトを生成
        image_configs = self._create_image_prompts_for_plan(marketing_plan)
        
        image_urls = {}
        generation_log = []
        has_quota_error = False
        quota_error_message = None
        
        for image_type, config in image_configs.items():
            try:
                # 画像を生成
                image_data, mime_type = await llm_client.generate_image(
                    prompt=config["prompt"],
                    aspect_ratio=config.get("aspect_ratio", "16:9")
                )
                
                # ファイル拡張子を決定
                ext = "png" if "png" in mime_type else "jpg"
                filename = f"{image_type}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(image_dir, filename)
                
                # 画像を保存
                with open(filepath, "wb") as f:
                    f.write(image_data)
                
                # URLパスを保存（フロントエンドからアクセス可能なパス）
                image_urls[image_type] = f"/static/generated_images/{hotel_id}/{filename}"
                generation_log.append(f"{image_type}: 生成成功")
                
            except Exception as e:
                error_str = str(e)
                print(f"画像生成エラー ({image_type}): {error_str}")
                
                # APIクォータエラーを検出
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    has_quota_error = True
                    quota_error_message = "API利用制限に達しました。しばらく待ってから再度お試しください。"
                    image_urls[image_type] = {"error": "quota_exceeded", "message": quota_error_message}
                else:
                    image_urls[image_type] = {"error": "generation_failed", "message": f"画像生成に失敗しました: {error_str[:100]}"}
                
                generation_log.append(f"{image_type}: 生成失敗 - {error_str[:100]}")
        
        prompt_summary = self._format_generation_summary(image_configs, generation_log)
        
        return image_urls, prompt_summary
    
    def _create_image_prompts_for_plan(self, plan: MarketingPlan) -> Dict:
        """マーケティングプランに基づいて画像生成プロンプトを作成"""
        target_info = json.dumps(plan.target_audience, ensure_ascii=False) if plan.target_audience else "一般"
        
        return {
            "hero_image": {
                "prompt": f"""A stunning, professional photograph of a Japanese ryokan (traditional inn) exterior or interior. 
The scene should convey: {plan.concept}
Target audience: {target_info}
Style: High-end hotel photography, warm and inviting atmosphere, soft natural lighting.
The image should feel luxurious yet authentic Japanese hospitality.""",
                "aspect_ratio": "16:9"
            },
            "feature_image": {
                "prompt": f"""A beautiful photograph showcasing a special feature of a Japanese accommodation.
Theme: {plan.plan_name}
Concept: {plan.concept}
Style: Editorial photography, highlighting unique amenities or experiences, warm colors.
Focus on details that appeal to travelers seeking authentic experiences.""",
                "aspect_ratio": "4:3"
            },
            "social_ad_image": {
                "prompt": f"""An eye-catching social media advertisement image for a Japanese hotel/ryokan.
Campaign: {plan.plan_name}
Message: {plan.concept}
Style: Modern, clean, Instagram-worthy, with space for text overlay.
The image should stop scrollers and evoke desire to travel.""",
                "aspect_ratio": "1:1"
            }
        }
    
    def _format_generation_summary(self, configs: Dict, logs: list) -> str:
        """生成サマリーをフォーマット"""
        summary = "【画像生成サマリー】\n\n"
        for image_type, config in configs.items():
            summary += f"■ {image_type}\n"
            summary += f"  プロンプト: {config['prompt'][:100]}...\n"
            summary += f"  アスペクト比: {config.get('aspect_ratio', '16:9')}\n\n"
        summary += "\n【生成ログ】\n" + "\n".join(logs)
        return summary
    
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
    
    def _create_lp_generation_prompt(self, plan: MarketingPlan, cv_url: str = None) -> str:
        """LP生成プロンプトを作成"""
        
        # CV URLがある場合のCTA説明
        cta_instruction = ""
        if cv_url:
            cta_instruction = f"""
【重要: CTAボタンについて】
- 予約ボタン（CTA）は以下のURLへの外部リンクにしてください
- 予約URL: {cv_url}
- フォームは設置せず、「今すぐ予約する」「ご予約はこちら」などのボタンをクリックすると上記URLに遷移するようにしてください
- ボタンは目立つデザインで、ページ内に複数配置してください（ヒーローセクション、価格セクション、フッター付近など）
"""
        else:
            cta_instruction = """
【CTAボタンについて】
- 予約ボタン（CTA）は「#」または「javascript:void(0)」をhrefに設定してください
- フォームは設置せず、ボタンのみ配置してください
"""
        
        return f"""
以下のマーケティングプランに基づいて、宿泊施設のランディングページを作成してください。

【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}

ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False, indent=2)}
価格帯: {json.dumps(plan.price_range, ensure_ascii=False, indent=2)}
特典: {json.dumps(plan.benefits, ensure_ascii=False, indent=2)}
{cta_instruction}
【要件】
- HTML + CSS + JavaScript のシングルファイル（.html）で実装
- CSSは<style>タグ内に記述
- JavaScriptは<script>タグ内に記述
- 外部ライブラリやCDNは使用しない（純粋なHTML/CSS/JavaScript）
- レスポンシブデザイン（モバイル対応）
- モダンで美しいデザイン
- 以下のセクションを含める：
  1. ヒーローセクション（キャッチコピーとCTAボタン）
  2. プランの特徴・特典
  3. 価格情報（CTAボタンも配置）
  4. CTAセクション（最終的な予約ボタン）
  5. フッター

完全に動作する単一のHTMLファイルを生成してください。
必ず<!DOCTYPE html>から始まる完全なHTMLドキュメントを出力してください。
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
        # マークダウンのコードブロックを抽出（HTML優先）
        code_match = re.search(r'```(?:html|tsx|typescript|jsx|javascript)?\n(.*?)\n```', response, re.DOTALL)
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


