import json
import re
import os
import uuid
from typing import Dict, Optional, Tuple
from app.models import MarketingPlan
from app.core.language import get_language_instruction, get_language_name, is_japanese


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
                # LP用画像は同じディレクトリにあるので、ファイル名のみ
                # /static/lp/5/hero_xxx.png -> ./hero_xxx.png
                if f"/static/lp/{hotel_id}/" in url:
                    filename = url.split("/")[-1]
                    relative_path = f"./{filename}"
                else:
                    # その他の画像（広告用など）は../で上に上がる
                    # /static/generated_images/5/xxx.png -> ../generated_images/5/xxx.png
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
        cv_url: str = None,
        hotel_info: Dict = None,
        image_urls: Dict[str, str] = None
    ) -> Tuple[str, str]:
        """
        ランディングページのコードを生成
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            cv_url: コンバージョン用URL（予約リンク）
            hotel_info: ホテル情報（name, address, phone, website）
            image_urls: 生成された画像のURL辞書
        
        Returns:
            (ソースコード, 生成プロンプト) のタプル
        """
        # ターゲット言語を取得
        target_language = self._get_target_language(marketing_plan)
        
        prompt = self._create_lp_generation_prompt(marketing_plan, cv_url, hotel_info, image_urls, target_language)
        
        # 言語に応じたシステムプロンプトを生成
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)
        
        system_prompt = f"""あなたは宿泊業界専門の経験豊富なWebデザイナー兼フロントエンドエンジニアです。
高級感があり、信頼性を感じさせる宿泊施設のランディングページを作成してください。

【重要：出力言語】
{language_instruction}
LPのテキストコンテンツ（見出し、本文、ボタンテキストなど）はすべて{language_name}で記述してください。

【重要なデザイン原則】
1. 色は指定されたカラーパレットのみを使用すること（3色以内）
2. 余白を十分に取り、読みやすいレイアウトにすること
3. 画像が指定されている場合は必ず使用すること
4. フォントサイズは見出し・本文・補足で明確に差をつけること
5. CTAボタンは目立つが上品なデザインにすること

HTML + CSS + JavaScript のシングルファイルで実装してください。
すべてのスタイルとスクリプトは1つのHTMLファイルに含めてください（<style>タグと<script>タグを使用）。
外部ライブラリやフレームワークを使用せず、純粋なHTML/CSS/JavaScriptで実装してください。"""
        
        response = await llm_client.generate_text(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=8000
        )
        
        # コードブロックを抽出
        code = self._extract_code_from_response(response)
        
        return code, prompt
    
    def _get_target_language(self, marketing_plan: MarketingPlan) -> str:
        """
        マーケティングプランからターゲット言語を取得
        
        Args:
            marketing_plan: マーケティングプラン
        
        Returns:
            言語コード（デフォルト: "ja"）
        """
        if marketing_plan.target_audience and isinstance(marketing_plan.target_audience, dict):
            return marketing_plan.target_audience.get('target_language', 'ja')
        return 'ja'
    
    async def _generate_images_with_configs(
        self,
        image_configs: Dict,
        llm_client,
        hotel_id: int,
        prefix: str = "",
        save_subdir: str = "generated_images"
    ) -> Tuple[Dict, str]:
        """
        画像設定に基づいて画像を生成する共通関数
        
        Args:
            image_configs: 画像設定辞書
            llm_client: LLMクライアント
            hotel_id: ホテルID
            prefix: ファイル名のプレフィックス
            save_subdir: 保存先サブディレクトリ（"generated_images" or "lp"）
        
        Returns:
            (画像URL辞書, 生成ログ) のタプル
        """
        # 画像保存ディレクトリを作成
        image_dir = os.path.join("static", save_subdir, str(hotel_id))
        os.makedirs(image_dir, exist_ok=True)
        
        image_urls = {}
        generation_log = []
        
        for image_type, config in image_configs.items():
            try:
                # 画像を生成
                image_data, mime_type = await llm_client.generate_image(
                    prompt=config["prompt"],
                    aspect_ratio=config.get("aspect_ratio", "16:9")
                )
                
                # ファイル拡張子を決定
                ext = "png" if "png" in mime_type else "jpg"
                filename = f"{prefix}{image_type}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(image_dir, filename)
                
                # 画像を保存
                with open(filepath, "wb") as f:
                    f.write(image_data)
                
                # URLパスを保存（save_subdirに応じたパス）
                image_urls[image_type] = f"/static/{save_subdir}/{hotel_id}/{filename}"
                generation_log.append(f"{image_type}: 生成成功")
                
            except Exception as e:
                error_str = str(e)
                print(f"画像生成エラー ({image_type}): {error_str}")
                
                # エラー情報を記録
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    image_urls[image_type] = {"error": "quota_exceeded", "message": "API利用制限に達しました"}
                else:
                    image_urls[image_type] = {"error": "generation_failed", "message": f"画像生成に失敗: {error_str[:100]}"}
                
                generation_log.append(f"{image_type}: 生成失敗 - {error_str[:100]}")
        
        return image_urls, generation_log

    async def generate_lp_images(
        self,
        marketing_plan: MarketingPlan,
        llm_client,
        hotel_id: int
    ) -> Tuple[Dict, str]:
        """
        LP用画像を生成（static/lp/{hotel_id}/に保存）
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            hotel_id: ホテルID
        
        Returns:
            (画像URL辞書, 生成プロンプト) のタプル
        """
        image_configs = self._create_lp_image_prompts(marketing_plan)
        image_urls, generation_log = await self._generate_images_with_configs(
            image_configs, llm_client, hotel_id, prefix="", save_subdir="lp"
        )
        prompt_summary = self._format_generation_summary(image_configs, generation_log, "LP用画像")
        return image_urls, prompt_summary

    async def generate_ad_images(
        self,
        marketing_plan: MarketingPlan,
        llm_client,
        hotel_id: int
    ) -> Tuple[Dict, str]:
        """
        広告用画像を生成（ディスプレイ広告、SNS広告用）
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            hotel_id: ホテルID
        
        Returns:
            (画像URL辞書, 生成プロンプト) のタプル
        """
        image_configs = self._create_ad_image_prompts(marketing_plan)
        image_urls, generation_log = await self._generate_images_with_configs(
            image_configs, llm_client, hotel_id, prefix="ad_"
        )
        prompt_summary = self._format_generation_summary(image_configs, generation_log, "広告用画像")
        return image_urls, prompt_summary

    def _create_lp_image_prompts(self, plan: MarketingPlan) -> Dict:
        """LP用画像のプロンプトを作成"""
        target_info = json.dumps(plan.target_audience, ensure_ascii=False) if plan.target_audience else "一般"
        
        # 共通の指示: テキストを生成しない
        no_text_instruction = """
CRITICAL: DO NOT generate any text, letters, words, numbers, logos, watermarks, or typography in the image.
The image must be purely photographic with no text elements whatsoever."""
        
        return {
            "hero": {
                "prompt": f"""A stunning, wide-angle photograph of a Japanese ryokan or hotel.
Scene: Beautiful exterior or grand interior entrance/lobby.
Concept: {plan.concept}
Style: High-end hospitality photography, dramatic lighting, cinematic composition.
The image should immediately convey luxury, comfort and Japanese hospitality.
{no_text_instruction}""",
                "aspect_ratio": "16:9"
            },
            "feature": {
                "prompt": f"""A warm, inviting photograph showcasing the best feature of a Japanese accommodation.
Theme: {plan.plan_name}
Could be: hot spring bath, traditional room, scenic view, or gourmet cuisine.
Style: Editorial travel photography, soft natural lighting, cozy atmosphere.
Focus on details that evoke relaxation and authentic experience.
{no_text_instruction}""",
                "aspect_ratio": "4:3"
            },
            "ambiance": {
                "prompt": f"""An atmospheric detail shot of a Japanese hotel/ryokan.
Theme: {plan.concept}
Could be: tea ceremony setup, flower arrangement, traditional crafts, garden view.
Style: Minimalist, zen aesthetic, beautiful bokeh, warm tones.
The image should add depth and cultural authenticity to the page.
{no_text_instruction}""",
                "aspect_ratio": "1:1"
            }
        }

    def _create_ad_image_prompts(self, plan: MarketingPlan) -> Dict:
        """広告用画像のプロンプトを作成（テキストオーバーレイ用スペースあり）"""
        target_info = json.dumps(plan.target_audience, ensure_ascii=False) if plan.target_audience else "一般"
        
        return {
            "display_wide": {
                "prompt": f"""A visually striking advertisement image for a Japanese hotel/ryokan.
Campaign: {plan.plan_name}
IMPORTANT: Leave clear space on the left or right side for text overlay.
Style: Modern advertising photography, high contrast, eye-catching.
The image should work as a banner ad background.""",
                "aspect_ratio": "16:9"
            },
            "display_square": {
                "prompt": f"""A compelling square advertisement image for social media.
Campaign: {plan.plan_name}
Message: {plan.concept}
IMPORTANT: Leave clear space at top or bottom for text overlay.
Style: Instagram-worthy, vibrant but elegant, scroll-stopping.
Target: {target_info}""",
                "aspect_ratio": "1:1"
            },
            "display_vertical": {
                "prompt": f"""A vertical advertisement image for mobile display ads or stories.
Campaign: {plan.plan_name}
IMPORTANT: Leave clear space at top and bottom for text overlay.
Style: Modern, aspirational, mobile-optimized composition.
The image should make viewers want to book immediately.""",
                "aspect_ratio": "9:16"
            }
        }

    def _format_generation_summary(self, configs: Dict, logs: list, category: str = "画像") -> str:
        """生成サマリーをフォーマット"""
        summary = f"【{category}生成サマリー】\n\n"
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
        # ターゲット言語を取得
        target_language = self._get_target_language(marketing_plan)
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)
        
        prompt = self._create_ad_copy_generation_prompt(marketing_plan, target_language)
        
        system_prompt = f"""あなたは宿泊業界の経験豊富なコピーライターです。
魅力的で効果的な広告コピーを作成してください。

【重要：出力言語】
{language_instruction}
すべての広告コピーを{language_name}で作成してください。"""
        
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        # コピーを抽出
        ad_copy = self._parse_ad_copy(response)
        
        return ad_copy, prompt
    
    def _create_lp_generation_prompt(
        self, 
        plan: MarketingPlan, 
        cv_url: str = None,
        hotel_info: Dict = None,
        image_urls: Dict[str, str] = None,
        target_language: str = "ja"
    ) -> str:
        """LP生成プロンプトを作成"""
        
        # 言語指示を作成
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)
        
        # ホテル情報セクション
        hotel_section = ""
        if hotel_info:
            hotel_section = f"""
【施設情報】
施設名: {hotel_info.get('name', '宿泊施設')}
住所: {hotel_info.get('address', '')}
電話番号: {hotel_info.get('phone', '') or '掲載なし'}
公式サイト: {hotel_info.get('website', '') or '掲載なし'}
"""
        
        # 画像セクション
        image_section = ""
        if image_urls and len(image_urls) > 0:
            image_section = """
【使用する画像 - 必ず以下の画像をHTMLに埋め込んでください】
"""
            for img_type, img_path in image_urls.items():
                # パスをファイル名のみの相対パス（./xxx.png）に変換
                if isinstance(img_path, str) and "/" in img_path:
                    filename = img_path.split("/")[-1]
                    relative_path = f"./{filename}"
                else:
                    relative_path = img_path
                
                if img_type == "hero":
                    image_section += f"- ヒーロー画像（メインビジュアル）: {relative_path}\n"
                elif img_type == "feature":
                    image_section += f"- 特徴紹介画像: {relative_path}\n"
                elif img_type == "ambiance":
                    image_section += f"- 雰囲気・ディテール画像: {relative_path}\n"
                else:
                    image_section += f"- {img_type}: {relative_path}\n"
            
            image_section += """
※ 上記の画像パス（./xxx.png形式）をそのままimgタグのsrc属性に使用してください
※ ヒーロー画像はヒーローセクションの背景または大きな画像として使用
※ 特徴画像は特徴・特典セクションで使用
※ 雰囲気画像は追加のビジュアルとして適宜使用
"""
        else:
            image_section = """
【画像について】
- 画像は使用せず、CSSグラデーションや図形でビジュアルを表現してください
"""
        
        # CV URLがある場合のCTA説明
        cta_instruction = ""
        if cv_url:
            cta_instruction = f"""
【重要: CTAボタンについて】
- 予約ボタン（CTA）は以下のURLへの外部リンクにしてください
- 予約URL: {cv_url}
- フォームは設置せず、「今すぐ予約する」「ご予約はこちら」などのボタンをクリックすると上記URLに遷移するようにしてください
- ボタンはページ内に3箇所以上配置（ヒーローセクション、特徴セクション後、フッター前）
"""
        else:
            cta_instruction = """
【CTAボタンについて】
- 予約ボタン（CTA）は「#」をhrefに設定してください
"""
        
        # カラーパレット（宿泊施設向けの上品な配色）
        color_palette = """
【カラーパレット - この3色のみを使用してください】
- メインカラー: #2c3e50（深いネイビー / 信頼感・高級感）
- アクセントカラー: #c0392b（落ち着いた赤 / CTAボタン用）
- 背景色: #fdfbf7（温かみのあるオフホワイト）
- テキスト色: #333333（ダークグレー / 本文用）
- サブテキスト色: #666666（グレー / 補足情報用）

※ 上記以外の色は使用しないでください
※ グラデーションを使う場合も上記の色の組み合わせのみ
"""
        
        return f"""
以下のマーケティングプランに基づいて、宿泊施設のランディングページを作成してください。
{hotel_section}
【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}

ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False, indent=2)}
価格帯: {json.dumps(plan.price_range, ensure_ascii=False, indent=2)}
特典: {json.dumps(plan.benefits, ensure_ascii=False, indent=2)}
{color_palette}
{image_section}
{cta_instruction}
【デザイン要件】
1. 全体的なスタイル
   - 余白を十分に取る（セクション間は80px以上）
   - 行間は1.8以上で読みやすく
   - 最大幅1200pxでセンタリング

2. タイポグラフィ
   - 見出し: 32px-48px, font-weight: 700
   - 本文: 16px-18px, font-weight: 400
   - 補足: 14px, font-weight: 400

3. CTAボタン
   - パディング: 16px 48px以上
   - 角丸: 4px（控えめ）
   - ホバー時に少し暗くなるエフェクト

4. セクション構成
   - ヒーローセクション: 施設名、キャッチコピー、CTAボタン、（ヒーロー画像があれば背景に使用）
   - コンセプト紹介: プランのコンセプトを魅力的に説明
   - 特徴・特典セクション: アイコンまたは画像付きで特典を紹介
   - 価格セクション: 価格情報をわかりやすく表示、CTAボタン
   - 施設情報: 施設名、住所、電話番号
   - フッター: CTAボタン、コピーライト

【技術要件】
- HTML + CSS + JavaScript のシングルファイル（.html）で実装
- CSSは<style>タグ内に記述
- JavaScriptは<script>タグ内に記述（スムーズスクロールなど）
- 外部ライブラリやCDNは使用しない
- レスポンシブデザイン（768px以下でモバイル対応）

【重要：出力言語】
{language_instruction}
- LPのテキストコンテンツ（見出し、本文、ボタンテキスト、キャッチコピーなど）はすべて{language_name}で記述してください
- 施設名やプラン名も{language_name}で適切に翻訳・表現してください
- CTAボタンのテキストも{language_name}にしてください（例: 英語なら "Book Now"、中国語なら "立即預約" など）

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
    
    def _create_ad_copy_generation_prompt(self, plan: MarketingPlan, target_language: str = "ja") -> str:
        """広告コピー生成プロンプトを作成"""
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)
        
        return f"""
