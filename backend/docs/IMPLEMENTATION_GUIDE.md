# 顧客分析機能 - 実装ガイド

## 実装完了日
2025年12月1日

## 概要

Gemini 3.1 Flash-Liteを使用した顧客分析機能の実装詳細を説明します。

## アーキテクチャ

### システム構成

```
┌─────────────────┐
│   Frontend      │
│   (Next.js)     │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   API Router    │
│  (FastAPI)      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Analysis Service│
│  (Core Logic)   │
└────┬────────────┘
     │
     ├─→ [Gemini 3.1 Flash-Lite] - AIスキーマ推定
     ├─→ [pandas] - 統計計算
     └─→ [Gemini 3.1 Flash-Lite] - インサイト生成
```

### ディレクトリ構造

```
backend/
├── app/
│   ├── core/
│   │   └── llm.py                    # LLMクライアント
│   ├── services/
│   │   ├── analysis_service.py       # メイン実装
│   │   └── csv_analyzer.py           # 既存サービス（更新済み）
│   ├── api/
│   │   └── analysis.py               # APIルーター
│   ├── schemas/
│   │   └── analysis.py               # Pydanticスキーマ
│   └── models.py                     # データベースモデル
├── docs/
│   ├── CUSTOMER_ANALYSIS_SPEC.md     # 機能仕様書
│   └── IMPLEMENTATION_GUIDE.md       # このファイル
├── tests/
│   └── test_analysis.py              # テストコード
└── requirements.txt                  # 依存関係
```

## 実装内容

### 1. LLMクライアント (`app/core/llm.py`)

#### 変更点

**コンストラクタの更新**
```python
class LLMClient:
    def __init__(self, model_name: str = "gemini-3.1-flash-lite"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY環境変数が設定されていません")
        genai.configure(api_key=api_key)
        self.model_name = model_name
```

**便利関数の追加**
```python
async def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = "gemini-3.1-flash-lite",
    max_tokens: int = 4096,
    temperature: float = 1.0
) -> str:
    """テキスト生成の便利関数"""
    client = get_llm_client(model_name=model)
    return await client.generate_text(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )
```

### 2. 分析サービス (`app/services/analysis_service.py`)

#### 主要クラス

```python
class AnalysisService:
    """顧客分析サービス"""
    
    def __init__(self):
        self.model_name = "gemini-3.1-flash-lite"
```

#### 実装メソッド

##### a. エンコーディング自動判別

```python
def _detect_encoding(self, file_content: bytes) -> str:
    """
    CSVファイルのエンコーディングを自動判別
    
    1. chardetで検出
    2. 優先度リストで試行
    3. 成功したエンコーディングを返却
    """
    detected = chardet.detect(file_content)
    encoding = detected.get('encoding', 'utf-8')
    
    encodings_to_try = [
        encoding,
        'utf-8',
        'shift_jis',
        'cp932',
        'euc-jp',
        'iso-2022-jp'
    ]
    
    for enc in encodings_to_try:
        try:
            file_content.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    
    return 'utf-8'
```

##### b. CSVの読み込み

```python
def _load_csv(self, file_content: bytes) -> pd.DataFrame:
    """
    エンコーディングを自動判別してCSVを読み込み
    """
    encoding = self._detect_encoding(file_content)
    
    try:
        text_content = file_content.decode(encoding)
        df = pd.read_csv(StringIO(text_content))
        return df
    except Exception as e:
        # フォールバック: UTF-8で再試行
        text_content = file_content.decode('utf-8', errors='ignore')
        df = pd.read_csv(StringIO(text_content))
        return df
```

##### c. AIスキーマ推定

```python
async def infer_csv_schema(self, df: pd.DataFrame) -> Dict[str, str]:
    """
    Gemini 3.1 Flash-LiteでCSVスキーマを推定
    
    1. ヘッダーとサンプルデータを取得
    2. AIにプロンプトを投げる
    3. JSON形式で結果を受け取る
    """
    columns = df.columns.tolist()
    sample_rows = df.head(10).to_dict('records')
    
    system_prompt = """あなたは宿泊予約データ分析の専門家です。
提示されたCSVデータから、以下の情報を表すカラム名を特定し、
正確なJSON形式で返してください。

- booking_date (予約日)
- stay_date (宿泊日)
- plan_name (プラン名)
- total_price (合計金額)
- status (予約ステータス - キャンセル判定用)

※データの中身から文脈を読んで判断すること。"""
    
    user_prompt = f"""以下のCSVデータを解析してください。

【カラム名】
{columns}

【サンプルデータ（先頭10行）】
{json.dumps(sample_rows, ensure_ascii=False, indent=2, default=str)}

出力形式（必ず以下のJSON形式で返してください）:
{{
  "booking_date": "該当するカラム名またはnull",
  "stay_date": "該当するカラム名またはnull",
  "plan_name": "該当するカラム名またはnull",
  "total_price": "該当するカラム名またはnull",
  "status": "該当するカラム名またはnull"
}}"""
    
    llm_client = get_llm_client(model_name=self.model_name)
    response = await llm_client.generate_structured_output(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=1024
    )
    
    # JSONをパース
    json_text = re.sub(r'```json\s*', '', response)
    json_text = re.sub(r'```\s*', '', json_text)
    json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
    
    if json_match:
        return json.loads(json_match.group())
    else:
        return json.loads(json_text)
