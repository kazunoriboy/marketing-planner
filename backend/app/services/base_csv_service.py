"""
Base CSV Service - CSV処理の共通機能

すべてのCSV分析サービスの基底クラス
"""

import json
import time

import pandas as pd
import numpy as np
import chardet
from typing import Any, Dict, List, Optional, Tuple
from io import StringIO


# 任意のバイト列をデコードできてしまうため、日本語CSVでは誤検出になりやすい
_UNRELIABLE_ENCODINGS = frozenset({
    'iso-8859-1', 'iso8859-1', 'latin-1', 'latin1', 'ascii', 'macroman',
})

_DEBUG_LOG_PATHS = (
    '/Users/matsushimaittoku/Projects/marketing-planner/.cursor/debug-75e7a4.log',
    '/app/debug-75e7a4.log',
)


class BaseCSVService:
    """CSV処理の共通機能を提供する基底クラス"""

    def _debug_log(self, location: str, message: str, data: dict, hypothesis_id: str) -> None:
        # #region agent log
        try:
            payload = {
                'sessionId': '75e7a4',
                'location': location,
                'message': message,
                'data': data,
                'timestamp': int(time.time() * 1000),
                'hypothesisId': hypothesis_id,
            }
            line = json.dumps(payload, ensure_ascii=False) + '\n'
            for path in _DEBUG_LOG_PATHS:
                try:
                    with open(path, 'a', encoding='utf-8') as f:
                        f.write(line)
                    break
                except Exception:
                    continue
        except Exception:
            pass
        # #endregion

    def _encoding_quality_score(self, text: str) -> float:
        """デコード結果の品質スコア（日本語CSV向け）。高いほど妥当。"""
        if not text:
            return 0.0

        sample = text[:8000]
        if not sample.strip():
            return 0.0

        japanese_chars = sum(
            1 for c in sample
            if ('\u3040' <= c <= '\u30ff') or ('\u4e00' <= c <= '\u9fff') or ('\uff00' <= c <= '\uffef')
        )
        replacement_chars = sample.count('\ufffd')
        control_chars = sum(1 for c in sample if ord(c) < 32 and c not in '\r\n\t')

        score = japanese_chars / max(len(sample), 1)
        score -= replacement_chars * 0.05
        score -= control_chars * 0.01

        header = sample.split('\n', 1)[0]
        if any(keyword in header for keyword in ('予約', 'チェックイン', 'プラン', '料金')):
            score += 0.5

        return score

    def _decode_csv_text(self, file_content: bytes, encoding: str) -> str:
        normalized = (encoding or 'utf-8').lower().replace('-', '_')
        if normalized in ('shift_jis', 'shiftjis', 'sjis'):
            encoding = 'cp932'
        return file_content.decode(encoding)

    def _try_load_csv_from_text(self, text_content: str) -> pd.DataFrame:
        return pd.read_csv(StringIO(text_content))

    def _detect_encoding(self, file_content: bytes) -> str:
        """
        CSVファイルのエンコーディングを自動判別
        
        Args:
            file_content: ファイルの内容（バイト列）
        
        Returns:
            検出されたエンコーディング名
        """
        detected = chardet.detect(file_content)
        chardet_encoding = detected.get('encoding') or 'utf-8'

        candidates: List[str] = list(dict.fromkeys([
            chardet_encoding,
            'utf-8-sig',
            'utf-8',
            'cp932',
            'shift_jis',
            'euc-jp',
            'iso-2022-jp',
        ]))

        best_encoding: Optional[str] = None
        best_score = float('-inf')
        candidate_scores: Dict[str, float] = {}

        for enc in candidates:
            if not enc or enc.lower() in _UNRELIABLE_ENCODINGS:
                continue
            try:
                text = self._decode_csv_text(file_content, enc)
            except (UnicodeDecodeError, LookupError, AttributeError, TypeError):
                continue

            score = self._encoding_quality_score(text)
            if detected.get('language') == 'Japanese' and enc.lower() in ('cp932', 'shift_jis', 'shift-jis'):
                score += 0.15
            candidate_scores[enc] = round(score, 4)

            if score > best_score:
                best_score = score
                best_encoding = enc

        if best_encoding:
            self._debug_log(
                'base_csv_service.py:_detect_encoding',
                'encoding detected',
                {
                    'chardet': detected,
                    'chosen_encoding': best_encoding,
                    'best_score': round(best_score, 4),
                    'candidate_scores': candidate_scores,
                },
                'B',
            )
            return best_encoding

        for enc in ('cp932', 'shift_jis', 'utf-8-sig', 'utf-8', 'euc-jp'):
            try:
                self._decode_csv_text(file_content, enc)
                self._debug_log(
                    'base_csv_service.py:_detect_encoding',
                    'encoding fallback used',
                    {'chardet': detected, 'chosen_encoding': enc},
                    'D',
                )
                return enc
            except (UnicodeDecodeError, LookupError, AttributeError, TypeError):
                continue

        self._debug_log(
            'base_csv_service.py:_detect_encoding',
            'encoding default cp932',
            {'chardet': detected},
            'D',
        )
        return 'cp932'
    
    def _load_csv(self, file_content: bytes) -> pd.DataFrame:
        """
        CSVファイルを読み込み（エンコーディング自動判別）
        
        Args:
            file_content: ファイルの内容（バイト列）
        
        Returns:
            pandasデータフレーム
        """
        encoding = self._detect_encoding(file_content)
        load_attempts: List[Tuple[str, str, Optional[str]]] = []

        for enc in dict.fromkeys([encoding, 'cp932', 'shift_jis', 'utf-8-sig', 'utf-8', 'euc-jp']):
            try:
                text_content = self._decode_csv_text(file_content, enc)
                df = self._try_load_csv_from_text(text_content)
                quality = self._encoding_quality_score(text_content)
                load_attempts.append((enc, 'success', f'quality={quality:.4f}'))

                header_preview = text_content.split('\n', 1)[0][:120]
                self._debug_log(
                    'base_csv_service.py:_load_csv',
                    'csv loaded',
                    {
                        'encoding': enc,
                        'quality_score': round(quality, 4),
                        'columns_preview': df.columns.tolist()[:8],
                        'header_preview': header_preview,
                        'row_count': len(df),
                    },
                    'A',
                )
                return df
            except Exception as exc:
                load_attempts.append((enc, 'failed', str(exc)[:120]))
                continue

        self._debug_log(
            'base_csv_service.py:_load_csv',
            'csv load failed',
            {'attempts': load_attempts},
            'A',
        )
        raise ValueError("CSVファイルの読み込みに失敗しました。文字コード（Shift_JIS/UTF-8）を確認してください。")
    
    def _convert_to_json_serializable(self, obj: Any) -> Any:
        """
        Pandasのデータ型をJSON serializable な型に変換
        
        Args:
            obj: 変換対象のオブジェクト
        
        Returns:
            JSON serializable なオブジェクト
        """
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_to_json_serializable(value) 
                    for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) 
                    for item in obj]
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def _safe_to_datetime(self, series: pd.Series) -> pd.Series:
        """
        安全に日付型に変換
        
        Args:
            series: pandas Series
        
        Returns:
            日付型に変換されたSeries
        """
        return pd.to_datetime(series, errors='coerce')
    
    def _safe_to_numeric(self, series: pd.Series) -> pd.Series:
        """
        安全に数値型に変換
        
        Args:
            series: pandas Series
        
        Returns:
            数値型に変換されたSeries
        """
        return pd.to_numeric(series, errors='coerce')
    
    def _get_column_value(
        self, 
        df: pd.DataFrame, 
        schema_map: Dict[str, str], 
        key: str
    ) -> pd.Series:
        """
        スキーママップからカラムを取得
        
        Args:
            df: データフレーム
            schema_map: スキーママッピング
            key: 取得するキー
        
        Returns:
            該当するカラムのSeries（存在しない場合はNone）
        """
        col_name = schema_map.get(key)
        if col_name and col_name in df.columns:
            return df[col_name]
        return None
    
    def _calculate_date_range(
        self, 
        df: pd.DataFrame, 
        date_column: str
    ) -> Dict[str, str]:
        """
        日付範囲を計算
        
        Args:
            df: データフレーム
            date_column: 日付カラム名
        
        Returns:
            開始日と終了日の辞書
        """
        if date_column not in df.columns:
            return {}
        
        date_series = self._safe_to_datetime(df[date_column])
        min_date = date_series.min()
        max_date = date_series.max()
        
        return {
            "start": min_date.isoformat() if pd.notna(min_date) else None,
            "end": max_date.isoformat() if pd.notna(max_date) else None
        }