以下のマーケティングプランに基づいて、複数の広告コピーを作成してください。

【重要：出力言語】
{language_instruction}
すべての広告コピーを{language_name}で作成してください。

【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}
ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False)}
特典: {json.dumps(plan.benefits, ensure_ascii=False)}

以下のJSON形式で出力してください（すべて{language_name}で記述）：
{{
    "headline": {{
        "main": "メインキャッチコピー",
        "sub": "サブコピー"
    }},
    "google_ads": {{
        "title_1": "Google広告タイトル1",
        "title_2": "Google広告タイトル2",
        "description": "説明文"
    }},
    "facebook_ads": {{
        "primary_text": "Facebook広告メインテキスト",
        "headline": "見出し",
        "description": "説明文"
    }},
    "instagram_caption": {{
        "main_text": "Instagram投稿テキスト",
        "hashtags": ["#ハッシュタグ1", "#ハッシュタグ2", "#ハッシュタグ3"]
    }},
    "email_subject": "メール件名"
}}
"""
    
    def _extract_code_from_response(self, response: str) -> str:
        """レスポンスからコードブロックを抽出"""
        # マークダウンのコードブロックを抽出（HTML優先）
        # パターン1: ```html や ```typescript など言語指定付き
        code_match = re.search(r'```(?:html|tsx|typescript|jsx|javascript)\s*\n(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # パターン2: 言語指定なしのコードブロック
        code_match = re.search(r'```\s*\n(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # パターン3: <!DOCTYPE html> または <html から始まるHTMLを直接抽出
        html_match = re.search(r'(<!DOCTYPE html>.*</html>)', response, re.DOTALL | re.IGNORECASE)
        if html_match:
            return html_match.group(1).strip()
        
        # パターン4: <html>から始まるHTMLを抽出
        html_match = re.search(r'(<html.*</html>)', response, re.DOTALL | re.IGNORECASE)
        if html_match:
            return html_match.group(1).strip()
        
        # コードブロックもHTMLも見つからない場合はレスポンス全体を返す
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
    
    async def generate_ota_text(
        self,
        marketing_plan: MarketingPlan,
        llm_client,
        hotel_info: Dict = None
    ) -> Tuple[Dict, str]:
        """
        OTA（じゃらん、楽天トラベル）向けテキストを生成
        
        ※ OTAは日本国内サービスのため、日本語ターゲット以外の場合はスキップ
        
        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            hotel_info: ホテル情報
        
        Returns:
            (OTAテキスト辞書, 生成プロンプト) のタプル
        """
        # ターゲット言語を取得
        target_language = self._get_target_language(marketing_plan)
        
        # 日本語以外のターゲットの場合はスキップ
        if not is_japanese(target_language):
            language_name = get_language_name(target_language)
            skip_message = {
                "jalan": {
                    "plan_title": f"※ {language_name}ターゲットのため生成スキップ",
                    "catch_copy": "OTAは日本国内サービスのため、海外向けプランでは生成されません",
                    "plan_description": f"このプランのターゲット言語は{language_name}です。じゃらん・楽天トラベルは日本国内向けサービスのため、OTAテキストの生成はスキップされました。\n\n海外向けのOTA（Booking.com、Expedia、Agoda等）への掲載をご検討の場合は、LP・広告コピーを参考に各サイトの形式に合わせてご作成ください。",
                    "features": ["海外向けプラン", "OTA生成スキップ"]
                },
                "rakuten": {
                    "plan_title": f"※ {language_name}ターゲットのため生成スキップ",
                    "catch_copy": "OTAは日本国内サービスのため、海外向けプランでは生成されません",
                    "plan_description": f"このプランのターゲット言語は{language_name}です。じゃらん・楽天トラベルは日本国内向けサービスのため、OTAテキストの生成はスキップされました。\n\n海外向けのOTA（Booking.com、Expedia、Agoda等）への掲載をご検討の場合は、LP・広告コピーを参考に各サイトの形式に合わせてご作成ください。",
                    "features": ["海外向けプラン", "OTA生成スキップ"]
                }
            }
            return skip_message, f"日本語以外のターゲット（{language_name}）のため、OTAテキスト生成をスキップしました。"
        
        prompt = self._create_ota_text_generation_prompt(marketing_plan, hotel_info)
        
        system_prompt = """あなたは宿泊業界のOTAマーケティング専門家です。
