# 顧客分析機能 - Gemini 3.1 Flash-Lite版

このドキュメントでは、Gemini 3.1 Flash-Liteを使用した顧客分析機能の実装について説明します。

## 概要

宿泊施設の予約データ（CSV形式）をアップロードし、AIによる自動分析とマーケティングインサイトを生成します。

### 主な機能

1. **スマートエンコーディング判別**: 自動でCSVのエンコーディング（UTF-8、Shift_JIS等）を検出
2. **AIスキーマ推定**: Gemini 3.1 Flash-LiteがCSV構造を理解し、カラムを自動マッピング
3. **統計計算**: pandas でデータを正規化し、重要な指標を計算
4. **AIインサイト生成**: データから実践的なマーケティング施策を提案

## 使用モデル

**Gemini 3.1 Flash-Lite**
- 高速・安価でありながら高い推論能力
- CSV構造の理解と戦略的提案に最適

## ファイル構成

```
backend/app/
├── core/
│   └── llm.py                    # LLMクライアント（Gemini 3.1 Flash-Lite対応）
├── services/
│   ├── analysis_service.py       # 新規実装（推奨）
│   └── csv_analyzer.py           # 既存実装（更新済み）
└── api/
    └── analysis.py               # APIルーター
```

## APIエンドポイント

### POST `/api/analysis/upload-csv`

顧客データ（CSV）を分析します（Gemini 3.1 Flash-Lite版）。

**リクエスト**
- `hotel_id` (form): 宿泊施設ID
- `file` (file): CSVファイル

**レスポンス**
```json
{
  "session_id": 1,
  "statistics": {
    "total_records": 1000,
    "schema_mapping": {
      "booking_date": "予約日",
      "stay_date": "宿泊日",
      "plan_name": "プラン名",
      "total_price": "合計金額",
      "status": "ステータス"
    },
    "date_range": {
      "start": "2024-01-01T00:00:00",
      "end": "2024-12-31T00:00:00"
    },
    "cancellation_stats": {
      "total_bookings": 1000,
      "cancelled_bookings": 150,
      "cancellation_rate_percent": 15.0,
      "last_minute_cancellation_rate_percent": 40.0
    },
    "average_lead_time": 21.5,
    "top_plans": {
      "素泊まりプラン": 300,
      "朝食付きプラン": 250,
      "...": "..."
    },
    "weekday_occupancy": {
      "Monday": 120,
      "Tuesday": 100,
      "...": "..."
    },
    "price_stats": {
      "average": 12000,
      "min": 5000,
      "max": 50000,
      "median": 10000
    }
  },
  "insights": "【AIによるマーケティングインサイト】\n分析結果から、リードタイムが平均21.5日であり、早期予約の傾向が見られます...",
  "created_at": "2024-12-01T12:00:00"
}
```

### POST `/api/analysis/customer`

従来の実装（既存エンドポイント、Gemini 3.1 Flash-Lite対応済み）。

## 実装詳細

### 1. Geminiクライアント設定 (`llm.py`)

```python
from app.core.llm import get_llm_client

# Gemini 3.1 Flash-Liteクライアントを取得
llm_client = get_llm_client(model_name="gemini-3.1-flash-lite")
```

### 2. AIによるスキーマ推定

`AnalysisService.infer_csv_schema()` メソッドが、CSVのヘッダーとサンプルデータからカラムの意味を推定します。

**プロンプト例:**
```
あなたは宿泊予約データ分析の専門家です。
提示されたCSVデータから、以下の情報を表すカラム名を特定し、
正確なJSON形式で返してください。

- booking_date (予約日)
- stay_date (宿泊日)
- plan_name (プラン名)
- total_price (合計金額)
- status (予約ステータス - キャンセル判定用)
```

### 3. データ正規化と統計計算

`calculate_statistics()` メソッドが pandas を使用して以下の指標を計算します:

- **キャンセル率**: 全体・直前（7日前以降）
- **平均リードタイム**: 予約日から宿泊日までの平均日数
- **プラン別予約数Top5**: 人気プランのランキング
- **曜日別稼働率**: 各曜日の予約数
- **価格統計**: 平均、最小、最大、中央値

### 4. AIマーケティングインサイト

`generate_marketing_insights()` メソッドが統計データを元に、実践的な提案を生成します。

**生成される内容:**
- ターゲット層の特徴
- 現状の課題（キャンセル率、リードタイム等）
- 推奨アクション（具体的なマーケティング施策）

## CSVエンコーディング自動判別

`_detect_encoding()` と `_load_csv()` メソッドが、以下のエンコーディングを自動判別します:

1. chardetによる自動検出
2. UTF-8
3. Shift_JIS
4. CP932（Windows版Shift_JIS）
5. EUC-JP
6. ISO-2022-JP

各エンコーディングで読み込みを試行し、成功したものを使用します。

## 使用例

### Pythonコードから使用

```python
from app.services.analysis_service import AnalysisService

# サービスを初期化
analysis_service = AnalysisService()

# CSVファイルを読み込み
with open("customer_data.csv", "rb") as f:
    file_content = f.read()

# 分析実行
statistics, insights = await analysis_service.analyze_csv(file_content)

print("統計情報:", statistics)
print("インサイト:", insights)
```

### curlでAPIを呼び出し

```bash
curl -X POST "http://localhost:8000/api/analysis/upload-csv" \
  -F "hotel_id=1" \
  -F "file=@customer_data.csv"
```

## 注意事項

### モデル名の指定

コード内で必ず `"gemini-3.1-flash-lite"` を指定してください。

```python
# ✅ 正しい
llm_client = get_llm_client(model_name="gemini-3.1-flash-lite")

# ❌ 間違い
llm_client = get_llm_client(model_name="gemini-2.0-flash-exp")
```

顧客分析以外の機能では別モデルを使用します。一覧は [ルート README](../../../README.md#使用-ai-モデル) を参照してください。

| モデル ID | 用途 |
|-----------|------|
| `gemini-3.5-flash` | LP 生成、プラン修正、高品質テキスト |
| `gemini-3.1-flash-image-preview` | 画像生成 |

### 環境変数

`.env` ファイルに `GOOGLE_API_KEY` を設定してください。

```bash
GOOGLE_API_KEY=your_api_key_here
```

### CSVフォーマット

推奨されるCSVフォーマット:
- ヘッダー行が必須
- 日付は ISO8601 形式または日本語形式（YYYY/MM/DD、YYYY-MM-DD等）
- 価格は数値形式（カンマ区切りも可）

## トラブルシューティング

### エンコーディングエラー

CSVファイルが正しく読み込めない場合、以下を確認してください:

1. ファイルが破損していないか
2. BOM付きUTF-8の場合、BOMを削除
3. 手動でエンコーディングを指定（必要に応じてコード修正）

### スキーマ推定の精度向上

スキーマ推定が正確でない場合:

1. CSVのヘッダー名を分かりやすくする（例: "予約日"、"宿泊日"）
2. サンプルデータ行数を増やす（`head(10)` → `head(20)`）
3. プロンプトに例を追加する

## 今後の拡張

- [ ] 複数CSVファイルの一括処理
- [ ] カスタムスキーママッピングの保存
- [ ] 時系列トレンド分析
- [ ] 地域別・年齢層別のセグメント分析
- [ ] 予測モデル（需要予測、キャンセル予測）

## ライセンス

このプロジェクトのライセンスに従います。