```

##### d. 統計計算

```python
def calculate_statistics(
    self,
    df: pd.DataFrame,
    schema_map: Dict[str, Optional[str]]
) -> Dict:
    """
    データ正規化と統計情報の計算
    """
    stats = {
        "total_records": len(df),
        "schema_mapping": schema_map,
        "date_range": {},
        "cancellation_stats": {},
        "average_lead_time": None,
        "top_plans": {},
        "weekday_occupancy": {},
        "price_stats": {}
    }
    
    df_work = df.copy()
    
    # 日付変換
    booking_col = schema_map.get("booking_date")
    stay_col = schema_map.get("stay_date")
    
    if stay_col and stay_col in df_work.columns:
        df_work[stay_col] = pd.to_datetime(df_work[stay_col], errors='coerce')
        stats["date_range"] = {
            "start": df_work[stay_col].min().isoformat(),
            "end": df_work[stay_col].max().isoformat()
        }
    
    # キャンセル率計算
    status_col = schema_map.get("status")
    if status_col and status_col in df_work.columns:
        cancel_keywords = ['キャンセル', 'cancel', 'cancelled', 'canceled', '取消']
        df_work['is_cancelled'] = df_work[status_col].astype(str).str.contains(
            '|'.join(cancel_keywords),
            case=False,
            na=False
        )
        
        cancellation_rate = (df_work['is_cancelled'].sum() / len(df_work) * 100)
        stats["cancellation_stats"] = {
            "total_bookings": len(df_work),
            "cancelled_bookings": int(df_work['is_cancelled'].sum()),
            "cancellation_rate_percent": round(cancellation_rate, 2)
        }
    
    # リードタイム計算
    if booking_col and stay_col:
        df_work['lead_time'] = (df_work[stay_col] - df_work[booking_col]).dt.days
        stats["average_lead_time"] = round(df_work['lead_time'].mean(), 1)
    
    # プラン別予約数Top5
    plan_col = schema_map.get("plan_name")
    if plan_col and plan_col in df_work.columns:
        top_plans = df_work[plan_col].value_counts().head(5).to_dict()
        stats["top_plans"] = {str(k): int(v) for k, v in top_plans.items()}
    
    # 曜日別稼働率
    if stay_col and stay_col in df_work.columns:
        df_work['weekday'] = df_work[stay_col].dt.day_name()
        weekday_counts = df_work['weekday'].value_counts().to_dict()
        stats["weekday_occupancy"] = {str(k): int(v) for k, v in weekday_counts.items()}
    
    # 価格統計
    price_col = schema_map.get("total_price")
    if price_col and price_col in df_work.columns:
        df_work[price_col] = pd.to_numeric(df_work[price_col], errors='coerce')
        stats["price_stats"] = {
            "average": round(df_work[price_col].mean(), 0),
            "min": round(df_work[price_col].min(), 0),
            "max": round(df_work[price_col].max(), 0),
            "median": round(df_work[price_col].median(), 0)
        }
    
    return stats
```

##### e. AIインサイト生成

```python
async def generate_marketing_insights(self, stats: Dict) -> str:
    """
    Gemini 3.1 Flash-Liteでマーケティングインサイトを生成
    """
    system_prompt = """あなたは宿泊施設のマーケティング戦略コンサルタントです。
データ分析結果から実践的なインサイトを導き出し、具体的なアクションプランを提案してください。

以下の観点を含めてください：
1. ターゲット層の特徴
2. 現状の課題（キャンセル率、リードタイムなど）
3. 推奨アクション（具体的な施策）"""
    
    user_prompt = f"""以下の顧客データ分析結果から、マーケティング施策に活かせるインサイトを300文字程度で生成してください。

【分析結果】
{json.dumps(stats, ensure_ascii=False, indent=2, default=str)}

具体的で実践的な提案をお願いします。"""
    
    llm_client = get_llm_client(model_name=self.model_name)
    insights = await llm_client.generate_text(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=1024,
        temperature=0.7
    )
    
    return insights
