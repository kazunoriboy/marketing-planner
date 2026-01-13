"""
CSVアップロード履歴管理サービス

CSVアップロードの履歴管理、統計の合算、データ期間の重複チェックを行う
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select
from app.models import CSVUploadHistory, AnalysisSession

logger = logging.getLogger(__name__)


class CSVHistoryService:
    """CSVアップロード履歴管理サービス"""
    
    def __init__(self, db_session: Session):
        self.session = db_session
    
    def _ensure_dict(self, data) -> Dict:
        """
        データが文字列の場合はJSONとしてパースしてdictに変換
        
        データベースからJSONBカラムを読み出す際に、文字列として
        返されることがあるため、安全にdictに変換する
        """
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return parsed
                logger.warning(f"Parsed JSON is not a dict: {type(parsed)}")
                return {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON string: {e}")
                return {}
        logger.warning(f"Unexpected data type for statistics: {type(data)}")
        return {}
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """ファイルのハッシュ値を計算"""
        return hashlib.sha256(file_content).hexdigest()
    
    def check_duplicate_file(self, hotel_id: int, file_hash: str) -> Optional[CSVUploadHistory]:
        """
        同じファイルが既にアップロードされているかチェック
        
        Returns:
            重複している場合は既存の履歴、なければNone
        """
        statement = select(CSVUploadHistory).where(
            CSVUploadHistory.hotel_id == hotel_id,
            CSVUploadHistory.file_hash == file_hash
        )
        return self.session.exec(statement).first()
    
    def check_period_overlap(
        self,
        hotel_id: int,
        period_start: datetime,
        period_end: datetime,
        exclude_history_id: Optional[int] = None
    ) -> List[CSVUploadHistory]:
        """
        データ期間が重複する履歴をチェック
        
        Args:
            hotel_id: ホテルID
            period_start: 新しいデータの開始日
            period_end: 新しいデータの終了日
            exclude_history_id: 除外する履歴ID（再アップロード時に自身を除外）
        
        Returns:
            重複している履歴のリスト
        """
        statement = select(CSVUploadHistory).where(
            CSVUploadHistory.hotel_id == hotel_id,
            CSVUploadHistory.data_period_start != None,
            CSVUploadHistory.data_period_end != None
        )
        
        histories = self.session.exec(statement).all()
        overlapping = []
        
        for history in histories:
            if exclude_history_id and history.id == exclude_history_id:
                continue
            
            # 期間の重複チェック
            # A: [period_start, period_end], B: [history.start, history.end]
            # 重複条件: A.start <= B.end AND A.end >= B.start
            if (period_start <= history.data_period_end and 
                period_end >= history.data_period_start):
                overlapping.append(history)
        
        return overlapping
    
    def get_upload_histories(self, hotel_id: int) -> List[CSVUploadHistory]:
        """ホテルのCSVアップロード履歴を取得"""
        statement = select(CSVUploadHistory).where(
            CSVUploadHistory.hotel_id == hotel_id
        ).order_by(CSVUploadHistory.upload_date.desc())
        histories = list(self.session.exec(statement).all())
        
        # 各履歴のstatisticsがdictであることを確認
        for history in histories:
            history.statistics = self._ensure_dict(history.statistics)
        
        return histories
    
    def add_upload_history(
        self,
        hotel_id: int,
        filename: str,
        file_hash: str,
        statistics: Dict,
        record_count: int,
        data_period_start: Optional[datetime] = None,
        data_period_end: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> CSVUploadHistory:
        """
        CSVアップロード履歴を追加
        
        Returns:
            作成された履歴
        """
        # statisticsがdictであることを確認
        statistics_dict = self._ensure_dict(statistics)
        logger.info(f"Adding upload history with statistics type: {type(statistics_dict)}")
        
        history = CSVUploadHistory(
            hotel_id=hotel_id,
            filename=filename,
            file_hash=file_hash,
            statistics=statistics_dict,
            record_count=record_count,
            data_period_start=data_period_start,
            data_period_end=data_period_end,
            notes=notes,
            is_migrated=False
        )
        self.session.add(history)
        return history
    
    def delete_upload_history(self, history_id: int) -> bool:
        """
        CSVアップロード履歴を削除
        
        Returns:
            削除成功したかどうか
        """
        history = self.session.get(CSVUploadHistory, history_id)
        if not history:
            return False
        
        self.session.delete(history)
        # 削除を即座にDBに反映（後続のクエリで削除が反映されるようにする）
        self.session.flush()
        return True
    
    def merge_all_statistics(self, hotel_id: int) -> Dict:
        """
        ホテルの全CSVアップロード履歴の統計を合算
        
        Returns:
            合算された統計情報
        """
        histories = self.get_upload_histories(hotel_id)
        
        if not histories:
            return {}
        
        if len(histories) == 1:
            return self._ensure_dict(histories[0].statistics)
        
        # 複数の統計を合算（文字列の場合はdictに変換）
        stats_list = [self._ensure_dict(h.statistics) for h in histories]
        return self._merge_statistics(stats_list)
    
    def _merge_statistics(self, stats_list: List[Dict]) -> Dict:
        """
        複数の統計情報を合算
        
        Args:
            stats_list: 統計情報のリスト
        
        Returns:
            合算された統計情報
        """
        if not stats_list:
            return {}
        
        # すべての統計がdictであることを確認
        stats_list = [self._ensure_dict(s) for s in stats_list]
        
        # 空の辞書を除外
        stats_list = [s for s in stats_list if s]
        
        if not stats_list:
            return {}
        
        if len(stats_list) == 1:
            return stats_list[0]
        
        merged = {}
        
        # total_records: 合算
        merged["total_records"] = sum(
            s.get("total_records", 0) for s in stats_list
        )
        
        # schema_mapping: 最新のものを使用
        for s in stats_list:
            if s.get("schema_mapping"):
                merged["schema_mapping"] = s["schema_mapping"]
                break
        
        # date_range: 最小の開始日と最大の終了日
        # analysis_service.py は "start", "end" を出力する
        all_starts = []
        all_ends = []
        for s in stats_list:
            date_range = s.get("date_range", {})
            if not isinstance(date_range, dict):
                date_range = self._ensure_dict(date_range)
            
            # 新形式: "start", "end"
            if date_range.get("start"):
                all_starts.append(date_range["start"])
            if date_range.get("end"):
                all_ends.append(date_range["end"])
            
            # 旧形式との互換性（念のため）
            if date_range.get("booking_date_start"):
                all_starts.append(date_range["booking_date_start"])
            if date_range.get("booking_date_end"):
                all_ends.append(date_range["booking_date_end"])
            if date_range.get("stay_date_start"):
                all_starts.append(date_range["stay_date_start"])
            if date_range.get("stay_date_end"):
                all_ends.append(date_range["stay_date_end"])
        
        if all_starts or all_ends:
            merged["date_range"] = {}
            # 文字列の日付をソートして最小/最大を取得
            if all_starts:
                merged["date_range"]["start"] = min(all_starts)
            if all_ends:
                merged["date_range"]["end"] = max(all_ends)
        
        # cancellation_stats: 合算
        merged["cancellation_stats"] = self._merge_cancellation_stats(stats_list)
        
        # top_plans: 合算して再ランキング
        merged["top_plans"] = self._merge_top_plans(stats_list)
        
        # weekday_occupancy: 合算
        merged["weekday_occupancy"] = self._merge_dict_values(
            [s.get("weekday_occupancy", {}) for s in stats_list]
        )
        
        # guest_stats: 合算
        merged["guest_stats"] = self._merge_guest_stats(stats_list)
        
        # price_stats: 加重平均
        merged["price_stats"] = self._merge_price_stats(stats_list)
        
        # guest_area_stats: 合算
        merged["guest_area_stats"] = self._merge_guest_area_stats(stats_list)
        
        # average_lead_time: 加重平均（レコード数で重み付け）
        merged["average_lead_time"] = self._merge_average_lead_time(stats_list)
        
        return merged
    
    def _merge_cancellation_stats(self, stats_list: List[Dict]) -> Dict:
        """キャンセル統計を合算（複数の形式に対応）
        
        対応する入力形式:
            形式1 (AnalysisService): total_bookings, cancelled_bookings, cancellation_rate_percent
            形式2 (旧マージ形式): confirmed_count, cancelled_count, cancellation_rate
        
        フロントエンドの期待する形式:
            - total_bookings: 総予約数
            - cancelled_bookings: キャンセル数
            - cancellation_rate: キャンセル率（0.0-1.0の小数）
        """
        total_bookings = 0
        total_cancelled = 0
        
        for s in stats_list:
            cancel_stats = s.get("cancellation_stats", {})
            # cancel_statsが辞書でない場合は変換
            if not isinstance(cancel_stats, dict):
                cancel_stats = self._ensure_dict(cancel_stats)
            
            # 形式1: total_bookings, cancelled_bookings (AnalysisService)
            if "total_bookings" in cancel_stats:
                total_bookings += cancel_stats.get("total_bookings", 0) or 0
                total_cancelled += cancel_stats.get("cancelled_bookings", 0) or 0
            # 形式2: confirmed_count, cancelled_count (旧マージ形式)
            elif "confirmed_count" in cancel_stats or "cancelled_count" in cancel_stats:
                confirmed = cancel_stats.get("confirmed_count", 0) or 0
                cancelled = cancel_stats.get("cancelled_count", 0) or 0
                total_bookings += confirmed + cancelled
                total_cancelled += cancelled
        
        # フロントエンドは 0.0-1.0 の小数を期待
        cancel_rate = round(total_cancelled / total_bookings, 4) if total_bookings > 0 else 0
        
        return {
            "total_bookings": total_bookings,
            "cancelled_bookings": total_cancelled,
            "cancellation_rate": cancel_rate  # 0.0-1.0 の小数形式
        }
    
    def _merge_top_plans(self, stats_list: List[Dict], top_n: int = 5) -> Dict[str, int]:
        """トッププランを合算して再ランキング
        
        analysis_service.py の出力形式: {"プラン名": 件数, ...}
        フロントエンドの期待する形式: {"プラン名": 件数, ...} (Object.entriesで処理)
        
        Returns:
            辞書形式 {"プラン名": 件数, ...} をトップN件まで返す
        """
        plan_counts = {}
        
        for s in stats_list:
            top_plans = s.get("top_plans", {})
            
            # top_plansが辞書形式の場合（{"プラン名": 件数, ...}）- 標準形式
            if isinstance(top_plans, dict):
                for plan_name, count in top_plans.items():
                    if plan_name and isinstance(count, (int, float)):
                        plan_counts[plan_name] = plan_counts.get(plan_name, 0) + int(count)
            # top_plansがリスト形式の場合（[{"plan_name": "...", "count": ...}, ...]）- 旧形式
            elif isinstance(top_plans, list):
                for plan in top_plans:
                    if isinstance(plan, dict):
                        plan_name = plan.get("plan_name", plan.get("name", ""))
                        count = plan.get("count", 0)
                        if plan_name:
                            plan_counts[plan_name] = plan_counts.get(plan_name, 0) + int(count)
                    elif isinstance(plan, str):
                        # プラン名だけのリストの場合
                        plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        # ソートしてトップNを辞書形式で返す（フロントエンドが Object.entries で処理）
        sorted_plans = sorted(plan_counts.items(), key=lambda x: x[1], reverse=True)
        return {name: count for name, count in sorted_plans[:top_n]}
    
    def _merge_dict_values(self, dict_list: List[Dict]) -> Dict:
        """辞書の値を合算"""
        merged = {}
        for d in dict_list:
            # dが辞書でない場合はスキップ
            if not isinstance(d, dict):
                d = self._ensure_dict(d)
            if not d:
                continue
            for key, value in d.items():
                if isinstance(value, (int, float)):
                    merged[key] = merged.get(key, 0) + value
        return merged
    
    def _merge_guest_stats(self, stats_list: List[Dict]) -> Dict:
        """宿泊人数統計を合算"""
        total_records = 0
        total_guests_sum = 0
        total_avg_sum = 0
        all_min = None
        all_max = None
        
        # 人数分布を合算
        distribution_totals = {
            "1人": 0,
            "2人": 0,
            "3人": 0,
            "4人": 0,
            "5人以上": 0
        }
        
        for s in stats_list:
            guest_stats = s.get("guest_stats", {})
            if not isinstance(guest_stats, dict):
                guest_stats = self._ensure_dict(guest_stats)
            
            count = s.get("total_records", 0) or 0
            avg = guest_stats.get("average", 0) or 0
            
            if count > 0 and avg > 0:
                total_records += count
                total_avg_sum += avg * count
            
            # total_guestsを合算
            if guest_stats.get("total_guests"):
                total_guests_sum += guest_stats["total_guests"]
            
            # distributionを合算
            dist = guest_stats.get("distribution", {})
            if isinstance(dist, dict):
                for key in distribution_totals:
                    distribution_totals[key] += dist.get(key, 0)
            
            if guest_stats.get("min") is not None:
                if all_min is None or guest_stats["min"] < all_min:
                    all_min = guest_stats["min"]
            
            if guest_stats.get("max") is not None:
                if all_max is None or guest_stats["max"] > all_max:
                    all_max = guest_stats["max"]
        
        result = {}
        if total_records > 0:
            result["average"] = round(total_avg_sum / total_records, 2)
        if all_min is not None:
            result["min"] = all_min
        if all_max is not None:
            result["max"] = all_max
        if total_guests_sum > 0:
            result["total_guests"] = total_guests_sum
        
        # 分布データがあれば追加
        if any(v > 0 for v in distribution_totals.values()):
            result["distribution"] = distribution_totals
            result["note"] = "キャンセルを除く確定予約のみ"
        
        return result
    
    def _merge_price_stats(self, stats_list: List[Dict]) -> Dict:
        """価格統計を合算（加重平均）"""
        # 1人あたり単価
        per_guest_records = 0
        per_guest_sum = 0
        per_guest_min = None
        per_guest_max = None
        
        # 予約合計金額
        total_records = 0
        total_sum = 0
        total_min = None
        total_max = None
        
        # valid_count（有効データ数）
        valid_count_sum = 0
        excluded_count_sum = 0
        
        for s in stats_list:
            price_stats = s.get("price_stats", {})
            if not isinstance(price_stats, dict):
                price_stats = self._ensure_dict(price_stats)
            
            # valid_countがあればそれを使う、なければtotal_recordsを使う
            valid_count = price_stats.get("valid_count", 0) or 0
            if valid_count > 0:
                valid_count_sum += valid_count
            
            excluded_count = price_stats.get("excluded_count", 0) or 0
            excluded_count_sum += excluded_count
            
            # 1人あたり単価の加重平均
            per_guest_avg = price_stats.get("per_guest_average", 0) or 0
            if valid_count > 0 and per_guest_avg > 0:
                per_guest_records += valid_count
                per_guest_sum += per_guest_avg * valid_count
            
            # 予約合計金額の加重平均
            total_avg = price_stats.get("total_average", 0) or 0
            if valid_count > 0 and total_avg > 0:
                total_records += valid_count
                total_sum += total_avg * valid_count
            
            # 1人あたり単価のmin/max
            pg_min = price_stats.get("per_guest_min")
            pg_max = price_stats.get("per_guest_max")
            if pg_min is not None:
                if per_guest_min is None or pg_min < per_guest_min:
                    per_guest_min = pg_min
            if pg_max is not None:
                if per_guest_max is None or pg_max > per_guest_max:
                    per_guest_max = pg_max
            
            # 予約合計金額のmin/max
            t_min = price_stats.get("total_min")
            t_max = price_stats.get("total_max")
            if t_min is not None:
                if total_min is None or t_min < total_min:
                    total_min = t_min
            if t_max is not None:
                if total_max is None or t_max > total_max:
                    total_max = t_max
        
        result = {}
        
        # 1人あたり単価
        if per_guest_records > 0:
            result["per_guest_average"] = round(per_guest_sum / per_guest_records, 0)
        if per_guest_min is not None:
            result["per_guest_min"] = per_guest_min
        if per_guest_max is not None:
            result["per_guest_max"] = per_guest_max
        
        # 予約合計金額
        if total_records > 0:
            result["total_average"] = round(total_sum / total_records, 0)
        if total_min is not None:
            result["total_min"] = total_min
        if total_max is not None:
            result["total_max"] = total_max
        
        # 有効データ数
        if valid_count_sum > 0:
            result["valid_count"] = valid_count_sum
        if excluded_count_sum > 0:
            result["excluded_count"] = excluded_count_sum
        
        if result:
            result["note"] = "キャンセルを除く確定予約のみ"
        
        return result
    
    def _merge_guest_area_stats(self, stats_list: List[Dict]) -> Dict:
        """予約者エリア統計を合算"""
        total_domestic = 0
        total_overseas = 0
        region_dist = {}
        prefecture_dist = {}
        overseas_dist = {}
        unique_areas = set()
        total_with_area = 0
        
        for s in stats_list:
            area_stats = s.get("guest_area_stats", {})
            if not isinstance(area_stats, dict):
                area_stats = self._ensure_dict(area_stats)
            
            total_domestic += area_stats.get("domestic_count", 0) or 0
            total_overseas += area_stats.get("overseas_count", 0) or 0
            total_with_area += area_stats.get("total_records_with_area", 0) or 0
            
            # 地方別
            region_distribution = area_stats.get("region_distribution", {})
            if not isinstance(region_distribution, dict):
                region_distribution = self._ensure_dict(region_distribution)
            for region, count in region_distribution.items():
                region_dist[region] = region_dist.get(region, 0) + (count or 0)
            
            # 都道府県別
            prefecture_distribution = area_stats.get("prefecture_distribution", {})
            if not isinstance(prefecture_distribution, dict):
                prefecture_distribution = self._ensure_dict(prefecture_distribution)
            for pref, count in prefecture_distribution.items():
                prefecture_dist[pref] = prefecture_dist.get(pref, 0) + (count or 0)
            
            # 海外
            overseas_distribution = area_stats.get("overseas_distribution", {})
            if not isinstance(overseas_distribution, dict):
                overseas_distribution = self._ensure_dict(overseas_distribution)
            for country, count in overseas_distribution.items():
                overseas_dist[country] = overseas_dist.get(country, 0) + (count or 0)
            
            unique_areas.add(area_stats.get("total_unique_areas", 0) or 0)
        
        if total_domestic == 0 and total_overseas == 0:
            return {}
        
        return {
            "domestic_count": total_domestic,
            "overseas_count": total_overseas,
            "total_records_with_area": total_with_area,
            "total_unique_areas": len(region_dist) + len(overseas_dist),
            "region_distribution": region_dist,
            "prefecture_distribution": prefecture_dist,
            "overseas_distribution": overseas_dist,
            "note": "複数CSVの合算データ"
        }
    
    def _merge_average_lead_time(self, stats_list: List[Dict]) -> Optional[float]:
        """平均リードタイムを加重平均で合算"""
        total_records = 0
        total_sum = 0
        
        for s in stats_list:
            lead_time = s.get("average_lead_time")
            count = s.get("total_records", 0)
            
            if lead_time is not None and count > 0:
                total_records += count
                total_sum += lead_time * count
        
        if total_records > 0:
            return round(total_sum / total_records, 1)
        return None
    
    def update_analysis_session_statistics(self, hotel_id: int) -> AnalysisSession:
        """
        AnalysisSessionの統計を全履歴から再計算して更新
        
        Returns:
            更新されたAnalysisSession
        """
        # 全履歴を取得して合算
        merged_stats = self.merge_all_statistics(hotel_id)
        histories = self.get_upload_histories(hotel_id)
        
        logger.info(f"Merged stats type: {type(merged_stats)}")
        
        # merged_statsがdictであることを確認
        merged_stats = self._ensure_dict(merged_stats)
        
        # AnalysisSessionを取得または作成
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        analysis_session = self.session.exec(statement).first()
        
        if analysis_session:
            analysis_session.csv_statistics = merged_stats
            analysis_session.csv_upload_count = len(histories)
        else:
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                csv_statistics=merged_stats,
                csv_upload_count=len(histories)
            )
            self.session.add(analysis_session)
        
        return analysis_session
