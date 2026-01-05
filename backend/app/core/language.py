"""
言語判定ユーティリティ

ペルソナのlocation（居住地）から対象言語を自動判定する
"""

from typing import Optional, Dict

# 国名・地域名と言語コードのマッピング
# キーは小文字で格納（検索時に小文字変換して比較）
LOCATION_TO_LANGUAGE: Dict[str, str] = {
    # 日本語
    "日本": "ja",
    "japan": "ja",
    "東京": "ja",
    "大阪": "ja",
    "京都": "ja",
    "北海道": "ja",
    "沖縄": "ja",
    "福岡": "ja",
    "名古屋": "ja",
    "横浜": "ja",
    "神戸": "ja",
    "札幌": "ja",
    
    # 英語（アメリカ）
    "アメリカ": "en",
    "米国": "en",
    "usa": "en",
    "united states": "en",
    "america": "en",
    "california": "en",
    "new york": "en",
    "los angeles": "en",
    "san francisco": "en",
    "hawaii": "en",
    "ハワイ": "en",
    
    # 英語（イギリス）
    "イギリス": "en",
    "英国": "en",
    "uk": "en",
    "united kingdom": "en",
    "england": "en",
    "london": "en",
    "ロンドン": "en",
    
    # 英語（オーストラリア）
    "オーストラリア": "en",
    "australia": "en",
    "sydney": "en",
    "シドニー": "en",
    "melbourne": "en",
    
    # 英語（カナダ）
    "カナダ": "en",
    "canada": "en",
    "toronto": "en",
    "vancouver": "en",
    
    # 英語（シンガポール）
    "シンガポール": "en",
    "singapore": "en",
    
    # 英語（その他）
    "ニュージーランド": "en",
    "new zealand": "en",
    
    # 中国語（繁体字 - 台湾）
    "台湾": "zh-TW",
    "taiwan": "zh-TW",
    "台北": "zh-TW",
    "taipei": "zh-TW",
    "高雄": "zh-TW",
    
    # 中国語（繁体字 - 香港）
    "香港": "zh-TW",
    "hong kong": "zh-TW",
    
    # 中国語（簡体字 - 中国本土）
    "中国": "zh-CN",
    "中華人民共和国": "zh-CN",
    "china": "zh-CN",
    "北京": "zh-CN",
    "上海": "zh-CN",
    "shanghai": "zh-CN",
    "beijing": "zh-CN",
    "広州": "zh-CN",
    "深圳": "zh-CN",
    
    # 韓国語
    "韓国": "ko",
    "korea": "ko",
    "south korea": "ko",
    "ソウル": "ko",
    "seoul": "ko",
    "釜山": "ko",
    "busan": "ko",
    
    # タイ語
    "タイ": "th",
    "thailand": "th",
    "バンコク": "th",
    "bangkok": "th",
    
    # ベトナム語
    "ベトナム": "vi",
    "vietnam": "vi",
    "ホーチミン": "vi",
    "ho chi minh": "vi",
    "ハノイ": "vi",
    "hanoi": "vi",
    
    # インドネシア語
    "インドネシア": "id",
    "indonesia": "id",
    "ジャカルタ": "id",
    "jakarta": "id",
    "バリ": "id",
    "bali": "id",
    
    # マレーシア語（英語も通用）
    "マレーシア": "ms",
    "malaysia": "ms",
    "クアラルンプール": "ms",
    "kuala lumpur": "ms",
    
    # フィリピン（英語）
    "フィリピン": "en",
    "philippines": "en",
    "マニラ": "en",
    "manila": "en",
    
    # インド（英語）
    "インド": "en",
    "india": "en",
    "mumbai": "en",
    "delhi": "en",
    
    # フランス語
    "フランス": "fr",
    "france": "fr",
    "パリ": "fr",
    "paris": "fr",
    
    # ドイツ語
    "ドイツ": "de",
    "germany": "de",
    "ベルリン": "de",
    "berlin": "de",
    "ミュンヘン": "de",
    "munich": "de",
    
    # スペイン語
    "スペイン": "es",
    "spain": "es",
    "マドリード": "es",
    "madrid": "es",
    "バルセロナ": "es",
    "barcelona": "es",
    
    # イタリア語
    "イタリア": "it",
    "italy": "it",
    "ローマ": "it",
    "rome": "it",
    "ミラノ": "it",
    "milan": "it",
    
    # ポルトガル語
    "ブラジル": "pt",
    "brazil": "pt",
    "ポルトガル": "pt",
    "portugal": "pt",
    
    # ロシア語
    "ロシア": "ru",
    "russia": "ru",
    "モスクワ": "ru",
    "moscow": "ru",
}

