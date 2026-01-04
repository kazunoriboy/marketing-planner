import os
import base64
from typing import Optional, Tuple
import google.generativeai as genai
from google.generativeai import types
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
    
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9"
    ) -> Tuple[bytes, str]:
        """
        テキストから画像を生成
        
        Args:
            prompt: 画像生成プロンプト
            aspect_ratio: アスペクト比（"1:1", "16:9", "9:16" など）
        
        Returns:
            (画像バイナリデータ, MIMEタイプ) のタプル
        
        Note:
            画像生成に使用するモデルはクライアント初期化時のmodel_nameを使用
            (例: gemini-3-pro-image-preview)
        """
        try:
            # 新しい google-genai パッケージを使用
            from google import genai as genai_new
            from google.genai import types as genai_types
            
            # クライアントを初期化（API Keyは環境変数から自動取得）
            client = genai_new.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # 画像生成（インスタンスのmodel_nameを使用）
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
                config=genai_types.GenerateContentConfig(
                    response_modalities=["Text", "Image"]
                )
            )
            
            # レスポンスから画像データを抽出
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    return part.inline_data.data, part.inline_data.mime_type
            
            raise Exception("画像が生成されませんでした")
                
        except Exception as e:
            raise Exception(f"画像生成エラー: {str(e)}")


# モデル名ごとのインスタンスキャッシュ
_llm_clients: dict[str, LLMClient] = {}


def get_llm_client(model_name: str = "gemini-2.5-flash-lite") -> LLMClient:
    """
    LLMクライアントのインスタンスを取得（モデル名ごとにキャッシュ）
    
    Args:
        model_name: 使用するGeminiモデル名（デフォルト: gemini-2.5-flash-lite）
    
    Returns:
        LLMクライアントインスタンス
    """
    global _llm_clients
    if model_name not in _llm_clients:
        _llm_clients[model_name] = LLMClient(model_name=model_name)
    return _llm_clients[model_name]


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