じゃらんや楽天トラベルで高い予約率を実現するプラン説明文を作成してください。

【絶対厳守】マークダウン記法の禁止：
- #, ##, ### などの見出し記法は使用禁止
- *, **, _ などの強調記法は使用禁止
- - による箇条書きは使用禁止（代わりに「・」「●」を使用）
- OTAサイトはプレーンテキストのみ対応のため、上記を厳守してください

重要なポイント：
- 具体的な体験価値を伝える
- ターゲット顧客の心に響く表現を使う
- 特典や差別化ポイントを明確に
- 季節感や限定感を演出
- SEOを意識したキーワードを含める
- 見出しは【】や◆、箇条書きは・や●を使用"""
        
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3000
        )
        
        # OTAテキストをパース
        ota_text = self._parse_ota_text(response)
        
        return ota_text, prompt
    
    def _create_ota_text_generation_prompt(self, plan: MarketingPlan, hotel_info: Dict = None) -> str:
        """OTAテキスト生成プロンプトを作成"""
        hotel_section = ""
        if hotel_info:
            hotel_section = f"""
【施設情報】
施設名: {hotel_info.get('name', '宿泊施設')}
住所: {hotel_info.get('address', '')}
"""
        
        return f"""
以下のマーケティングプランに基づいて、OTA（じゃらん、楽天トラベル）向けのプラン説明テキストを作成してください。
{hotel_section}
【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}
ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False)}
特典: {json.dumps(plan.benefits, ensure_ascii=False)}