```

##### f. 一気通貫分析

```python
async def analyze_csv(self, file_content: bytes) -> Tuple[Dict, str]:
    """
    CSV分析の一気通貫実行
    
    1. CSVを読み込み（エンコーディング自動判別）
    2. スキーマを推定（AI）
    3. 統計を計算（pandas）
    4. インサイトを生成（AI）
    """
    df = self._load_csv(file_content)
    schema_map = await self.infer_csv_schema(df)
    statistics = self.calculate_statistics(df, schema_map)
    insights = await self.generate_marketing_insights(statistics)
    
    return statistics, insights
```

### 3. APIルーター (`app/api/analysis.py`)

#### 新規エンドポイント

```python
@router.post("/upload-csv", response_model=CSVAnalysisResponse)
async def upload_and_analyze_csv(
    hotel_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    顧客データ（CSV）を分析（Gemini 3.1 Flash-Lite版）
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # ファイルタイプの確認
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    try:
        # ファイルを読み込み
        file_content = await file.read()
        
        # 新しいAnalysisServiceを使用
        analysis_service = AnalysisService()
        
        # 分析実行
        statistics, insights = await analysis_service.analyze_csv(file_content)
        
        # 分析セッションを作成または更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        existing_session = session.exec(statement).first()
        
        if existing_session:
            existing_session.csv_statistics = statistics
            existing_session.csv_insights = insights
            analysis_session = existing_session
        else:
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                csv_statistics=statistics,
                csv_insights=insights
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return CSVAnalysisResponse(
            session_id=analysis_session.id,
            statistics=statistics,
            insights=insights,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")
```

## 依存関係

### requirements.txt

```txt
# 新規追加
chardet  # エンコーディング自動判別

# 既存
fastapi
uvicorn[standard]
python-dotenv
python-multipart
sqlmodel
psycopg2-binary
pandas
google-generativeai
```

## 環境変数

### .env ファイル

```bash
# Google AI API Key（必須）
GOOGLE_API_KEY=your_api_key_here

# データベース設定
DATABASE_URL=postgresql://postgres:postgres@db:5432/marketing_planner

# アプリケーション設定
APP_NAME=Marketing Planner API
APP_VERSION=1.0.0
DEBUG=True
```

## テスト

テストコードは `tests/test_analysis.py` を参照してください。

### テスト実行方法

```bash
# コンテナ内で実行
docker compose exec backend python -m pytest tests/test_analysis.py -v
```

## デプロイ

### ローカル環境

```bash
# 依存関係のインストール
pip install -r requirements.txt

# サーバー起動
uvicorn app.main:app --reload
```

### Docker環境

```bash
# コンテナをビルド・起動
docker compose up -d

# ログ確認
docker compose logs -f backend
```

## トラブルシューティング

### よくある問題と解決策

#### 1. GOOGLE_API_KEY環境変数エラー

**エラー**
```
ValueError: GOOGLE_API_KEY環境変数が設定されていません
```

**解決策**
```bash
# .envファイルを確認
cat .env | grep GOOGLE_API_KEY

# 設定されていない場合は追加
echo "GOOGLE_API_KEY=your_api_key_here" >> .env

# コンテナを再起動
docker compose restart backend
```

#### 2. CSVエンコーディングエラー

**エラー**
```
ValueError: CSVファイルの読み込みに失敗しました
```

**解決策**
- ファイルが破損していないか確認
- BOM付きUTF-8の場合、BOMを削除
- 手動でエンコーディングを確認

#### 3. スキーマ推定の精度が低い

**症状**
- カラムが正しく認識されない

**解決策**
- CSVのヘッダー名を分かりやすくする
- サンプルデータ行数を増やす（`head(10)` → `head(20)`）
- プロンプトに具体例を追加

## パフォーマンスチューニング

### 最適化ポイント

1. **バッチ処理**
   - 複数CSVを一度に処理する場合、並列化を検討

2. **キャッシング**
   - スキーママッピングを保存し、再利用

3. **データベースクエリ**
   - 分析セッションの取得をインデックス最適化

## セキュリティ考慮事項

### チェックリスト

- ✅ ファイル拡張子の検証
- ✅ ファイルサイズ制限
- ✅ SQLインジェクション対策
- ⚠️ API認証（今後実装）
- ⚠️ ファイルコンテンツスキャン（今後実装）

## 今後の拡張

### 計画中の機能

1. **カスタムスキーママッピング**
   - ユーザーが手動でカラムマッピングを修正可能に

2. **時系列分析**
   - 月別・季節別のトレンド分析

3. **予測モデル**
   - 需要予測、キャンセル予測

4. **エクスポート機能**
   - PDF、Excelレポート生成

## 参考資料

- [Gemini API ドキュメント](https://ai.google.dev/docs)
- [FastAPI ドキュメント](https://fastapi.tiangolo.com/)
- [pandas ドキュメント](https://pandas.pydata.org/docs/)
- [SQLModel ドキュメント](https://sqlmodel.tiangolo.com/)

---

**バージョン**: 1.0  
**最終更新**: 2025年12月1日

