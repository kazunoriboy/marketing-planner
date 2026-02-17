import os
import base64
import asyncio
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from google.generativeai import types
from dotenv import load_dotenv

load_dotenv()

# 画像生成用のスレッドプール（同期APIをブロックせずに実行するため）
_image_executor = ThreadPoolExecutor(max_workers=4)


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
        テキストを生成（非同期版）
        
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
            
            # 非同期でテキスト生成（イベントループをブロックしない）
            response = await model.generate_content_async(
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
    
    async def generate_text_with_grounding(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        enable_grounding: bool = True
    ) -> Tuple[str, Optional[dict]]:
        """
        Grounding with Google Searchを有効化したテキスト生成
        
        Args:
            user_prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
            max_tokens: 最大トークン数
            temperature: 温度パラメータ（Grounding使用時は1.0推奨）
            enable_grounding: Groundingを有効化するか
        
        Returns:
            (生成されたテキスト, groundingメタデータ) のタプル
        """
        def _generate_with_grounding_sync():
            """同期的なgrounding処理（google.genaiパッケージを使用）"""
            from google import genai as genai_new
            from google.genai import types as genai_types
            
            # クライアントを初期化（API Keyは環境変数から自動取得）
            client = genai_new.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # Groundingツールを設定
            tools = None
            if enable_grounding:
                tools = [genai_types.Tool(google_search=genai_types.GoogleSearch())]
            
            # 生成設定
            config = genai_types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                tools=tools if enable_grounding else None,
                system_instruction=system_prompt if system_prompt else None
            )
            
            # コンテンツ生成
            response = client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config
            )
            
            # レスポンスからテキストを抽出
            text = ""
            if hasattr(response, 'text') and response.text:
                text = response.text
            elif hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate and hasattr(candidate, 'content'):
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text += part.text
                    elif hasattr(candidate.content, 'text') and candidate.content.text:
                        text = candidate.content.text
            
            # Groundingメタデータを抽出
            grounding_metadata = None
            if enable_grounding and hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate and hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding_metadata = {
                        'web_search_queries': [],
                        'grounding_chunks': [],
                        'grounding_supports': []
                    }
                    
                    # 検索クエリを抽出
                    web_search_queries = getattr(candidate.grounding_metadata, 'web_search_queries', None)
                    if web_search_queries is not None:
                        try:
                            # web_search_queriesがイテレート可能か確認
                            if hasattr(web_search_queries, '__iter__') and not isinstance(web_search_queries, (str, bytes)):
                                grounding_metadata['web_search_queries'] = [
                                    q.query if hasattr(q, 'query') else str(q)
                                    for q in web_search_queries
                                ]
                            else:
                                grounding_metadata['web_search_queries'] = []
                        except (TypeError, AttributeError) as e:
                            grounding_metadata['web_search_queries'] = []
                    
                    # ソース情報を抽出
                    grounding_chunks = getattr(candidate.grounding_metadata, 'grounding_chunks', None)
                    if grounding_chunks is not None:
                        grounding_metadata['grounding_chunks'] = []
                        try:
                            # grounding_chunksがイテレート可能か確認
                            if hasattr(grounding_chunks, '__iter__') and not isinstance(grounding_chunks, (str, bytes)):
                                for chunk in grounding_chunks:
                                    if isinstance(chunk, dict):
                                        grounding_metadata['grounding_chunks'].append({
                                            'uri': chunk.get('uri', ''),
                                            'title': chunk.get('title', '')
                                        })
                                    else:
                                        grounding_metadata['grounding_chunks'].append({
                                            'uri': getattr(chunk, 'uri', ''),
                                            'title': getattr(chunk, 'title', '')
                                        })
                        except (TypeError, AttributeError) as e:
                            grounding_metadata['grounding_chunks'] = []
            
            return text, grounding_metadata
        
        try:
            # スレッドプールで同期処理を実行（イベントループをブロックしない）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_image_executor, _generate_with_grounding_sync)
            return result
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise Exception(f"LLM生成エラー: {str(e)}\n詳細: {error_details}")
    
    async def generate_structured_output_with_grounding(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        enable_grounding: bool = True
    ) -> Tuple[str, Optional[dict]]:
        """
        Grounding with Google Searchを有効化した構造化JSON出力生成
        
        Args:
            user_prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
            max_tokens: 最大トークン数
            enable_grounding: Groundingを有効化するか
        
        Returns:
            (JSON文字列, groundingメタデータ) のタプル
        """
        # JSON出力を明示的に指示
        enhanced_prompt = f"{user_prompt}\n\n必ずJSON形式で出力してください。マークダウンのコードブロックは使わず、純粋なJSONのみを返してください。"
        
        return await self.generate_text_with_grounding(
            user_prompt=enhanced_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=1.0,  # Grounding使用時は1.0推奨
            enable_grounding=enable_grounding
        )
    
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> str:
        """
        画像を分析してテキストを生成（非同期版）
        
        Args:
            image_data: 画像のバイナリデータ
            prompt: 分析プロンプト
            system_prompt: システムプロンプト（オプション）
            max_tokens: 最大トークン数
        
        Returns:
            分析結果テキスト
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
                temperature=0.3,  # より正確な抽出のため低温度
            )
            
            # 画像データをBase64エンコード
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 非同期で画像とプロンプトを組み合わせて送信
            response = await model.generate_content_async(
                [
                    {
                        "mime_type": "image/png",
                        "data": image_base64
                    },
                    prompt
                ],
                generation_config=generation_config
            )
            
            if response.text:
                return response.text
            else:
                return ""
                
        except Exception as e:
            raise Exception(f"画像分析エラー: {str(e)}")

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9"
    ) -> Tuple[bytes, str]:
        """
        テキストから画像を生成（非同期版）
        
        Args:
            prompt: 画像生成プロンプト
            aspect_ratio: アスペクト比（"1:1", "16:9", "9:16" など）
        
        Returns:
            (画像バイナリデータ, MIMEタイプ) のタプル
        
        Note:
            画像生成に使用するモデルはクライアント初期化時のmodel_nameを使用
            (例: gemini-3-pro-image-preview)
            google.genai パッケージは同期APIのため、スレッドプールで実行
        """
        def _generate_image_sync():
            """同期的な画像生成処理"""
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
        
        try:
            # スレッドプールで同期処理を実行（イベントループをブロックしない）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_image_executor, _generate_image_sync)
            return result
                
        except Exception as e:
            raise Exception(f"画像生成エラー: {str(e)}")

    async def generate_image_with_reference(
        self,
        prompt: str,
        reference_image_data: bytes,
        reference_mime_type: str = "image/webp",
        aspect_ratio: str = "16:9",
    ) -> Tuple[bytes, str]:
        """
        参照画像を添付して画像を生成（非同期版）

        Args:
            prompt: 画像生成プロンプト
            reference_image_data: 参照画像バイナリ
            reference_mime_type: 参照画像MIMEタイプ
            aspect_ratio: アスペクト比（未使用、将来拡張用）

        Returns:
            (画像バイナリデータ, MIMEタイプ) のタプル
        """
        def _generate_image_with_reference_sync():
            from google import genai as genai_new
            from google.genai import types as genai_types

            client = genai_new.Client(api_key=os.getenv("GOOGLE_API_KEY"))

            image_part = genai_types.Part.from_bytes(
                data=reference_image_data,
                mime_type=reference_mime_type,
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[image_part, prompt],
                config=genai_types.GenerateContentConfig(
                    response_modalities=["Text", "Image"]
                )
            )

            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    return part.inline_data.data, part.inline_data.mime_type

            raise Exception("画像が生成されませんでした")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_image_executor, _generate_image_with_reference_sync)
            return result
        except Exception as e:
            raise Exception(f"参照画像付き画像生成エラー: {str(e)}")


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
