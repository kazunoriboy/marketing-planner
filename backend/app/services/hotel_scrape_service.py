"""宿の公式サイトからハイライト・周辺情報・アクセスを自動取得するサービス"""
import json
import re
from html.parser import HTMLParser

import httpx

from app.core.llm import get_llm_client

_DEFAULT_RESULT = {
    "highlights": [],
    "surrounding": {"description": "", "attractions": []},
    "access": "",
}

_USER_AGENT = (
    "Mozilla/5.0 (compatible; MarketingPlannerBot/1.0; +https://example.com/bot)"
)


class _TextExtractor(HTMLParser):
    """<script> / <style> を除外してテキストを抽出する HTMLParser"""

    def __init__(self):
        super().__init__()
        self._skip = False
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.get_text()


class HotelScrapeService:
    @staticmethod
    async def scrape_hotel_info(website_url: str, hotel_name: str) -> dict:
        """
        公式サイトからホテル情報をスクレイプして構造化JSONで返す。

        Args:
            website_url: ホテル公式サイトURL
            hotel_name:  ホテル名（プロンプトに使用）

        Returns:
            {highlights, surrounding: {description, attractions}, access}
        """
        # 1. HTMLを取得
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                response = await client.get(website_url)
                html = response.text
        except Exception:
            return dict(_DEFAULT_RESULT)

        # 2. テキスト抽出 → 最大8,000文字
        text = _extract_text(html)[:8000]

        if not text.strip():
            return dict(_DEFAULT_RESULT)

        # 3. Gemini で構造化JSON生成
        system_prompt = (
            "あなたは宿泊施設のウェブサイト情報を整理するエキスパートです。"
            "ウェブサイトのテキストを読み取り、宿のハイライト・周辺情報・アクセス情報を"
            "指定のJSON形式で返してください。"
            "情報が見つからないフィールドは空値（空文字列または空配列）にしてください。"
            "推測で情報を作らず、サイトに記載されている内容のみを使用してください。"
        )

        user_prompt = f"""以下は「{hotel_name}」の公式サイトから取得したテキストです。

---
{text}
---

このテキストを元に、次のJSON形式で情報を抽出してください：
{{
  "highlights": ["宿の特徴フレーズ1", "宿の特徴フレーズ2"],
  "surrounding": {{
    "description": "周辺エリアの説明文",
    "attractions": [
      {{"name": "観光スポット名", "distance": "距離（例：車で15分）"}}
    ]
  }},
  "access": "アクセス情報テキスト"
}}

ルール:
- highlights は最大8個の短いフレーズ
- attractions は最大10件
- 情報がない場合は空値（[]、""）を返す
- 純粋なJSONのみを返す（コードブロック不要）"""

        try:
            llm = get_llm_client(model_name="gemini-3.1-flash-lite")
            raw = await llm.generate_structured_output(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=2048,
            )
        except Exception:
            return dict(_DEFAULT_RESULT)

        # 4. JSONパース
        try:
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
            result = json.loads(cleaned)
        except Exception:
            return dict(_DEFAULT_RESULT)

        # 5. 構造を保証して返す
        highlights = result.get("highlights", [])
        if not isinstance(highlights, list):
            highlights = []

        surrounding_raw = result.get("surrounding", {})
        if not isinstance(surrounding_raw, dict):
            surrounding_raw = {}

        attractions_raw = surrounding_raw.get("attractions", [])
        if not isinstance(attractions_raw, list):
            attractions_raw = []

        attractions = [
            {"name": str(a.get("name", "")), "distance": str(a.get("distance", ""))}
            for a in attractions_raw
            if isinstance(a, dict)
        ]

        return {
            "highlights": [str(h) for h in highlights if h],
            "surrounding": {
                "description": str(surrounding_raw.get("description", "")),
                "attractions": attractions,
            },
            "access": str(result.get("access", "")),
        }