【重要：出力形式について】
- OTAサイトはプレーンテキストのみ対応のため、マークダウン記法（#, *, -, ** など）は絶対に使用しないでください
- 箇条書きは「・」「●」「◆」「■」などの記号を使用してください
- 見出しは「【】」や「＜＞」で囲むか、「◎」「★」などの記号を先頭に付けてください
- 強調は「」や『』で囲んでください

以下のJSON形式で出力してください：
{{
    "jalan": {{
        "plan_title": "プランタイトル（50文字以内、【】を使った訴求力のあるタイトル）",
        "catch_copy": "キャッチコピー（30文字以内、インパクトのある一言）",
        "plan_description": "プラン説明文（1000〜1500文字、改行を含む読みやすい形式）。以下の構成で作成：\\n・冒頭のアピールポイント\\n・プランの特徴\\n・含まれるサービス・特典\\n・おすすめのシーン\\n・注意事項",
        "features": ["特徴1", "特徴2", "特徴3"]
    }},
    "rakuten": {{
        "plan_title": "プランタイトル（50文字以内、検索されやすいキーワードを含む）",
        "catch_copy": "キャッチコピー（50文字以内）",
        "plan_description": "プラン説明文（1000〜2000文字、改行を含む読みやすい形式）。以下の構成で作成：\\n・プランの魅力\\n・含まれるサービス内容\\n・お部屋の特徴\\n・お食事について\\n・特典・サービス\\n・ご予約時の注意",
        "features": ["特徴1", "特徴2", "特徴3"]
    }}
}}

【作成のポイント】
1. じゃらん向け：感情に訴える表現、体験価値を重視
2. 楽天トラベル向け：具体的なスペック・サービス内容を詳細に
3. 両方：SEOキーワード（温泉、露天風呂、懐石料理、記念日など）を自然に含める
4. 両方：マークダウン記法は使用せず、プレーンテキストの装飾（「」『』【】・●◆など）を使用
"""
    
    def _parse_ota_text(self, response: str) -> Dict:
        """OTAテキストをパース"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except Exception as e:
            print(f"OTAテキスト解析エラー: {e}")
            return {
                "jalan": {
                    "plan_title": "【特別プラン】心に残るひとときを",
                    "catch_copy": "大切な人と特別な時間を",
                    "plan_description": "ゆったりとした時間をお過ごしいただける特別プランです。",
                    "features": ["特別な体験", "くつろぎの空間", "おもてなし"]
                },
                "rakuten": {
                    "plan_title": "【特別プラン】心に残るひとときを",
                    "catch_copy": "大切な人と過ごす特別な時間をお届けします",
                    "plan_description": "ゆったりとした時間をお過ごしいただける特別プランです。",
                    "features": ["特別な体験", "くつろぎの空間", "おもてなし"]
                }
            }


