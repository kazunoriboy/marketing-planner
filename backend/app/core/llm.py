import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Google Geminiを使用するLLMクライアント"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY環境変数が設定されていません")
        genai.configure(api_key=api_key)
        self.model_name = model_name  # デフォルトはGemini 2.5 Flash-Lite
    
    async def generate_text(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> str:
        """
        テキストを生成
        
        Args:
            user_prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
            max_tokens: 最大トークン数
            temperature: 温度パラメータ（0.0-2.0）
        
        Returns:
            生成されたテキスト
        """
        try:
            # モデルを初期化
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt if system_prompt else None
            )
            
            # 生成設定
            generation_config = genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            
            # テキスト生成
            response = model.generate_content(
                user_prompt,
                generation_config=generation_config
            )
            
            # レスポンスからテキストを抽出
            if response.text:
                return response.text
            else:
                return ""
                
        except Exception as e:
            raise Exception(f"LLM生成エラー: {str(e)}")
    
    async def generate_structured_output(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> str:
        """
        構造化されたJSON出力を生成
        
        Args:
            user_prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
            max_tokens: 最大トークン数
        
        Returns:
            JSON文字列
        """
        # JSON出力を明示的に指示
        enhanced_prompt = f"{user_prompt}\n\n必ずJSON形式で出力してください。マークダウンのコードブロックは使わず、純粋なJSONのみを返してください。"
        
        return await self.generate_text(
            user_prompt=enhanced_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.3  # より決定論的な出力のため温度を低く
        )


# シングルトンインスタンス
_llm_client: Optional[LLMClient] = None


def get_llm_client(model_name: str = "gemini-2.5-flash-lite") -> LLMClient:
    """
    LLMクライアントのシングルトンインスタンスを取得
    
    Args:
        model_name: 使用するGeminiモデル名（デフォルト: gemini-2.5-flash-lite）
    
    Returns:
        LLMクライアントインスタンス
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(model_name=model_name)
    return _llm_client


async def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = "gemini-2.5-flash-lite",
    max_tokens: int = 4096,
    temperature: float = 1.0
) -> str:
    """
    テキストを生成（便利関数）
    
    Args:
        system_prompt: システムプロンプト
        user_prompt: ユーザープロンプト
        model: 使用するモデル名
        max_tokens: 最大トークン数
        temperature: 温度パラメータ
    
    Returns:
        生成されたテキスト
    """
    client = get_llm_client(model_name=model)
    return await client.generate_text(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )


