# アーキテクチャ設計

## 📐 サービス設計

### CSV処理の設計パターン

顧客分析機能では、CSV処理の共通ロジックを基底クラスに切り出し、継承による再利用を実現しています。

## 🏗️ クラス構造

```
BaseCSVService (基底クラス)
    ↑
    ├─ AnalysisService (顧客分析サービス)
    └─ CSVAnalyzer (CSV分析サービス)
```

### BaseCSVService（基底クラス）

**責務**: CSV処理の共通機能を提供

**提供する機能**:

1. **エンコーディング自動判別**
   - `_detect_encoding(file_content: bytes) -> str`
   - UTF-8、Shift_JIS、CP932等を自動検出

2. **CSV読み込み**
   - `_load_csv(file_content: bytes) -> pd.DataFrame`
   - エンコーディングを自動判別して読み込み

3. **JSON変換**
   - `_convert_to_json_serializable(obj) -> Any`
   - Pandasのデータ型をJSON serializable な型に変換

4. **ヘルパーメソッド**
   - `_safe_to_datetime(series) -> pd.Series` - 安全な日付変換
   - `_safe_to_numeric(series) -> pd.Series` - 安全な数値変換
   - `_get_column_value(df, schema_map, key)` - スキーママップからカラム取得
   - `_calculate_date_range(df, date_column)` - 日付範囲計算

**ファイル**: `app/services/base_csv_service.py`

### AnalysisService（Gemini 3.1 Flash-Lite版）

**責務**: 顧客データの包括的な分析

**固有機能**:

1. **AIスキーマ推定**
   - `infer_csv_schema(df) -> Dict`
   - Gemini 3.1 Flash-LiteでCSV構造を解釈

2. **詳細統計計算**
   - `calculate_statistics(df, schema_map) -> Dict`
   - キャンセル率、リードタイム、曜日別稼働率等

3. **マーケティングインサイト生成**
   - `generate_marketing_insights(stats) -> str`
   - AIによる実践的な施策提案

4. **一気通貫分析**
   - `analyze_csv(file_content) -> Tuple[Dict, str]`
   - スキーマ推定 → 統計計算 → インサイト生成

**ファイル**: `app/services/analysis_service.py`

### CSVAnalyzer（既存サービス）

**責務**: 基本的なCSV分析

**固有機能**:

1. **スキーマ検出**
   - `detect_schema(df, llm_client) -> Dict`

2. **基本統計計算**
   - `calculate_statistics(df, schema_mapping) -> Dict`

3. **インサイト生成**
   - `generate_insights(statistics, llm_client) -> str`

4. **CSV分析**
   - `analyze_csv(file_content, llm_client) -> Tuple[Dict, str]`

**ファイル**: `app/services/csv_analyzer.py`

## 🎯 設計の利点

### 1. DRY原則（Don't Repeat Yourself）

**Before（リファクタリング前）**:
```python
# analysis_service.py
def _detect_encoding(self, file_content):
    # エンコーディング判別ロジック（重複）
    ...

# csv_analyzer.py
def _detect_encoding(self, file_content):
    # 同じロジック（重複）
    ...
```

**After（リファクタリング後）**:
```python
# base_csv_service.py
class BaseCSVService:
    def _detect_encoding(self, file_content):
        # 共通ロジック（1箇所のみ）
        ...

# analysis_service.py
class AnalysisService(BaseCSVService):
    # 継承により_detect_encodingを利用
    pass

# csv_analyzer.py
class CSVAnalyzer(BaseCSVService):
    # 継承により_detect_encodingを利用
    pass
```

### 2. 単一責任の原則（Single Responsibility Principle）

各クラスが明確な責務を持ちます：

- **BaseCSVService**: CSV処理の技術的詳細
- **AnalysisService**: ビジネスロジック（分析・インサイト生成）
- **CSVAnalyzer**: 基本的な分析機能

### 3. 拡張性

新しいCSV分析サービスを追加する場合：

```python
class ReportService(BaseCSVService):
    """レポート生成サービス"""
    
    def __init__(self):
        super().__init__()
        # CSV処理の共通機能が自動的に利用可能
    
    def generate_report(self, file_content: bytes):
        # BaseCSVServiceの機能を利用
        df = self._load_csv(file_content)
        # ... レポート生成ロジック
        return self._convert_to_json_serializable(report)
```

### 4. テスタビリティ

基底クラスの機能を個別にテスト可能：

```python
def test_encoding_detection():
    service = BaseCSVService()
    utf8_content = b"..."
    assert service._detect_encoding(utf8_content) == "utf-8"
    
    sjis_content = b"..."
    assert service._detect_encoding(sjis_content) == "shift_jis"
```

### 5. 保守性

- バグ修正や機能追加が1箇所で済む
- 変更の影響範囲が明確
- コードの重複が減り、読みやすい

## 🔄 データフロー

### AnalysisServiceの処理フロー

```
[CSVファイル（bytes）]
    ↓
[BaseCSVService._detect_encoding()]
    ↓ エンコーディング検出
[BaseCSVService._load_csv()]
    ↓ DataFrame化
[AnalysisService.infer_csv_schema()]
    ↓ AIスキーマ推定
[AnalysisService.calculate_statistics()]
    ↓ 統計計算
[BaseCSVService._convert_to_json_serializable()]
    ↓ JSON変換
[AnalysisService.generate_marketing_insights()]
    ↓ AIインサイト生成
[結果返却]
```

