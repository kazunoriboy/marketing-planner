"""
Dify APIクライアント

Difyのワークフローを呼び出すためのクライアント。
口コミ収集ワークフロー等を実行します。
"""
import json
import os
import re
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DifyClient:
    """Dify APIクライアント"""
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.api_url = api_url or os.getenv("DIFY_API_URL", "http://localhost/v1")
        self.api_key = api_key or os.getenv("DIFY_API_KEY", "")
        
        if not self.api_key:
            raise ValueError("DIFY_API_KEY is required")
    
    @property
    def _headers(self) -> dict:
        """APIリクエスト用ヘッダー"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def run_workflow(
        self,
        inputs: dict,
        user: str = "marketing-planner",
        response_mode: str = "blocking",
    ) -> dict:
        """
        ワークフローを実行
        
        Args:
            inputs: ワークフローへの入力パラメータ
            user: ユーザー識別子
            response_mode: レスポンスモード（blocking/streaming）
        
        Returns:
            ワークフローの実行結果
        """
        url = f"{self.api_url}/workflows/run"
        
        payload = {
            "inputs": inputs,
            "response_mode": response_mode,
            "user": user,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()
    
    def _extract_json_from_text(self, text: str) -> dict:
        """
        LLMのテキスト出力からJSONを抽出
        
        Markdownのコードブロック（```json ... ```）で囲まれている場合は除去し、
        JSONとしてパースします。
        
        Args:
            text: LLMからのテキスト出力
        
        Returns:
            パースされたJSONオブジェクト
        """
        # Markdownのコードブロックを除去（```json ... ``` または ``` ... ```）
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(code_block_pattern, text)
        
        if match:
            json_str = match.group(1).strip()
        else:
            # コードブロックがない場合はそのままJSONとしてパース
            json_str = text.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            print(f"[ERROR] JSON string: {json_str[:500]}...")
            # パースに失敗した場合は空のデータを返す
            return {"reviews": [], "summary": {}}
    
    async def run_review_extraction(
        self,
        review_url: str,
        site_type: str,
        user: str = "marketing-planner",
    ) -> dict:
        """
        口コミ抽出ワークフローを実行
        
        Args:
            review_url: 口コミページのURL
            site_type: サイトタイプ（jalan/google）
            user: ユーザー識別子
        
        Returns:
            抽出された口コミデータ
        """
        print(f"[DEBUG] run_review_extraction called: url={review_url}, site_type={site_type}")
        
        inputs = {
            "review_url": review_url,
            "site_type": site_type,
        }
        
        print(f"[DEBUG] Calling Dify API: {self.api_url}/workflows/run")
        result = await self.run_workflow(inputs=inputs, user=user)
        print(f"[DEBUG] Dify raw response: {result}")
        
        # Difyのレスポンス形式からデータを抽出
        outputs = result.get("data", {}).get("outputs", {})
        
        # textフィールドにJSON文字列が含まれている場合はパース
        if "text" in outputs:
            text_content = outputs["text"]
            print(f"[DEBUG] Extracting JSON from text field...")
            parsed_data = self._extract_json_from_text(text_content)
            print(f"[DEBUG] Parsed data: {parsed_data}")
            return parsed_data
        
        # outputsに直接reviews/summaryがある場合はそのまま返す
        if "reviews" in outputs or "summary" in outputs:
            return outputs
        
        return result


def get_dify_client() -> DifyClient:
    """Difyクライアントのインスタンスを取得"""
    return DifyClient()


