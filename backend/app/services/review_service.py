"""
口コミ収集・分析サービス

Dify + Jina Readerを使用して口コミを収集・分析します。
"""
import json
import re
from typing import Optional
from datetime import datetime

from app.services.dify_client import get_dify_client, DifyClient


class ReviewService:
    """口コミ収集・分析サービス"""
    
    # サポートする口コミサイト
    SUPPORTED_SITES = {
        "jalan": {
            "name": "じゃらん",
            "url_pattern": r"jalan\.net",
        },
        "google": {
            "name": "Googleマップ",
            "url_pattern": r"google\.(com|co\.jp)/maps",
        },
    }
    
    def __init__(self, dify_client: Optional[DifyClient] = None):
        self.dify_client = dify_client
    
    def _get_dify_client(self) -> DifyClient:
        """Difyクライアントを取得（遅延初期化）"""
        if self.dify_client is None:
            self.dify_client = get_dify_client()
        return self.dify_client
    
    def validate_url(self, url: str, site_type: str) -> bool:
        """
        口コミURLの形式を検証
        
        Args:
            url: 検証するURL
            site_type: サイトタイプ（jalan/google）
        
        Returns:
            URLが有効かどうか
        """
        if site_type not in self.SUPPORTED_SITES:
            return False
        
        pattern = self.SUPPORTED_SITES[site_type]["url_pattern"]
        return bool(re.search(pattern, url))
    
    def detect_site_type(self, url: str) -> Optional[str]:
        """
        URLからサイトタイプを自動検出
        
        Args:
            url: 口コミページのURL
        
        Returns:
            検出されたサイトタイプ（検出できない場合はNone）
        """
        for site_type, config in self.SUPPORTED_SITES.items():
            if re.search(config["url_pattern"], url):
                return site_type
        return None
    
    async def extract_reviews(
        self,
        review_url: str,
        site_type: Optional[str] = None,
    ) -> dict:
        """
        口コミを抽出
        
        Args:
            review_url: 口コミページのURL
            site_type: サイトタイプ（省略時は自動検出）
        
        Returns:
            抽出結果:
            {
                "reviews": [...],
                "summary": {...},
                "source": {...},
                "extracted_at": "..."
            }
        """
        # サイトタイプを自動検出
        if site_type is None:
            site_type = self.detect_site_type(review_url)
            if site_type is None:
                raise ValueError(f"サポートされていないURLです: {review_url}")
        
        # URLの検証
        if not self.validate_url(review_url, site_type):
            raise ValueError(f"URLの形式が不正です: {review_url}")
        
        # Difyワークフローを実行
        dify_client = self._get_dify_client()
        result = await dify_client.run_review_extraction(
            review_url=review_url,
            site_type=site_type,
        )
        
        # 結果を整形
        return {
            "reviews": result.get("reviews", []),
            "summary": result.get("summary", {}),
            "source": {
                "url": review_url,
                "site_type": site_type,
                "site_name": self.SUPPORTED_SITES[site_type]["name"],
            },
            "extracted_at": datetime.utcnow().isoformat(),
        }
    
    async def analyze_multiple_sources(
        self,
        review_urls: dict,
    ) -> dict:
        """
        複数ソースから口コミを収集・分析
        
        Args:
            review_urls: サイトタイプとURLのマッピング
                         例: {"jalan": "https://...", "google": "https://..."}
        
        Returns:
            統合された分析結果:
            {
                "sources": [...],
                "all_reviews": [...],
                "combined_summary": {...},
                "analyzed_at": "..."
            }
        """
        sources = []
        all_reviews = []
        all_positive_themes = []
        all_negative_themes = []
        all_guest_expectations = []
        
        for site_type, url in review_urls.items():
            if not url:
                continue
            
            try:
                result = await self.extract_reviews(url, site_type)
                sources.append(result["source"])
                all_reviews.extend(result.get("reviews", []))
                
                summary = result.get("summary", {})
                all_positive_themes.extend(summary.get("positive_themes", []))
                all_negative_themes.extend(summary.get("negative_themes", []))
                all_guest_expectations.extend(summary.get("guest_expectations", []))
                
            except Exception as e:
                sources.append({
                    "url": url,
                    "site_type": site_type,
                    "error": str(e),
                })
        
        # 重複を除去してトップ項目を抽出
        combined_summary = {
            "positive_themes": self._dedupe_and_limit(all_positive_themes, 5),
            "negative_themes": self._dedupe_and_limit(all_negative_themes, 5),
            "guest_expectations": self._dedupe_and_limit(all_guest_expectations, 5),
            "total_reviews": len(all_reviews),
            "sources_count": len([s for s in sources if "error" not in s]),
        }
        
        return {
            "sources": sources,
            "all_reviews": all_reviews[:50],  # 最新50件に制限
            "combined_summary": combined_summary,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    def _dedupe_and_limit(self, items: list, limit: int = 5) -> list:
        """重複を除去して上位N件を返す"""
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
                if len(result) >= limit:
                    break
        return result
    
    def format_for_reviews_summary(self, analysis_result: dict) -> dict:
        """
        分析結果をreviews_summary形式に変換
        
        既存のAnalysisSession.reviews_summaryフィールドと互換性のある形式に変換
        
        Args:
            analysis_result: analyze_multiple_sourcesの結果
        
        Returns:
            reviews_summary形式のデータ
        """
        combined = analysis_result.get("combined_summary", {})
        
        return {
            "positive_themes": combined.get("positive_themes", []),
            "negative_themes": combined.get("negative_themes", []),
            "guest_expectations": combined.get("guest_expectations", []),
            "source_urls": {
                s["site_type"]: s["url"]
                for s in analysis_result.get("sources", [])
                if "error" not in s
            },
            "total_reviews": combined.get("total_reviews", 0),
            "analyzed_at": analysis_result.get("analyzed_at"),
        }


def get_review_service() -> ReviewService:
    """ReviewServiceのインスタンスを取得"""
    return ReviewService()

