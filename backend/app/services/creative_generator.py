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
                elif "/hotel_images/" in url or "/generated_images/" in url:
                    # S3 経由で配信される画像は絶対パスのまま（変換しない）
                    relative_path = url
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
        image_urls: Dict[str, str] = None,
        hotel_detail: Dict = None
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
        
        prompt = self._create_lp_generation_prompt(marketing_plan, cv_url, hotel_info, image_urls, target_language, hotel_detail)
        
        # 言語に応じたシステムプロンプトを生成
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)
        
        system_prompt = f"""あなたは宿泊業界に特化した世界トップクラスのWebデザイナー兼フロントエンドエンジニアです。
与えられたマーケティングプランのコンセプトとターゲット像を深く読み込み、
その施設が持つ世界観を最もよく表現するランディングページを一から設計してください。

【重要：出力言語】
{language_instruction}
LPのテキストコンテンツ（見出し、本文、ボタンテキストなど）はすべて{language_name}で記述してください。

【デザイン哲学】
- 「このカラーパレットを使え」という指示はしない。あなたがコンセプトから最適な色を導き出すこと
- 「このレイアウトにしろ」という指示もしない。施設の個性に合ったセクション構成を自分で決めること
- ただし以下の品質原則は絶対に守ること：

【品質原則（Non-negotiable）】
1. **コントラスト**: 画像上のテキストには必ず半透明オーバーレイ（rgba）を使用。
   - ヒーローエリアや画像カードなど、背景に画像を使用する場合は、文字の背面に必ずオーバーレイを適用すること。
   - 実装: .hero::after 等で rgba(0,0,0,0.45) 以上の暗幕を重ねるか、linear-gradient（下から上への黒グラデーション）を配置すること。
   - WCAG AA 基準（4.5:1）以上のコントラスト比を確保すること
2. **タイポグラフィ**: 見出し・本文・補足で明確な階層を作ること（サイズ・ウェイトで差別化）
3. **余白**: セクション間は十分な余白を確保し、窮屈なレイアウトにしないこと
4. **CTA**: コンバージョンボタンは目立ちつつも、全体のデザインと調和させること。コントラスト比 4.5:1 以上を維持すること
5. **技術制約**: HTML + CSS + JS シングルファイル、外部ライブラリ不使用

【あなたに期待すること】
- プランのコンセプトを読んで「この宿はどんな雰囲気か」を想像する
- その雰囲気を体現するカラーパレット（5色以内）を自分で選ぶ
- レイアウト、フォント、セクション順も施設の個性に合わせて決める
- 毎回同じデザインにならないよう、コンセプトに忠実な独自性を出す"""
        
        response = await llm_client.generate_text(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=16000
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
        image_dir = os.path.join(self.static_dir, save_subdir, str(hotel_id))
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

    async def generate_ad_images_with_references(
        self,
        marketing_plan: MarketingPlan,
        llm_client,
        hotel_id: int,
        reference_images: Dict[str, Dict[str, object]],
        hotel_info: Dict = None,
    ) -> Tuple[Dict, str]:
        """
        施設画像を参照として広告画像を生成する。

        Args:
            marketing_plan: マーケティングプラン
            llm_client: 画像生成対応LLMクライアント
            hotel_id: ホテルID
            reference_images: 枠ごとの参照画像情報
                例: {"display_wide": {"data": b"...", "mime_type": "image/webp", "url": "..."}}
            hotel_info: 施設情報（name, address など）。パターン3のブランド署名に使用。

        Returns:
            (画像URL辞書, 生成ログ) のタプル
        """
        image_configs = self._create_ad_image_prompts(marketing_plan)
        image_dir = os.path.join("static", "generated_images", str(hotel_id))
        os.makedirs(image_dir, exist_ok=True)

        image_urls = {}
        generation_log = []

        for image_type, config in image_configs.items():
            ref = reference_images.get(image_type, {})
            ref_data = ref.get("data")
            ref_mime = ref.get("mime_type", "image/webp")
            if not ref_data:
                image_urls[image_type] = {"error": "reference_not_found", "message": "参照画像が見つかりません"}
                generation_log.append(f"{image_type}: 生成失敗 - 参照画像なし")
                continue

            try:
                edit_prompt = await self._create_ad_edit_prompt(config["prompt"], image_type, marketing_plan, llm_client, hotel_info)
                image_data, mime_type = await llm_client.generate_image_with_reference(
                    prompt=edit_prompt,
                    reference_image_data=ref_data,
                    reference_mime_type=ref_mime,
                    aspect_ratio=config.get("aspect_ratio", "16:9"),
                )

                ext = "png" if "png" in mime_type else "jpg"
                filename = f"ad_{image_type}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(image_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)

                image_urls[image_type] = f"/static/generated_images/{hotel_id}/{filename}"
                generation_log.append(f"{image_type}: 生成成功（参照画像から編集）")
            except Exception as e:
                err = str(e)
                image_urls[image_type] = {"error": "generation_failed", "message": f"画像生成に失敗: {err[:100]}"}
                generation_log.append(f"{image_type}: 生成失敗 - {err[:100]}")

        prompt_summary = self._format_generation_summary(image_configs, generation_log, "広告用画像（参照編集）")
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

    async def _derive_overlay_copy(self, image_type: str, plan: MarketingPlan, llm_client) -> str:
        """プランの内容からオーバーレイコピーを導出する。
        自然に16文字以内に収まるフレーズが見つかればそれを使い、
        なければLLMで生成する。
        """
        MAX_LEN = 16
        concept = plan.concept or ""
        plan_name = plan.plan_name or ""
        benefits = plan.benefits if isinstance(plan.benefits, dict) else {}

        # コンセプトを句読点で分割して短いフレーズ候補を抽出
        concept_phrases = [p.strip() for p in re.split(r'[、。,.・\n]', concept) if p.strip()]

        def first_short(phrases: list) -> str | None:
            return next((p for p in phrases if len(p) <= MAX_LEN), None)

        # benefitsから短い文言を候補として収集
        benefit_phrases = []
        for v in benefits.values():
            if isinstance(v, str) and v.strip():
                benefit_phrases.append(v.strip())
            elif isinstance(v, list):
                benefit_phrases.extend(str(item).strip() for item in v if str(item).strip())

        if image_type == "display_wide":
            candidate = first_short(concept_phrases)
        elif image_type == "display_square":
            candidate = (
                first_short(benefit_phrases)
                or first_short(concept_phrases[1:])
                or first_short(concept_phrases)
            )
        elif image_type == "display_vertical":
            candidate = (
                (plan_name if len(plan_name) <= MAX_LEN else None)
                or first_short(concept_phrases)
            )
        else:
            candidate = plan_name if len(plan_name) <= MAX_LEN else None

        if candidate:
            return candidate

        # 自然に短いフレーズが見つからない場合はLLMで生成
        return await self._generate_overlay_copy_with_llm(image_type, plan, llm_client, MAX_LEN)

    async def _generate_overlay_copy_with_llm(
        self, image_type: str, plan: MarketingPlan, llm_client, max_len: int = 16
    ) -> str:
        """LLMを使って広告オーバーレイコピーを生成する"""
        tone_map = {
            "display_wide": "広告バナー向けの、コンセプトを凝縮した訴求フレーズ",
            "display_square": "SNS広告向けの、特典・体験価値を伝えるフレーズ",
            "display_vertical": "モバイル広告向けの、体験・感情に訴えるフレーズ",
        }
        tone = tone_map.get(image_type, "広告向けの訴求フレーズ")

        prompt = f"""以下のマーケティングプランに基づいて、広告画像に重ねる短いプロモーションテキストを1つ生成してください。

【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}
特典: {json.dumps(plan.benefits, ensure_ascii=False)}

【要件】
- {tone}
- 必ず{max_len}文字以内で作成すること（厳守）
- 日本語で記述
- キャッチーで広告効果の高い表現
- テキストのみ出力（説明や引用符は不要）"""

        fallback_map = {
            "display_wide": "特別なひとときへ",
            "display_square": "今だけの特別プラン",
            "display_vertical": "特別な体験を",
        }

        try:
            response = await llm_client.generate_text(
                user_prompt=prompt,
                system_prompt="あなたは宿泊業界の広告コピーライターです。指定の文字数制限を厳守して、簡潔で効果的なコピーを1行だけ出力してください。",
                max_tokens=50,
            )
            copy = response.strip().strip('"').strip("「」").strip()
            if not copy or len(copy) > max_len:
                return fallback_map.get(image_type, "今すぐ予約")
            return copy
        except Exception:
            return fallback_map.get(image_type, "今すぐ予約")

    def _should_add_human_presence(self, plan: MarketingPlan) -> bool:
        """プランの内容から人物を追加すべきか判定する。
        ファミリー・一人旅・旅の体験フォーカスの場合は True、
        施設・客室・料理などにフォーカスする場合は False を返す。
        """
        # 判定対象テキストを結合（プラン名・コンセプト・ターゲット情報）
        target_str = json.dumps(plan.target_audience, ensure_ascii=False) if plan.target_audience else ""
        haystack = " ".join([plan.plan_name or "", plan.concept or "", target_str]).lower()

        # 人物を入れた方がよいキーワード
        human_keywords = [
            "ファミリー", "家族", "子供", "お子", "親子", "kids", "family",
            "一人旅", "ひとり旅", "おひとり", "solo",
            "カップル", "couple", "ふたり", "二人",
            "体験", "アクティビティ", "思い出", "旅の", "旅行",
        ]
        # 施設・空間にフォーカスするキーワード（人物不要）
        facility_keywords = [
            "客室", "お部屋", "部屋", "空間", "インテリア",
            "料理", "お料理", "美食", "グルメ", "食事",
            "温泉", "露天風呂", "大浴場", "サウナ",
            "施設", "設備", "庭園",
        ]

        human_score = sum(1 for kw in human_keywords if kw in haystack)
        facility_score = sum(1 for kw in facility_keywords if kw in haystack)

        return human_score >= facility_score

    def _select_ad_pattern(self, plan: MarketingPlan) -> int:
        """広告パターンを選択する（1: 予約促進、2: 商品理解、3: ブランド訴求）"""
        all_text = " ".join([
            plan.plan_name or "",
            plan.concept or "",
            json.dumps(plan.benefits, ensure_ascii=False),
            json.dumps(plan.target_audience, ensure_ascii=False),
        ])

        p1_keywords = ["割引", "OFF", "off", "円引", "特典", "プレゼント", "無料", "お得", "限定価格", "特別価格"]
        p1_score = sum(1 for kw in p1_keywords if kw in all_text)

        p3_keywords = ["高級", "上質", "大人", "隠れ", "プレミアム", "ラグジュアリー", "贅沢", "至高", "一流", "こだわり"]
        p3_score = sum(1 for kw in p3_keywords if kw in all_text)

        if p1_score >= 2:
            return 1
        if p3_score >= 2:
            return 3
        return 2

    def _extract_plan_text_vars(self, plan: MarketingPlan, hotel_info: Dict = None) -> Dict[str, str]:
        """プランからパターン埋め込み用テキスト変数を抽出する"""
        benefits = plan.benefits or {}
        price_range = plan.price_range or {}

        benefit_texts: list[str] = []
        if isinstance(benefits, dict):
            for v in benefits.values():
                if isinstance(v, str) and v.strip():
                    benefit_texts.append(v.strip())
                elif isinstance(v, list):
                    benefit_texts.extend(str(i).strip() for i in v if str(i).strip())

        price_str = ""
        if isinstance(price_range, dict):
            min_p = price_range.get("min") or price_range.get("standard") or price_range.get("base")
            if isinstance(min_p, (int, float)):
                price_str = f"{int(min_p):,}円〜"
            elif isinstance(min_p, str) and min_p:
                price_str = min_p

        concept_phrases = [p.strip() for p in re.split(r"[、。\n]", plan.concept or "") if p.strip()]
        concept_short = concept_phrases[0] if concept_phrases else plan.plan_name or ""

        hotel_name = ""
        place = ""
        if hotel_info:
            hotel_name = hotel_info.get("name", "")
            address = hotel_info.get("address", "")
            if address:
                m = re.match(r"^(.+?[都道府県])(.+?[市区町村])?", address)
                if m:
                    place = (m.group(1) or "") + (m.group(2) or "")

        benefits_str = json.dumps(benefits, ensure_ascii=False)
        label = "期間限定" if any(kw in benefits_str for kw in ["限定", "期間"]) else "公式サイト限定"

        return {
            "label": label,
            "offer_big": benefit_texts[0] if benefit_texts else plan.plan_name,
            "offer_sub": benefit_texts[1] if len(benefit_texts) > 1 else concept_short,
            "cta_p1": "空室を確認する",
            "footnote": "※詳細・条件は公式サイトにて確認",
            "feature_main": benefit_texts[0] if benefit_texts else concept_short,
            "feature_sub": benefit_texts[1] if len(benefit_texts) > 1 else (concept_phrases[1] if len(concept_phrases) > 1 else ""),
            "support_1": benefit_texts[2] if len(benefit_texts) > 2 else "",
            "price_or_tag": price_str or (plan.plan_name[:12] if plan.plan_name else ""),
            "cta_p2": "詳細を見る",
            "concept_vertical": concept_short,
            "brand": hotel_name,
            "place": place,
            "mini_info": benefit_texts[0] if benefit_texts else "",
        }

    def _build_ad_prompt_pattern1(self, text_vars: Dict[str, str], aspect_ratio: str, human_instruction: str) -> str:
        """パターン1: 数字＋CTAで予約を促進する広告プロンプト"""
        return f"""あなたは広告バナーデザイナー。旅館の予約を促進する高品質な広告画像を生成する。

# 参照画像の扱い
提供された参照画像を背景写真として使用（撮り直し不要・施設の雰囲気を保持）。
{human_instruction}
背景全体をわずかに暗く（-10〜-20%）してコントラストを確保。

# 出力
- アスペクト比：{aspect_ratio}
- 余白（セーフエリア）：四辺6%は必ず空ける
- 文字は日本語を指定どおり正確に描画（文字化け・誤字禁止）。指定外のテキスト追加禁止。

# レイアウト（予約促進型）
- 右端に縦長のCTAボタン領域（全幅の18〜22%）を確保：角丸の濃色ボタン
  - ボタン中央に「{text_vars["cta_p1"]}」（白字、太め、中央揃え）
- 残り左側に「特典パネル」（全幅の60〜70%、高さ55〜70%）：半透明の金/ベージュ系、角丸
  - パネル上部にピル型ラベル：「{text_vars["label"]}」（小さめ、中央揃え）
  - パネル中央に最大サイズで「{text_vars["offer_big"]}」（最も大きい文字、見出し）
  - 「{text_vars["offer_sub"]}」をその直下に（中サイズ、行間広め）
- 画像の最下部に「{text_vars["footnote"]}」（小さめ、セーフエリア内）

# トーン
上品・高級感。文字組は整然、要素は少なく、読みやすさ最優先。"""

    def _build_ad_prompt_pattern2(self, text_vars: Dict[str, str], aspect_ratio: str, human_instruction: str) -> str:
        """パターン2: 色面ブロックで特徴を一撃表示する広告プロンプト"""
        feature_sub_line = (
            f"  ブロック内に「{text_vars['feature_sub']}」を縦書きまたは2行縦積み（小〜中サイズ、行間広め）"
            if text_vars.get("feature_sub") else
            "  ブロック内は空白（薄いアクセントカラーのみ）"
        )
        support_line = (
            f"- 下部に「{text_vars['support_1']}」と「{text_vars['price_or_tag']}」を小さく横並び"
            if text_vars.get("support_1") else
            f"- 下部に「{text_vars['price_or_tag']}」を小さく表示"
        )
        return f"""あなたは広告バナーデザイナー。旅館の特徴を一瞬で理解させる広告画像を生成する。

# 参照画像の扱い
提供された参照画像を背景写真として使用（撮り直し不要・施設の雰囲気を保持）。
{human_instruction}
背景の主役（風呂・景色）を邪魔しない位置に文字ブロックを置くため、被写体は右側または奥側に寄せた構図に調整。

# 出力
- アスペクト比：{aspect_ratio}
- セーフエリア：四辺6%
- 文字は日本語を指定どおり正確に描画。指定外のテキスト追加禁止。

# レイアウト（色面ブロック型）
- 画面中央〜やや左に「メイン色面ブロック」（全幅40〜50%、高さ45〜60%）：不透明寄り（85〜95%）
  - ブロック内に「{text_vars['feature_main']}」を最大サイズで（白字、太字、中央揃え）
- メインブロック左に「サブ縦長ブロック」（全幅12〜18%、高さ45〜60%）：濃色（黒/濃茶）で半透明
{feature_sub_line}
{support_line}
- 右下に小さなCTAボタン「{text_vars['cta_p2']}」（角丸、目立たせすぎない）

# トーン
和・温かさ・上品。写真の空気感を残しつつ、文字はブロックで確実に読ませる。"""

    def _build_ad_prompt_pattern3(self, text_vars: Dict[str, str], aspect_ratio: str, human_instruction: str) -> str:
        """パターン3: 縦書きコンセプト＋ミニマルなブランド訴求プロンプト"""
        brand_parts = []
        if text_vars.get("place"):
            brand_parts.append(f"「{text_vars['place']}」を小さく")
        if text_vars.get("brand"):
            brand_parts.append(f"「{text_vars['brand']}」をやや大きく")
        if text_vars.get("mini_info"):
            brand_parts.append(f"「{text_vars['mini_info']}」をさらに小さく添える（入れすぎない）")
        brand_block = (
            "- 左下にブランド署名：" + "、".join(brand_parts)
            if brand_parts else
            "- 左下のブランド署名は省略"
        )
        return f"""あなたは高級旅館のアートディレクター。世界観で惹きつけるミニマルな広告画像を生成する。

# 参照画像の扱い
提供された参照画像を背景写真として使用（撮り直し不要・施設の静けさと世界観を保持）。
{human_instruction}
右側に暗めのグラデーション（右→左に透明へ）を薄く入れ、縦書きの可読性を確保。

# 出力
- アスペクト比：{aspect_ratio}
- セーフエリア：四辺8%（この型は余白多め）
- 文字は日本語を指定どおり正確に描画。指定外のテキスト追加禁止。

# レイアウト（縦書きコンセプト型）
- 右端（全幅18〜24%）に縦書きで「{text_vars['concept_vertical']}」を配置
  - 明朝体、白字、行間ゆったり、文字サイズは"読める最小限"より少し大きめ
{brand_block}
- CTAや価格は入れない（世界観優先）

# トーン
上品、静けさ、余白。広告臭を抑え、指名検索・保存される見え方を狙う。"""

    async def _create_ad_edit_prompt(self, base_prompt: str, image_type: str, plan: MarketingPlan, llm_client, hotel_info: Dict = None) -> str:
        """参照画像編集向けの広告生成プロンプトを作成（3パターン切り替え）"""
        pattern = self._select_ad_pattern(plan)
        aspect_ratio_map = {"display_wide": "16:9", "display_square": "1:1", "display_vertical": "9:16"}
        aspect_ratio = aspect_ratio_map.get(image_type, "1:1")
        text_vars = self._extract_plan_text_vars(plan, hotel_info)
        add_human = self._should_add_human_presence(plan)

        human_instruction = (
            "人物（宿泊客またはスタッフ）を自然に追加して温かみと信頼感を演出する。"
            "ただし入浴シーン・露天風呂・大浴場には絶対に人物を追加しないこと。"
            if add_human else
            "人物は追加せず、施設・空間・料理のディテールにフォーカスする。"
        )

        if pattern == 1:
            return self._build_ad_prompt_pattern1(text_vars, aspect_ratio, human_instruction)
        elif pattern == 3:
            return self._build_ad_prompt_pattern3(text_vars, aspect_ratio, human_instruction)
        else:
            return self._build_ad_prompt_pattern2(text_vars, aspect_ratio, human_instruction)

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
        llm_client,
        hotel_info: Dict = None
    ) -> Tuple[Dict, str, list]:
        """
        広告コピーを生成

        Args:
            marketing_plan: マーケティングプラン
            llm_client: LLMクライアント
            hotel_info: 施設情報（name, address）

        Returns:
            (広告コピー辞書, 生成プロンプト, warnings) のタプル
        """
        # ターゲット言語を取得
        target_language = self._get_target_language(marketing_plan)
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)

        prompt = self._create_ad_copy_generation_prompt(marketing_plan, target_language, hotel_info=hotel_info)

        system_prompt = f"""あなたは広告コピーライターの専門家です。
ホテル・旅館の予約促進広告において、クリック率と予約転換率を最大化するコピーを作成してください。

【Google 検索広告（RSA）のコピー原則】
- どの見出し3本の組み合わせでも意味が完結するよう、各見出しは独立して成立させる
- ブランド訴求・ベネフィット訴求・限定性訴求など、異なる角度から書く
- 検索意図（旅行先探し・宿泊予約）に直結したキーワードを自然に含める

【Meta 広告（Facebook / Instagram）のコピー原則】
- Primary Text の冒頭1〜2行がフィードの「続きを見る」折りたたみ前に表示される唯一のチャンス
- フック（冒頭）→ 価値提示 → CTA の構造を守る
- 3案は「感情訴求」「お得・特典訴求」「問題解決訴求」で明確に角度を変える

【重要：出力言語】
{language_instruction}
すべての広告コピーを{language_name}で作成してください。"""

        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3000
        )

        # コピーを抽出
        ad_copy = self._parse_ad_copy(response)

        # 文字数バリデーション
        warnings = self._validate_ad_copy_lengths(ad_copy)
        if warnings:
            print(f"広告コピー文字数警告: {warnings}")

        return ad_copy, prompt, warnings
    
    def _create_lp_generation_prompt(
        self,
        plan: MarketingPlan,
        cv_url: str = None,
        hotel_info: Dict = None,
        image_urls: Dict[str, str] = None,
        target_language: str = "ja",
        hotel_detail: Dict = None
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
        
        # 宿のストーリー・周辺情報セクション
        hotel_detail_section = ""
        if hotel_detail:
            story = hotel_detail.get("story", "").strip()
            highlights = hotel_detail.get("highlights", [])
            surrounding = hotel_detail.get("surrounding", {})
            surrounding_desc = surrounding.get("description", "").strip()
            attractions = surrounding.get("attractions", [])
            access = hotel_detail.get("access", "").strip()

            parts = []
            if story:
                parts.append(f"【宿のストーリー・こだわり】\n{story}")
            if highlights:
                bullet = "\n".join(f"- {h}" for h in highlights)
                parts.append(f"【宿のハイライト】\n{bullet}")
            if surrounding_desc or attractions:
                surr_lines = ["【周辺観光情報】"]
                if surrounding_desc:
                    surr_lines.append(f"エリア説明: {surrounding_desc}")
                if attractions:
                    surr_lines.append("観光スポット:")
                    for a in attractions:
                        name = a.get("name", "")
                        distance = a.get("distance", "")
                        surr_lines.append(f"  - {name}（{distance}）")
                parts.append("\n".join(surr_lines))
            if access:
                parts.append(f"【アクセス】\n{access}")

            if parts:
                hotel_detail_section = "\n\n".join(parts) + "\n"

        # 画像スロットの役割ラベル（6スロット対応）
        _LP_SLOT_LABELS = {
            "hero":        "ヒーロー画像（施設外観・玄関などメインビジュアル）",
            "feature1":    "客室紹介画像",
            "feature2":    "風呂・温泉紹介画像",
            "feature3":    "料理・食事紹介画像",
            "surrounding": "周辺観光・景観画像",
            "ambiance":    "雰囲気・内装画像",
            # 旧スロット名との後方互換
            "feature":     "特徴紹介画像",
        }

        # 画像セクション
        image_section = ""
        if image_urls and len(image_urls) > 0:
            image_section = "【使用する画像 - 必ず以下の画像をHTMLに埋め込んでください】\n"
            for img_type, img_path in image_urls.items():
                # パスをファイル名のみの相対パス（./xxx.png）に変換
                if isinstance(img_path, str) and "/hotel_images/" in img_path:
                    # 施設画像は S3 カスタムハンドラー経由のため絶対パスのまま使用
                    relative_path = img_path
                elif isinstance(img_path, str) and "/" in img_path:
                    filename = img_path.split("/")[-1]
                    relative_path = f"./{filename}"
                else:
                    relative_path = img_path
                label = _LP_SLOT_LABELS.get(img_type, img_type)
                image_section += f"- {label}: {relative_path}\n"

            image_section += """
※ 上記の画像パス（./xxx.png形式）をそのままimgタグのsrc属性に使用してください
※ ヒーロー画像はヒーローセクションの背景または大きな画像として使用
※ 客室・風呂・料理・周辺観光画像はそれぞれ対応するセクションで使用
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
        
        # デザイン方針（コンセプトから自由に設計）
        color_palette = f"""
【デザイン方針（あなたが決める）】
このプランのコンセプト「{plan.concept}」とターゲット層を読み込み、
以下を自分で設計してください：

1. カラーパレット（5色以内）
   - メイン・アクセント・背景・テキスト・サブテキスト の役割を意識して選色
   - コンセプトの感情トーン（高級感・自然感・都会感・温かみ 等）を色で表現すること

2. タイポグラフィ
   - serif / sans-serif / 混用 など、施設の個性に合うフォント系統を選ぶ
   - 見出しサイズ、行間、letter-spacing を一貫させること

3. レイアウト・セクション構成
   - 標準的なセクション（ヒーロー・特典・価格・アクセス・CTA）は含めること
   - それ以外のセクション順・構成はコンセプトに合わせて自由に変えてよい
   - 全幅・グリッド・非対称など、レイアウトスタイルも自由に選択

毎回同じデザインにならないよう、コンセプトの個性を最大限に引き出すこと。
"""
        
        return f"""
以下のマーケティングプランに基づいて、宿泊施設のランディングページを作成してください。
{hotel_section}
{hotel_detail_section}
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

【コントラスト実装パターン（必ずこの方法を使うこと）】

■ ヒーローセクション（画像上のテキスト）
.hero {{ position: relative; }}
.hero::after {{
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);  /* 写真の明るさに応じて 0.3〜0.6 で調整 */
}}
.hero-content {{ position: relative; z-index: 1; color: #ffffff; }}

■ 画像カードのテキスト（feature / surrounding セクション等）
.card-overlay {{ background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 60%); }}

■ 本文テキスト（背景色に応じた動的選択）
- 明るい背景: 黒〜濃いグレー系の文字色を選択（コントラスト比 4.5:1 以上を確保）
- 暗い背景: 白〜明るいグレー系の文字色を選択（コントラスト比 4.5:1 以上を確保）
- 上記原則を満たしている場合のみ、ニュアンスカラー（薄いグレー等）の使用を許可

■ フッターセクション
- ダーク系背景を推奨し、テキストは背景に沈まない明度を維持すること
- フッター内 CTA ボタンは背景色との差を明確にし、コントラスト比 4.5:1 以上を確保すること

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
    
    def _create_ad_copy_generation_prompt(self, plan: MarketingPlan, target_language: str = "ja", hotel_info: Dict = None) -> str:
        """広告コピー生成プロンプトを作成"""
        language_instruction = get_language_instruction(target_language)
        language_name = get_language_name(target_language)

        # 施設情報セクション
        hotel_section = ""
        if hotel_info:
            hotel_section = f"""
【施設情報】
施設名: {hotel_info.get('name', '')}
所在地: {hotel_info.get('address', '')}
"""

        # 価格帯
        price_section = ""
        if getattr(plan, 'price_range', None):
            price_section = f"価格帯: {plan.price_range}\n"

        # 競合差別化（3C分析）
        strategy_section = ""
        strategy_3c = getattr(plan, 'strategy_3c', None)
        if strategy_3c and isinstance(strategy_3c, dict):
            customer_value = strategy_3c.get('customer_value', '')
            competitor_diff = strategy_3c.get('competitor_diff', '')
            if customer_value or competitor_diff:
                strategy_section = f"""
【競合差別化ポイント（3C分析）】
顧客価値: {customer_value}
競合との差別化: {competitor_diff}
"""

        return f"""
以下のマーケティングプランに基づいて、各プラットフォーム向け広告コピーを作成してください。
{hotel_section}
【プラン情報】
プラン名: {plan.plan_name}
コンセプト: {plan.concept}
ターゲット層: {json.dumps(plan.target_audience, ensure_ascii=False)}
特典: {json.dumps(plan.benefits, ensure_ascii=False)}
{price_section}{strategy_section}
広告コピーの文字数制限は厳密に守ってください。
【Google広告 - レスポンシブ検索広告（RSA）】
- headlines: 5本生成。1件あたり15文字以内厳守
  - 見出し#1: 施設のUSP・際立った特徴（例:「源泉かけ流し 露天風呂付き客室」）
  - 見出し#2: ターゲットが得るベネフィット・体験価値（例:「日常を忘れる癒しの2日間」）
  - 見出し#3: 限定性・希少性（例:「週末限定 特別会席プラン」）
  - 見出し#4: 社会的証明・信頼性（例:「口コミ評価4.8 選ばれる宿」）
  - 見出し#5: CTA・行動促進（例:「今すぐ予約で特典付き」）
  - どの3本の組み合わせでも意味が完結するよう、各見出しは独立して成立させること
- descriptions: 3本生成。1件あたり45文字以内厳守
- path1: サービスカテゴリを表す短い語。15文字以内。
- path2: 地域名またはプラン名。15文字以内。

【Meta広告（Facebook）】
- primary_texts: 125文字以内厳守、3案生成、冒頭1〜2行をフック（読者の注意を引く文）→ 価値提示 → CTAの構造で書く。
  - 案1: 感情・ストーリー訴求（例:「〇〇に疲れていませんか？」で始める）
  - 案2: お得・特典訴求（例:「【期間限定】〇〇が無料でついてくるプラン」で始める）
  - 案3: 問題解決・ニーズ直撃（例:「〇〇をお探しなら、このプランがぴったりです」で始める）
- headlines: 3案生成。各40文字以内を目安（超過で省略されやすい）。
- descriptions: 3案生成。各20〜30文字程度を目安（表示されない配置も多い）。
- cta: "詳しくはこちら" / "今すぐ予約" / "お問い合わせ" から最適なものを1つ。

【Meta広告（Instagram）】
- primary_texts:  125文字以内厳守、3案生成、冒頭1〜2行をフック（読者の注意を引く文）→ 価値提示 → CTAの構造で書く
  （Facebookと同様の3角度で、Instagramユーザー向けに調整）
- headlines: 3案生成。各40文字以内を目安。
- descriptions: 3案生成。各20〜30文字程度を目安。
- hashtags: ホテル名・地域・体験カテゴリを含む10〜15個程度。

以下のJSON形式のみで出力してください（すべて{language_name}で記述。コードブロック不要）：
{{
    "google_ads": {{
        "headlines": [
            "見出し1（USP・特徴）",
            "見出し2（ベネフィット）",
            "見出し3（限定性）",
            "見出し4（社会的証明）",
            "見出し5（CTA）"
        ],
        "descriptions": [
            "説明文1（全角45文字以内）",
            "説明文2",
            "説明文3"
        ],
        "path1": "パス1（15文字以内）",
        "path2": "パス2（15文字以内）"
    }},
    "facebook_ads": {{
        "primary_texts": [
            "案1（感情訴求・フック→価値提示→CTA）",
            "案2（お得・特典訴求）",
            "案3（問題解決訴求）"
        ],
        "headlines": [
            "見出し案1",
            "見出し案2",
            "見出し案3"
        ],
        "descriptions": [
            "説明文案1",
            "説明文案2",
            "説明文案3"
        ],
        "cta": "詳しくはこちら"
    }},
    "instagram_ads": {{
        "primary_texts": [
            "案1（感情訴求）",
            "案2（お得・特典訴求）",
            "案3（問題解決訴求）"
        ],
        "headlines": [
            "見出し案1",
            "見出し案2",
            "見出し案3"
        ],
        "descriptions": [
            "説明文案1",
            "説明文案2",
            "説明文案3"
        ],
        "hashtags": ["#ハッシュタグ1", "#ハッシュタグ2"]
    }}
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
                "google_ads": {
                    "headlines": [
                        "特別な宿泊体験をあなたに",
                        "日常を忘れる癒しの時間",
                        "週末限定 特別プラン",
                        "口コミ高評価の人気施設",
                        "今すぐ予約で特典付き"
                    ],
                    "descriptions": [
                        "ゆったりとした客室で、くつろぎのひとときを。特別な特典もご用意しております。",
                        "心に残る宿泊体験をお届けします。ご予約はお早めに。",
                        "上質なサービスと快適な環境で、忘れられない旅をお楽しみください。"
                    ],
                    "path1": "宿泊予約",
                    "path2": "特別プラン"
                },
                "facebook_ads": {
                    "primary_texts": [
                        "日常の喧騒から離れて、本当の意味でリフレッシュしたいと思いませんか？\n\n当施設では、心と体を癒す特別な時間をご用意しています。\n\n今すぐご予約を。",
                        "【期間限定】特別プランが登場！\n\n通常より特典充実のこのプランは、数量限定です。\n\nお早めにご予約ください。",
                        "特別な宿泊先をお探しなら、このプランがぴったりです。\n\n上質なサービスと快適な環境で、忘れられない旅をお届けします。"
                    ],
                    "headlines": [
                        "特別なひとときを、あなたに",
                        "期間限定 特別プラン公開中",
                        "理想の宿泊体験がここに"
                    ],
                    "descriptions": [
                        "心に残る宿泊体験をお届けします",
                        "今だけの特別特典付きプラン",
                        "上質なサービスで癒しの時間を"
                    ],
                    "cta": "詳しくはこちら"
                },
                "instagram_ads": {
                    "primary_texts": [
                        "旅の疲れを癒す、特別な時間。\n\nここでしか体験できない宿泊プランをご用意しました。\n\n#旅行 #宿泊",
                        "【お得情報】期間限定プラン公開中！\n\n特典盛りだくさんのこのプランをお見逃しなく。\n\n詳細はリンクから。",
                        "理想の宿泊体験をお探しですか？\n\n上質な空間と温かいおもてなしで、特別な旅をご提供します。"
                    ],
                    "headlines": [
                        "特別な宿泊体験",
                        "期間限定プラン",
                        "理想の旅がここに"
                    ],
                    "descriptions": [
                        "心に残る旅をご提供",
                        "特典付き限定プラン",
                        "上質な空間でリフレッシュ"
                    ],
                    "hashtags": ["#宿泊", "#旅行", "#癒し", "#ホテル", "#旅館", "#温泉", "#観光", "#週末旅行", "#国内旅行", "#おすすめ宿"]
                }
            }

    def _validate_ad_copy_lengths(self, ad_copy: Dict) -> list:
        """
        生成された広告コピーの文字数を検証し、超過フィールドを返す
        Google: 全角1文字 = 半角2文字でカウント
        """
        warnings = []

        def hw_len(s: str) -> int:
            return sum(2 if ord(c) > 0x7F else 1 for c in s)

        for i, h in enumerate(ad_copy.get("google_ads", {}).get("headlines", [])):
            if hw_len(h) > 30:
                warnings.append(f"google_ads.headlines[{i}]: {hw_len(h)}文字（上限30）")
        for i, d in enumerate(ad_copy.get("google_ads", {}).get("descriptions", [])):
            if hw_len(d) > 90:
                warnings.append(f"google_ads.descriptions[{i}]: {hw_len(d)}文字（上限90）")

        return warnings
    
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