# 言語コードと表示名のマッピング
LANGUAGE_NAMES: Dict[str, str] = {
    "ja": "日本語",
    "en": "英語",
    "zh-TW": "中国語（繁体字）",
    "zh-CN": "中国語（簡体字）",
    "ko": "韓国語",
    "th": "タイ語",
    "vi": "ベトナム語",
    "id": "インドネシア語",
    "ms": "マレーシア語",
    "fr": "フランス語",
    "de": "ドイツ語",
    "es": "スペイン語",
    "it": "イタリア語",
    "pt": "ポルトガル語",
    "ru": "ロシア語",
}


def detect_language_from_location(location: str) -> str:
    """
    locationから言語コードを判定する
    
    Args:
        location: ペルソナの居住地（例: "台湾台北市", "California, USA"）
    
    Returns:
        言語コード（例: "ja", "en", "zh-TW"）
        判定できない場合は "en"（英語）をデフォルトとして返す
    """
    if not location:
        return "ja"
    
    # 小文字に変換
    location_lower = location.lower()
    
    # 完全一致を先にチェック
    if location_lower in LOCATION_TO_LANGUAGE:
        return LOCATION_TO_LANGUAGE[location_lower]
    
    # 部分一致でチェック（マッピングのキーがlocationに含まれているか）
    for key, lang_code in LOCATION_TO_LANGUAGE.items():
        if key in location_lower:
            return lang_code
    
    # 日本の都道府県パターン（〜県、〜府、〜都、〜道）
    japanese_prefixes = ["都", "道", "府", "県"]
    for suffix in japanese_prefixes:
        if suffix in location:
            return "ja"
    
    # 判定できない場合は英語（国際的に通用）をデフォルトとする
    # ただし、日本語の文字が含まれている場合は日本語
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in location):
        # ひらがな、カタカナ、漢字が含まれている
        # ただし、中国語の可能性もあるので漢字のみの場合は要注意
        if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in location):
            # ひらがな or カタカナがあれば日本語確定
            return "ja"
    
    return "en"


def get_language_name(lang_code: str) -> str:
    """
    言語コードから言語名を取得
    
    Args:
        lang_code: 言語コード（例: "ja", "en"）
    
    Returns:
        言語名（例: "日本語", "英語"）
    """
    return LANGUAGE_NAMES.get(lang_code, lang_code)


def is_japanese(lang_code: str) -> bool:
    """日本語かどうかを判定"""
    return lang_code == "ja"


def get_language_instruction(lang_code: str) -> str:
    """
    成果物生成時の言語指示文を生成
    
    Args:
        lang_code: 言語コード
    
    Returns:
        LLMへの言語指示文
    """
    if lang_code == "ja":
        return "日本語で出力してください。"
    
    lang_name = get_language_name(lang_code)
    
    # 言語別の特記事項
    special_instructions = {
        "zh-TW": "繁体字（Traditional Chinese）を使用してください。",
        "zh-CN": "簡体字（Simplified Chinese）を使用してください。",
    }
    
    special = special_instructions.get(lang_code, "")
    
    return f"{lang_name}（{lang_code}）で出力してください。{special}"

