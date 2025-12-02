"""
Base CSV Service - CSV処理の共通機能

すべてのCSV分析サービスの基底クラス
"""

import pandas as pd
import numpy as np
import chardet
from typing import Any, Dict
from io import StringIO


class BaseCSVService:
    """CSV処理の共通機能を提供する基底クラス"""
    
    def _detect_encoding(self, file_content: bytes) -> str:
        """
        CSVファイルのエンコーディングを自動判別
        
        Args:
            file_content: ファイルの内容（バイト列）
        
        Returns:
            検出されたエンコーディング名
        """
        # chardetで検出を試みる
        detected = chardet.detect(file_content)
        encoding = detected.get('encoding', 'utf-8')
        
        # よくあるエンコーディングの優先順位リスト
        encodings_to_try = [
            encoding,  # 検出されたもの
            'utf-8',
            'shift_jis',
            'cp932',  # Windows版Shift_JIS
            'euc-jp',
            'iso-2022-jp'
        ]
        
        # 重複を除去
        encodings_to_try = list(dict.fromkeys(encodings_to_try))
        
        # 各エンコーディングで読み込みを試行
        for enc in encodings_to_try:
            try:
                file_content.decode(enc)
                return enc
            except (UnicodeDecodeError, AttributeError):
                continue
        
        # すべて失敗した場合はutf-8をデフォルトで返す
        return 'utf-8'
    
    def _load_csv(self, file_content: bytes) -> pd.DataFrame:
        """
        CSVファイルを読み込み（エンコーディング自動判別）
        
        Args:
            file_content: ファイルの内容（バイト列）
        
        Returns:
            pandasデータフレーム
        """
        # エンコーディングを検出
        encoding = self._detect_encoding(file_content)
        
        try:
            # 検出したエンコーディングで読み込み
            text_content = file_content.decode(encoding)
            df = pd.read_csv(StringIO(text_content))
            return df
        except Exception as e:
            # 失敗した場合、utf-8でリトライ（エラー無視）
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                df = pd.read_csv(StringIO(text_content))
                return df
            except Exception as e2:
                raise ValueError(f"CSVファイルの読み込みに失敗しました: {str(e2)}")
    
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

