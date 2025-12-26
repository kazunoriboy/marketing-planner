import json
import re
from typing import List, Dict, Any, Optional
from app.models import MarketingPlan, OperationManual, OperationChatMessage


class OperationService:
    """オペレーションマニュアル生成サービス"""
    
    def __init__(self):
        pass
    
    async def generate_chat_response(
        self,
        manual: OperationManual,
        plan: MarketingPlan,
        chat_history: List[OperationChatMessage],
        user_message: str,
        llm_client
    ) -> Dict[str, Any]:
        """
        チャットレスポンスを生成
        
        Returns:
            {
                "response": "AIの応答",
                "extracted_context": {...},  # 抽出された施設状況
                "is_ready_for_manual": bool  # マニュアル生成準備完了フラグ
            }
        """
        # チャット履歴を整形
        messages_text = self._format_chat_history(chat_history)
        
        # プラン情報を整形
        plan_info = self._format_plan_info(plan)
        
        # 現在の施設コンテキスト
        current_context = manual.facility_context or {}
        
        # プロンプト作成
        prompt = self._create_chat_prompt(
            plan_info=plan_info,
            messages_text=messages_text,
            current_context=current_context,
            user_message=user_message
        )
        
        # LLMで応答生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_chat_system_prompt(),
            max_tokens=2000
        )
        
        # レスポンスをパース
        parsed = self._parse_chat_response(response)
        
        return parsed
    
    async def generate_manual(
        self,
        manual: OperationManual,
        plan: MarketingPlan,
        chat_history: List[OperationChatMessage],
        llm_client,
        additional_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        チャット履歴と施設状況から実行マニュアルを生成
        
        Returns:
            マニュアル内容（構造化JSON）
        """
        # チャット履歴を整形
        messages_text = self._format_chat_history(chat_history)
        
        # プラン情報を整形
        plan_info = self._format_plan_info(plan)
        
        # 施設コンテキスト
        facility_context = manual.facility_context or {}
        
        # プロンプト作成
        prompt = self._create_manual_generation_prompt(
            plan_info=plan_info,
            messages_text=messages_text,
            facility_context=facility_context,
            additional_instructions=additional_instructions
        )
        
        # LLMでマニュアル生成
        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=self._get_manual_generation_system_prompt(),
            max_tokens=6000
        )
        
        # マニュアルをパース
        manual_content = self._parse_manual_response(response)
        
        return manual_content
    
    def _format_chat_history(self, chat_history: List[OperationChatMessage]) -> str:
        """チャット履歴をテキスト形式に整形"""
        if not chat_history:
            return "（まだ会話はありません）"
        
        lines = []
        for msg in chat_history:
            role_label = "ユーザー" if msg.role == "user" else "AI"
            lines.append(f"【{role_label}】\n{msg.content}")
        
        return "\n\n".join(lines)
    
    def _format_plan_info(self, plan: MarketingPlan) -> str:
        """プラン情報をテキスト形式に整形"""
        info = {
            "プラン名": plan.plan_name,
            "コンセプト": plan.concept,
            "ターゲット顧客": plan.target_audience,
            "価格帯": plan.price_range,
            "特典・特徴": plan.benefits,
            "3C分析": plan.strategy_3c,
            "PEST分析": plan.strategy_pest,
        }
        return json.dumps(info, ensure_ascii=False, indent=2)
    
    def _create_chat_prompt(
        self,
        plan_info: str,
        messages_text: str,
        current_context: Dict,
        user_message: str
    ) -> str:
        """チャット用プロンプトを作成"""
        context_str = json.dumps(current_context, ensure_ascii=False, indent=2) if current_context else "（まだ情報はありません）"
        
        return f"""
あなたは宿泊施設のマーケティングプラン実行をサポートするアドバイザーです。
以下のマーケティングプランを実行するための実行マニュアルを作成するために、施設の状況を把握する必要があります。

【承認されたマーケティングプラン】
{plan_info}

【これまでの会話】
{messages_text}

【把握している施設の状況】
{context_str}

【ユーザーの最新メッセージ】
{user_message}

---

上記を踏まえて、以下の形式でJSONで回答してください：

{{
    "response": "ユーザーへの応答（親しみやすく、具体的な質問を含める）",
    "extracted_context": {{
        // ユーザーの回答から抽出した新しい情報
        // 例: "current_tools": ["じゃらん"], "staff_count": 2, "marketing_experience": "なし"
    }},
    "is_ready_for_manual": false
}}

【重要なガイドライン】
1. 一度に聞く質問は1-2個に絞ってください
2. ユーザーが答えやすいよう、具体例を挙げてください
3. 以下の情報を段階的に把握してください：
   - 現在使っている予約サイト・SNS
   - スタッフの人数とマーケティング経験
   - 予算感（月額や初期費用）
   - 特に困っていること、苦手なこと
   - 写真撮影や文章作成のスキル
   - 対応可能な作業時間

4. 十分な情報が集まったら、is_ready_for_manual を true にして
   「マニュアルを生成する準備ができました」と伝えてください

5. extracted_context には、今回の会話で新たに判明した情報のみを含めてください
"""
    
    def _get_chat_system_prompt(self) -> str:
        """チャット用システムプロンプト"""
        return """あなたは宿泊施設のマーケティング支援アドバイザーです。

特徴：
- 親しみやすく、専門用語を避けて分かりやすく説明します
- 施設の状況を丁寧にヒアリングし、実行可能なアドバイスを提供します
- 質問は具体的で答えやすいものにします
- 施設の規模や状況に合わせた現実的な提案をします

必ず指定されたJSON形式で出力してください。"""
    
    def _parse_chat_response(self, response: str) -> Dict[str, Any]:
        """チャットレスポンスをパース"""
        try:
            # JSONを抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            return {
                "response": data.get("response", "申し訳ありません、もう一度お聞かせください。"),
                "extracted_context": data.get("extracted_context", {}),
                "is_ready_for_manual": data.get("is_ready_for_manual", False)
            }
        
        except json.JSONDecodeError as e:
            print(f"チャットレスポンスJSONパースエラー: {e}")
            return {
                "response": response,
                "extracted_context": {},
                "is_ready_for_manual": False
            }
    
    def _create_manual_generation_prompt(
        self,
        plan_info: str,
        messages_text: str,
        facility_context: Dict,
        additional_instructions: Optional[str] = None
    ) -> str:
        """マニュアル生成用プロンプトを作成"""
        context_str = json.dumps(facility_context, ensure_ascii=False, indent=2)
        additional = f"\n\n【追加の指示】\n{additional_instructions}" if additional_instructions else ""
        
        return f"""
以下の情報を基に、宿泊施設のマーケティングプラン実行マニュアルを作成してください。

【承認されたマーケティングプラン】
{plan_info}

【これまでの会話】
{messages_text}

【把握している施設の状況】
{context_str}
{additional}

---

以下のJSON形式でマニュアルを出力してください：

{{
    "title": "マニュアルのタイトル",
    "overview": "このマニュアルの概要（200文字程度）",
    "phases": [
        {{
            "name": "フェーズ名（例：準備フェーズ）",
            "description": "フェーズの説明",
            "duration": "想定期間（例：1週間）",
            "tasks": [
                {{
                    "title": "タスク名",
                    "description": "具体的な手順の説明（ステップバイステップで）",
                    "estimated_time": "所要時間の目安",
                    "responsible": "担当者の提案",
                    "tools": ["使用するツール"],
                    "tips": "成功のコツやよくある失敗"
                }}
            ]
        }}
    ],
    "timeline": "全体のタイムライン説明",
    "budget_estimate": "概算予算（施設の状況に合わせて）",
    "success_metrics": ["KPI1", "KPI2"],
    "notes": "その他の注意点やアドバイス"
}}

【重要なポイント】
1. 施設の状況（スタッフ数、スキル、予算）に合わせた現実的な内容にしてください
2. 各タスクは具体的な手順を含め、初心者でも実行できるレベルで記載してください
3. フェーズは「準備」「実行」「運用・改善」の3つに分けてください
4. 施設が苦手としている部分には特に丁寧な説明を加えてください
"""
    
    def _get_manual_generation_system_prompt(self) -> str:
        """マニュアル生成用システムプロンプト"""
        return """あなたは宿泊施設のマーケティング実行支援の専門家です。

施設の状況を踏まえた、実行可能で具体的なマニュアルを作成してください。

特徴：
- 専門用語を避け、初心者でも理解できる説明
- 具体的なステップバイステップの手順
- 施設の規模やリソースに合わせた現実的な提案
- よくある失敗とその回避方法を含める

必ず指定されたJSON形式で出力してください。"""
    
    def _parse_manual_response(self, response: str) -> Dict[str, Any]:
        """マニュアルレスポンスをパース"""
        try:
            # JSONを抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # 必須フィールドの確認
            required_fields = ["title", "overview", "phases"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"必須フィールド '{field}' が見つかりません")
            
            return data
        
        except json.JSONDecodeError as e:
            print(f"マニュアルレスポンスJSONパースエラー: {e}")
            raise ValueError(f"マニュアル生成に失敗しました: JSONの形式が不正です")
        except Exception as e:
            print(f"マニュアルレスポンス解析エラー: {e}")
            raise ValueError(f"マニュアル生成に失敗しました: {str(e)}")
    
    def get_initial_message(self, plan: MarketingPlan) -> str:
        """チャット開始時の最初のメッセージを生成"""
        return f"""こんにちは！「{plan.plan_name}」の実行マニュアルを一緒に作成していきましょう。

このプランを実現するために、まず施設の現状についていくつかお聞かせください。

**現在、宿の集客や情報発信に使っているサービスを教えていただけますか？**

例えば：
- 予約サイト（じゃらん、楽天トラベル、Booking.comなど）
- SNS（Instagram、Facebook、Xなど）
- Googleビジネスプロフィール
- 自社ホームページ

使っているものがあれば教えてください。使っていなければ「特にない」で大丈夫です！"""


