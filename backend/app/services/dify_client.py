"""
Dify APIクライアント

Difyのワークフローを呼び出すためのクライアント。
口コミ収集ワークフロー等を実行します。
"""
import os
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
        inputs = {
            "review_url": review_url,
            "site_type": site_type,
        }
        
        result = await self.run_workflow(inputs=inputs, user=user)
        
        # Difyのレスポンス形式からデータを抽出
        if result.get("data", {}).get("outputs"):
            return result["data"]["outputs"]
        
        return result


def get_dify_client() -> DifyClient:
    """Difyクライアントのインスタンスを取得"""
    return DifyClient()