## 📦 ディレクトリ構造

```
backend/app/services/
├── base_csv_service.py        # 基底クラス（CSV共通処理）
├── analysis_service.py         # 顧客分析サービス
├── csv_analyzer.py             # CSV分析サービス
├── plan_generator.py           # プラン生成サービス
└── creative_generator.py       # クリエイティブ生成サービス
```

## 🎨 デザインパターン

### Template Methodパターン

基底クラスで処理の骨格を定義し、サブクラスで具体的な実装を行います。

```python
class BaseCSVService:
    def _load_csv(self, file_content):
        """テンプレートメソッド"""
        encoding = self._detect_encoding(file_content)
        return self._parse_csv(file_content, encoding)

class AnalysisService(BaseCSVService):
    def analyze_csv(self, file_content):
        """具体的な実装"""
        df = self._load_csv(file_content)  # テンプレート利用
        schema = self.infer_csv_schema(df)  # 独自処理
        return self.calculate_statistics(df, schema)
```

### Strategy パターン（今後の拡張）

異なる分析戦略を切り替え可能に：

```python
class BaseAnalysisStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Dict:
        pass

class SimpleAnalysisStrategy(BaseAnalysisStrategy):
    def analyze(self, df):
        # シンプルな分析
        ...

class DetailedAnalysisStrategy(BaseAnalysisStrategy):
    def analyze(self, df):
        # 詳細な分析
        ...

class AnalysisService(BaseCSVService):
    def __init__(self, strategy: BaseAnalysisStrategy):
        super().__init__()
        self.strategy = strategy
```

## 🔮 今後の拡張案

### 1. 分析パイプラインの抽象化

```python
class BaseAnalysisPipeline(BaseCSVService):
    """分析パイプラインの基底クラス"""
    
    def execute(self, file_content: bytes):
        df = self._load_csv(file_content)
        df = self.preprocess(df)
        schema = self.detect_schema(df)
        stats = self.calculate_stats(df, schema)
        insights = self.generate_insights(stats)
        return self._convert_to_json_serializable({
            'statistics': stats,
            'insights': insights
        })
    
    @abstractmethod
    def preprocess(self, df): pass
    
    @abstractmethod
    def detect_schema(self, df): pass
```

### 2. バリデーション機能の追加

```python
class BaseCSVService:
    def _validate_csv(self, df: pd.DataFrame) -> bool:
        """CSVの妥当性を検証"""
        if df.empty:
            raise ValueError("CSVが空です")
        if len(df) < 3:
            raise ValueError("データが少なすぎます")
        return True
```

### 3. キャッシング機能

```python
class BaseCSVService:
    def __init__(self):
        self._cache = {}
    
    def _load_csv_cached(self, file_content: bytes):
        cache_key = hashlib.md5(file_content).hexdigest()
        if cache_key not in self._cache:
            self._cache[cache_key] = self._load_csv(file_content)
        return self._cache[cache_key]
```

## 📊 パフォーマンス考慮事項

### メモリ効率

- 大規模CSVの場合、chunk読み込みを検討
- 不要なデータフレームのコピーを避ける

```python
class BaseCSVService:
    def _load_csv_chunked(self, file_content: bytes, chunksize=1000):
        """大規模CSV用のチャンク読み込み"""
        encoding = self._detect_encoding(file_content)
        text_content = file_content.decode(encoding)
        return pd.read_csv(StringIO(text_content), chunksize=chunksize)
```

### 処理速度

- pandasのベクトル化演算を活用
- 不要なデータ変換を避ける
- 必要な列のみを読み込む

## 🔐 セキュリティ考慮事項

### ファイルサイズ制限

```python
class BaseCSVService:
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def _validate_file_size(self, file_content: bytes):
        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(f"ファイルサイズが大きすぎます（最大: {self.MAX_FILE_SIZE}バイト）")
```

### インジェクション対策

- CSV読み込み時にエスケープ処理
- ユーザー入力の検証

## 📝 命名規約

### プライベートメソッド

- `_` で始まる（例: `_load_csv`, `_detect_encoding`）
- サブクラスから利用可能

### パブリックメソッド

- `_` なし（例: `analyze_csv`, `infer_csv_schema`）
- 外部から呼び出し可能

### 戻り値の型

- 明示的な型ヒントを使用
- `typing` モジュールを活用

## 🧪 テスト戦略

### ユニットテスト

```python
# tests/test_base_csv_service.py
def test_encoding_detection():
    service = BaseCSVService()
    # UTF-8
    assert service._detect_encoding(b"...") == "utf-8"
    # Shift_JIS
    assert service._detect_encoding(b"...") == "shift_jis"

# tests/test_analysis_service.py
def test_schema_inference():
    service = AnalysisService()
    df = pd.DataFrame(...)
    schema = await service.infer_csv_schema(df)
    assert "booking_date" in schema
```

### 統合テスト

```python
# tests/test_integration.py
async def test_full_analysis_flow():
    service = AnalysisService()
    with open("test_data.csv", "rb") as f:
        content = f.read()
    stats, insights = await service.analyze_csv(content)
    assert stats["total_records"] > 0
    assert len(insights) > 0
```

---

**バージョン**: 1.1  
**最終更新**: 2025年12月2日

