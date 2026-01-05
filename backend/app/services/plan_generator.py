import json
import re
from typing import List, Dict, Any, Literal, Optional
from app.models import AnalysisSession, MarketingPlan, ExistingPlan


# セクション名の日本語マッピング
SECTION_LABELS = {
    "concept": "コンセプト",
    "target_audience": "ターゲット顧客",
    "price_range": "価格帯",
    "benefits": "特典・特徴",
}


class PlanGenerator:
    """マーケティングプラン生成サービス"""
    
    def __init__(self):
        pass
    
    async def edit_section(
        self,
        plan: MarketingPlan,
        section: Literal["concept", "target_audience", "price_range", "benefits"],
        instruction: str,
        llm_client,
        analysis_session: Optional[Any] = None,
        hotel_assets: Optional[Dict] = None,
        existing_plans: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        プランの特定セクションを修正指示に基づいて、プラン全体を調整して再生成
        
        Args:
            plan: 現在のマーケティングプラン
            section: 修正の起点となるセクション
            instruction: 修正指示
            llm_client: LLMクライアント
            analysis_session: 分析セッション（ペルソナ、顧客データなど）
            hotel_assets: 施設の資産情報
            existing_plans: 既存プランのリスト
        
        Returns:
            修正されたプラン全体のデータ
        """
        # プロンプトを作成
        prompt = self._create_plan_edit_prompt(
            plan=plan,
            section=section,
            instruction=instruction,
            analysis_session=analysis_session,
            hotel_assets=hotel_assets,
            existing_plans=existing_plans
        )
        
        # LLMで再生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_plan_edit_system_prompt(
                has_analysis=analysis_session is not None,
                has_assets=hotel_assets is not None
            ),
            max_tokens=4000
        )
        
        # レスポンスをパース
        edited_plan = self._parse_plan_edit_response(response)
        
        return edited_plan
    
    def _create_plan_edit_prompt(
        self,
        plan: MarketingPlan,
        section: str,
        instruction: str,
        analysis_session: Optional[Any] = None,
        hotel_assets: Optional[Dict] = None,
        existing_plans: Optional[List[Dict]] = None
    ) -> str:
        """プラン全体編集用のプロンプトを作成"""
        section_label = SECTION_LABELS.get(section, section)
        
        # 現在のプラン全体をJSON形式で表示
        current_plan = {
            "plan_name": plan.plan_name,
            "concept": plan.concept,
            "target_audience": plan.target_audience,
            "price_range": plan.price_range,
            "benefits": plan.benefits,
            "strategy_3c": plan.strategy_3c,
            "strategy_pest": plan.strategy_pest,
        }
        current_plan_str = json.dumps(current_plan, ensure_ascii=False, indent=2)
        
        # 分析データのサマリー
        analysis_context = ""
        if analysis_session:
            analysis_parts = []
            
            # ペルソナ情報
            if hasattr(analysis_session, 'personas') and analysis_session.personas:
                analysis_parts.append("\n【ターゲットペルソナ】")
                for i, persona in enumerate(analysis_session.personas, 1):
                    persona_name = persona.get('name', f'ペルソナ{i}')
                    analysis_parts.append(f"■ {persona_name}")
                    if persona.get('age_range'):
                        analysis_parts.append(f"  - 年齢層: {persona['age_range']}")
                    if persona.get('travel_purpose'):
                        analysis_parts.append(f"  - 旅行目的: {persona['travel_purpose']}")
                    if persona.get('values'):
                        analysis_parts.append(f"  - 重視すること: {', '.join(persona['values'][:3])}")
                    if persona.get('pain_points'):
                        analysis_parts.append(f"  - 悩み: {', '.join(persona['pain_points'][:3])}")
            
            # 顧客データの分析結果
            if hasattr(analysis_session, 'csv_insights') and analysis_session.csv_insights:
                analysis_parts.append(f"\n【顧客データ分析の知見】\n{analysis_session.csv_insights[:500]}")
            
            # 口コミ分析結果
            if hasattr(analysis_session, 'reviews_summary') and analysis_session.reviews_summary:
                reviews = analysis_session.reviews_summary
                if isinstance(reviews, dict):
                    if reviews.get('strengths'):
                        analysis_parts.append(f"\n【口コミで評価されている点】\n{', '.join(reviews['strengths'][:5])}")
                    if reviews.get('weaknesses'):
                        analysis_parts.append(f"\n【口コミで改善点とされている点】\n{', '.join(reviews['weaknesses'][:5])}")
            
            if analysis_parts:
                analysis_context = "\n".join(analysis_parts)
        
        # 施設の資産情報
        assets_context = ""
        if hotel_assets:
            asset_parts = ["\n【施設が提供できる資産】"]
            asset_categories = {
                "room_amenities": "部屋の設備",
                "shared_facilities": "共有施設",
                "dining": "料理・食事",
                "services": "サービス",
                "experiences": "体験",
            }
            for key, label in asset_categories.items():
                items = hotel_assets.get(key, [])
                if items:
                    asset_parts.append(f"■ {label}: {', '.join(items)}")
            if len(asset_parts) > 1:
                assets_context = "\n".join(asset_parts)
        
        # 既存プラン情報
        existing_context = ""
        if existing_plans and len(existing_plans) > 0:
            existing_parts = ["\n【現在運用中の既存プラン】"]
            for ep in existing_plans[:3]:
                existing_parts.append(f"■ {ep.get('plan_title', '不明')}: {ep.get('plan_description', '')[:100]}")
            existing_context = "\n".join(existing_parts)
        
        # コンテキスト情報をまとめる
        context_info = ""
        if analysis_context or assets_context or existing_context:
            context_info = f"""
【重要：以下の情報を考慮してプランを修正してください】
{analysis_context}
{assets_context}
{existing_context}
"""
        
        return f"""
以下のマーケティングプランを修正してください。
{context_info}
【現在のプラン】
{current_plan_str}

【修正指示】
「{section_label}」について: {instruction}

【重要な注意事項】
- 上記の修正指示に基づいて、プラン全体の一貫性を保つように調整してください
- プラン名、コンセプト、ターゲット顧客、価格帯の根拠、特典など、関連するすべての箇所を修正してください
- 修正指示に関係のない部分でも、一貫性を保つために必要な調整を行ってください
- 3C分析とPEST分析も必要に応じて調整してください
{"- ペルソナや顧客分析の情報が提供されている場合は、それらと整合性のある修正を行ってください" if analysis_context else ""}
{"- 施設の資産情報が提供されている場合は、実際に提供可能なサービス・設備の範囲内で修正を行ってください" if assets_context else ""}

【出力形式】
以下のJSON形式で出力してください：
{{
    "plan_name": "修正後のプラン名",
    "concept": "修正後のコンセプト（200文字程度）",
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
"""
    
    def _get_plan_edit_system_prompt(self, has_analysis: bool = False, has_assets: bool = False) -> str:
        """プラン編集用のシステムプロンプト"""
        base_prompt = """あなたは宿泊業界の経験豊富なマーケティングストラテジストです。
ユーザーの修正指示に従って、マーケティングプラン全体を調整してください。

重要なポイント：
1. 修正指示に基づいて、プラン全体の一貫性を保つように調整してください
2. プラン名、コンセプト、ターゲット、価格根拠、特典など、関連するすべての箇所を修正してください
3. 実現可能で具体的な内容にしてください
4. 必ず指定されたJSON形式で出力してください"""
        
        if has_analysis:
            base_prompt += """
5. 提供されたペルソナ情報や顧客分析結果を十分に考慮し、ターゲット顧客のニーズや価値観に沿った内容にしてください
6. 口コミで評価されている点は積極的に活用し、改善点とされている点は避けるか対策を含めてください"""
        
        if has_assets:
            base_prompt += """
7. 施設の資産情報を参考に、実際に提供可能なサービスや設備の範囲内でプランを作成してください
8. 施設が提供できないサービスや設備は含めないでください"""
        
        return base_prompt
    
    def _parse_plan_edit_response(self, response: str) -> Dict[str, Any]:
        """プラン編集レスポンスをパース"""
        try:
            # JSONを抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # 必須フィールドの確認
            required_fields = ["plan_name", "concept", "target_audience", "price_range", "benefits", "strategy_3c", "strategy_pest"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"必須フィールド '{field}' が見つかりません")
            
            return data
        
        except json.JSONDecodeError as e:
            print(f"プラン編集レスポンスJSONパースエラー: {e}")
            raise ValueError(f"修正結果の解析に失敗しました: JSONの形式が不正です")
        except Exception as e:
            print(f"プラン編集レスポンス解析エラー: {e}")
            raise ValueError(f"修正結果の解析に失敗しました: {str(e)}")
    
    async def generate_plans(
        self,
        analysis_session: AnalysisSession,
        num_plans: int,
        llm_client,
        persona_index: int = None
    ) -> List[Dict]:
        """
        分析結果からマーケティングプランを生成
        
        Args:
            analysis_session: 分析セッション
            num_plans: 生成するプラン数
            llm_client: LLMクライアント
            persona_index: 特定のペルソナを指定する場合のインデックス（0始まり）
        
        Returns:
            プラン情報のリスト
        """
        # 分析結果をまとめる（ペルソナ情報は後で個別に追加）
        analysis_summary = self._create_analysis_summary(analysis_session, exclude_personas=True)
        
        # ペルソナ情報を取得
        personas = analysis_session.personas if analysis_session.personas else []
        
        # 特定のペルソナが指定されている場合
        target_persona = None
        if persona_index is not None and personas and 0 <= persona_index < len(personas):
            target_persona = personas[persona_index]
        
        # プラン生成プロンプトを作成
        prompt = self._create_plan_generation_prompt(
            analysis_summary, 
            num_plans, 
            target_persona=target_persona
        )
        
        # LLMでプランを生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_system_prompt(has_persona=target_persona is not None),
            max_tokens=8000
        )
        
        # JSONをパース
        plans = self._parse_plans_response(response)
        
        return plans
    
    async def generate_plans_from_existing(
        self,
        existing_plan: ExistingPlan,
        target_persona: Optional[Dict] = None,
        num_plans: int = 3,
        llm_client = None
    ) -> List[Dict]:
        """
        既存プランをベースに、見せ方を変えたマーケティングプランを生成
        
        Args:
            existing_plan: 既存プラン（宿が現在運用中のプラン）
            target_persona: ターゲットペルソナ（オプション）
            num_plans: 生成するプラン数
            llm_client: LLMクライアント
        
        Returns:
            プラン情報のリスト
        """
        # プラン生成プロンプトを作成
        prompt = self._create_existing_plan_prompt(
            existing_plan=existing_plan,
            target_persona=target_persona,
            num_plans=num_plans
        )
        
        # LLMでプランを生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_existing_plan_system_prompt(has_persona=target_persona is not None),
            max_tokens=8000
        )
        
        # JSONをパース
        plans = self._parse_plans_response(response)
        
        return plans
    
    async def generate_plans_from_assets(
        self,
        hotel_assets: Dict,
        existing_plans: List[Dict],
        target_persona: Optional[Dict] = None,
        num_plans: int = 3,
        llm_client = None
    ) -> List[Dict]:
        """
        施設の資産＋既存プラン全体から、見せ方を変えたマーケティングプランを生成
        
        Args:
            hotel_assets: 施設の資産（カテゴリ別）
            existing_plans: 既存プランのリスト
            target_persona: ターゲットペルソナ（オプション）
            num_plans: 生成するプラン数
            llm_client: LLMクライアント
        
        Returns:
            プラン情報のリスト
        """
        # プラン生成プロンプトを作成
        prompt = self._create_assets_based_prompt(
            hotel_assets=hotel_assets,
            existing_plans=existing_plans,
            target_persona=target_persona,
            num_plans=num_plans
        )
        
        # LLMでプランを生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_assets_based_system_prompt(has_persona=target_persona is not None),
            max_tokens=8000
        )
        
        # JSONをパース
        plans = self._parse_plans_response(response)
        
        return plans
    
    def _create_assets_based_prompt(
        self,
        hotel_assets: Dict,
        existing_plans: List[Dict],
        target_persona: Optional[Dict],
        num_plans: int
    ) -> str:
        """施設の資産＋既存プランベースのプラン生成プロンプトを作成"""
        
        # 施設の資産情報をまとめる
        assets_info = "【施設が提供できる資産】\n"
        
        asset_categories = {
            "room_amenities": "部屋の設備・備品",
            "shared_facilities": "共有施設",
            "dining": "料理・食事",
            "services": "サービス",
            "experiences": "体験・アクティビティ",
        }
        
        for key, label in asset_categories.items():
            items = hotel_assets.get(key, [])
            if items:
                assets_info += f"■ {label}: {', '.join(items)}\n"
        
        # 既存プラン情報をまとめる
        plans_info = ""
        if existing_plans:
            plans_info = "\n【現在運用中のプラン】\n"
            for i, ep in enumerate(existing_plans, 1):
                plans_info += f"\n--- プラン{i}: {ep.get('plan_title', '不明')} ---\n"
                plans_info += f"説明: {ep.get('plan_description', '')}\n"
                if ep.get('room_facilities'):
                    plans_info += f"部屋の設備: {', '.join(ep['room_facilities'])}\n"
                if ep.get('hotel_assets'):
                    plans_info += f"活用資産: {', '.join(ep['hotel_assets'])}\n"
                if ep.get('price_info'):
                    price = ep['price_info']
                    plans_info += f"価格帯: {price.get('min', '?')}〜{price.get('max', '?')}円\n"
                if ep.get('meal_info'):
                    meal = ep['meal_info']
                    if meal.get('breakfast'):
                        plans_info += f"朝食: {meal['breakfast']}\n"
                    if meal.get('dinner'):
                        plans_info += f"夕食: {meal['dinner']}\n"
        
        # ペルソナ情報
        persona_instruction = ""
        if target_persona:
            persona_json = json.dumps(target_persona, ensure_ascii=False, indent=2)
            
            persona_instruction = f"""
【ターゲットペルソナ】
以下のペルソナに刺さるマーケティングプランを提案してください。

{persona_json}

【ポイント】
- 施設の既存資産を最大限に活かす
- ペルソナの「旅行目的」「重視すること」「悩み」に響くように訴求
- 同じ資産でも、見せ方や組み合わせ方で異なる価値を提供できる
- {num_plans}つの異なる切り口でプランを提案
"""
        else:
            persona_instruction = f"""
【指示】
施設の資産を活かした{num_plans}つのマーケティングプランを提案してください。
- 各プランは異なるターゲット層や訴求ポイントを持つこと
- 既存の資産を最大限に活用し、新規投資を最小限に抑える
"""
        
        return f"""
以下の施設情報を元に、見せ方・訴求方法を変えたマーケティングプランを{num_plans}つ提案してください。

{assets_info}
{plans_info}

{persona_instruction}

【重要】
- 既存の設備やサービスを変えずに、見せ方・伝え方を変える
- 新たな設備投資やオペレーション変更が不要なプランを優先
- 同じ「実体」でも、ターゲットによって異なる価値として見せられる
- 既存プランがある場合は、それらの良い点を活かしつつ新しい訴求を考える

各プランについて、以下の項目を含むJSON形式で出力してください：

{{
    "plans": [
        {{
            "plan_name": "プラン名（訴求ポイントを表す魅力的な名前）",
            "concept": "プランのコンセプト（200文字程度、どんな価値を提供するか）",
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
                "unique_value": "独自の価値提案（既存設備をどう見せるか）",
                "amenities": ["アメニティ1", "アメニティ2"]
            }},
            "strategy_3c": {{
                "customer": "顧客分析",
                "competitor": "競合分析",
                "company": "自社の強み（既存資産の活用）"
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

【プラン名の注意事項】
- ペルソナの名前（人名）は絶対にプラン名に含めないでください
- 体験価値や訴求ポイントを表す魅力的な名前をつけてください
"""
    
    def _get_assets_based_system_prompt(self, has_persona: bool = False) -> str:
        """施設の資産ベース生成用のシステムプロンプト"""
        base_prompt = """あなたは宿泊業界の経験豊富なマーケティングストラテジストです。
施設の既存資産を活かしながら、見せ方や訴求方法を変えることで、
異なる顧客層にアピールできるプランを提案してください。

重要なポイント：
1. 既存の設備やサービスを変えずに、見せ方・伝え方を変える
2. 新たな投資やオペレーション変更が最小限で済むプランを提案
3. 同じ「実体」でも、ターゲットによって異なる価値として見せられる
4. キャッチコピーや訴求ポイントを工夫して、異なる魅力を引き出す"""
        
        if has_persona:
            persona_instruction = """

【ペルソナ対応の重要ポイント】
- 指定されたペルソナの「悩み」「価値観」「旅行目的」を深く理解する
- 既存設備の中から、そのペルソナに響く要素を見つけ出す
- 同じ設備でも、ペルソナによって異なる価値として訴求する"""
            return base_prompt + persona_instruction
        
        return base_prompt
    
    def _create_existing_plan_prompt(
        self,
        existing_plan: ExistingPlan,
        target_persona: Optional[Dict],
        num_plans: int
    ) -> str:
        """既存プランベースのプラン生成プロンプトを作成"""
        
        # 既存プランの情報をまとめる
        existing_plan_info = f"""
【既存プラン情報】
■ プランタイトル: {existing_plan.plan_title}
■ プラン説明: {existing_plan.plan_description}
■ 部屋の施設・設備: {', '.join(existing_plan.room_facilities) if existing_plan.room_facilities else 'なし'}
■ 宿の活用可能な資産: {', '.join(existing_plan.hotel_assets) if existing_plan.hotel_assets else 'なし'}
"""
        
        if existing_plan.price_info:
            price_info = existing_plan.price_info
            existing_plan_info += f"■ 価格帯: {price_info.get('min', '?')}円〜{price_info.get('max', '?')}円（標準: {price_info.get('standard', '?')}円）\n"
        
        if existing_plan.meal_info:
            meal = existing_plan.meal_info
            meal_parts = []
            if meal.get('breakfast'):
                meal_parts.append(f"朝食: {meal['breakfast']}")
            if meal.get('dinner'):
                meal_parts.append(f"夕食: {meal['dinner']}")
            if meal.get('options'):
                meal_parts.append(f"オプション: {', '.join(meal['options'])}")
            if meal_parts:
                existing_plan_info += f"■ 食事: {', '.join(meal_parts)}\n"
        
        if existing_plan.notes:
            existing_plan_info += f"■ 特記事項: {existing_plan.notes}\n"
        
        # ペルソナ情報
        persona_instruction = ""
        if target_persona:
            persona_name = target_persona.get('name', 'ターゲット顧客')
            persona_json = json.dumps(target_persona, ensure_ascii=False, indent=2)
            
            persona_instruction = f"""
【ターゲットペルソナ】
以下のペルソナに刺さるように、既存プランの見せ方を変えてください。

{persona_json}

【ポイント】
- 既存プランの「実体」（設備・サービス内容）は変えない
- ペルソナの「旅行目的」「重視すること」「悩み」に響くように訴求方法を変える
- 同じ設備でも、ペルソナによって異なる価値として見せられる
  例: 「露天風呂」→ ビジネスパーソンには「疲れを癒す」、カップルには「ロマンチックな時間」
- {num_plans}つの異なる切り口でプランを提案してください
"""
        else:
            persona_instruction = f"""
【指示】
この既存プランの見せ方を変えた{num_plans}つのマーケティングプランを提案してください。
- 既存プランの「実体」（設備・サービス内容）は変えない
- 異なるターゲット層や訴求ポイントで、同じプランを魅力的に見せる方法を考えてください
"""
        
        return f"""
以下の既存プランをベースに、見せ方・訴求方法を変えたマーケティングプランを{num_plans}つ提案してください。

{existing_plan_info}

{persona_instruction}

【重要】
- 既存の設備やサービスを最大限に活かしてください
- 新たな設備投資や大きなオペレーション変更が不要なプランにしてください
- 同じ「実体」でも、見せ方やキャッチコピーを変えることで異なる魅力を伝えられます

各プランについて、以下の項目を含むJSON形式で出力してください：

{{
    "plans": [
        {{
            "plan_name": "プラン名（訴求ポイントを表す魅力的な名前）",
            "concept": "プランのコンセプト（200文字程度、どんな価値を提供するか）",
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
                "unique_value": "独自の価値提案（既存設備をどう見せるか）",
                "amenities": ["アメニティ1", "アメニティ2"]
            }},
            "strategy_3c": {{
                "customer": "顧客分析",
                "competitor": "競合分析",
                "company": "自社の強み（既存資産の活用）"
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

【プラン名の注意事項】
- ペルソナの名前（人名）は絶対にプラン名に含めないでください
- 体験価値や訴求ポイントを表す魅力的な名前をつけてください
"""
    
    def _get_existing_plan_system_prompt(self, has_persona: bool = False) -> str:
        """既存プランベース生成用のシステムプロンプト"""
        base_prompt = """あなたは宿泊業界の経験豊富なマーケティングストラテジストです。
既存のプランや設備を活かしながら、見せ方や訴求方法を変えることで、
異なる顧客層にアピールできるプランを提案してください。

重要なポイント：
1. 既存の設備やサービスを変えずに、見せ方・伝え方を変える
2. 新たな投資やオペレーション変更が最小限で済むプランを提案
3. 同じ「実体」でも、ターゲットによって異なる価値として見せられる
4. キャッチコピーや訴求ポイントを工夫して、異なる魅力を引き出す"""
        
        if has_persona:
            persona_instruction = """

【ペルソナ対応の重要ポイント】
- 指定されたペルソナの「悩み」「価値観」「旅行目的」を深く理解する
- 既存設備の中から、そのペルソナに響く要素を見つけ出す
- 同じ設備でも、ペルソナによって異なる価値として訴求する
  例: 「大浴場」
    * ビジネスパーソン → 「一日の疲れを流す癒しの時間」
    * 家族連れ → 「子供と一緒に楽しめる広々空間」
    * カップル → 「二人でゆったり過ごす特別な時間」"""
            return base_prompt + persona_instruction
        
        return base_prompt
    
    def _create_analysis_summary(self, session: AnalysisSession, exclude_personas: bool = False) -> str:
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
        
        # ペルソナ情報（exclude_personasがTrueの場合はスキップ）
        if not exclude_personas and session.personas and len(session.personas) > 0:
            summary_parts.append("\n【ターゲットペルソナ】")
            summary_parts.append("以下のペルソナが特定されています。各ペルソナに対して効果的なプランを提案してください。")
            for i, persona in enumerate(session.personas, 1):
                summary_parts.append(f"\n--- ペルソナ{i}: {persona.get('name', f'顧客像{i}')} ---")
                summary_parts.append(json.dumps(persona, ensure_ascii=False, indent=2))
        
        return "\n".join(summary_parts)
    
    def _create_plan_generation_prompt(self, analysis_summary: str, num_plans: int, target_persona: dict = None) -> str:
        """プラン生成プロンプトを作成"""
        
        # 特定のペルソナが指定されている場合
        if target_persona:
            persona_name = target_persona.get('name', 'ターゲット顧客')
            persona_json = json.dumps(target_persona, ensure_ascii=False, indent=2)
            
            persona_instruction = f"""
【ターゲットペルソナ】
以下のペルソナに対して、{num_plans}つの異なる切り口でマーケティングプランを提案してください。

{persona_json}

【プラン生成のポイント】
このペルソナ（{persona_name}）に刺さる{num_plans}つの異なるアプローチを提案してください：

1. **切り口を変える**: 同じペルソナでも、異なる訴求軸でアプローチできます
   - 価格・お得感訴求（コスパ重視）
   - 体験価値訴求（特別な体験・思い出）
   - 利便性訴求（手軽さ・時短）
   - 癒し・リラックス訴求
   - 特別感・プレミアム訴求
   - アクティビティ・アドベンチャー訴求
   
2. **ペルソナの異なるニーズに注目**: 
   - 「旅行目的」から導かれるプラン
   - 「悩み・課題（pain_points）」を解決するプラン
   - 「重視すること（values）」を満たすプラン

3. **価格帯を変える**: ペルソナの予算帯の中で、エントリー〜プレミアムまで幅を持たせる

4. **特典・サービスを変える**: 同じコンセプトでも、異なる特典パッケージを用意

各プランは明確に差別化し、このペルソナが「どのプランも魅力的だけど、どれにしよう？」と迷うような選択肢を提供してください。
"""
        else:
            persona_instruction = f"""
{num_plans}つの具体的なマーケティングプランを提案してください。
各プランは差別化され、異なるターゲット層や戦略を持つようにしてください。
"""
        
        return f"""
以下の分析結果に基づいて、マーケティングプランを提案してください。

{analysis_summary}

{persona_instruction}

各プランについて、以下の項目を含むJSON形式で出力してください：

{{
    "plans": [
        {{
            "plan_name": "プラン名（訴求ポイントや体験価値を表す魅力的な名前。例：『週末リフレッシュステイ』『贅沢おこもりプラン』『アクティブ満喫プラン』など）",
            "concept": "プランのコンセプト（200文字程度、ターゲットの課題解決を明確に）",
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

【プラン名の注意事項】
- ペルソナの名前（人名）は絶対にプラン名に含めないでください
- 代わりに、そのペルソナが求める体験や価値を表現したキャッチーな名前をつけてください
- 例：「癒しの温泉リトリート」「アクティブ家族旅プラン」「記念日を彩るプレミアムステイ」など
"""
    
    def _get_system_prompt(self, has_persona: bool = False) -> str:
        """システムプロンプトを取得"""
        base_prompt = """あなたは宿泊業界の経験豊富なマーケティングストラテジストです。
データに基づいた実践的で、すぐに実行可能なマーケティングプランを提案してください。
3C分析（Customer, Competitor, Company）とPEST分析（Political, Economic, Social, Technological）を
活用した戦略的なプランを作成してください。"""
        
        if has_persona:
            persona_instruction = """

【単一ペルソナに対する複数プラン戦略】
- 指定されたペルソナに対して、複数の異なる切り口でプランを提案してください
- 同じペルソナでも、訴求ポイントやアプローチ方法によって響くプランは異なります
- 例えば「忙しいビジネスパーソン」に対しても:
  * 「短時間で最大限リフレッシュ」という時短訴求
  * 「贅沢な自分へのご褒美」というプレミアム訴求
  * 「コスパ良く疲れを癒す」というお得感訴求
  など、異なるアプローチが可能です
- ペルソナの悩み（pain_points）それぞれに対応するプランを考えてください
- 価格帯にも幅を持たせ、選択肢を提供してください

【プラン名の命名ルール】
- プラン名にペルソナの名前（人名）は絶対に含めないでください
- 「〇〇さん向けプラン」のような名前は禁止です
- 代わりに、体験価値や訴求ポイントを表す魅力的な名前をつけてください
  例：「癒しの温泉リトリート」「お得に満喫プラン」「プレミアムおこもりステイ」など"""
            return base_prompt + persona_instruction
        
        return base_prompt
    
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


