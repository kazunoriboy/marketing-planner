# Marketing Planner Backend API

宿泊施設向けマーケティングAIエージェントのバックエンドAPI

## 🎯 概要

このAPIは、宿泊施設のマーケティング活動を支援するAIエージェントです。顧客データ分析、市場調査、マーケティングプラン生成、クリエイティブアセット生成の機能を提供します。

## 🏗️ アーキテクチャ

- **フレームワーク**: FastAPI
- **ORM**: SQLModel
- **データベース**: PostgreSQL (with pgvector)
- **AI**: Google Gemini（Google AI API 直接呼び出し）
- **データ分析**: Pandas

### LangChainを使用しない理由

シンプルで保守性の高いアーキテクチャを実現するため、AIモデルのAPIを直接呼び出す方式を採用しています。

### 使用 AI モデル

| モデル ID | 用途 |
|-----------|------|
| `gemini-3.1-flash-lite` | デフォルト（顧客分析、市場調査、プラン生成、運用チャットなど） |
| `gemini-3.5-flash` | LP 生成、プラン修正、高品質テキスト生成 |
| `gemini-3.1-flash-image-preview` | 広告・LP 用画像生成 |

## 📁 ディレクトリ構造

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPIアプリケーション
│   ├── models.py                  # SQLModelデータベースモデル
│   ├── core/                      # コア機能
│   │   ├── database.py            # データベース接続
│   │   ├── config.py              # 設定管理
│   │   └── llm.py                 # LLMクライアント（Google Gemini）
│   ├── api/                       # APIエンドポイント
│   │   ├── analysis.py            # 顧客分析・市場調査
│   │   ├── planning.py            # プラン作成
│   │   └── creative.py            # クリエイティブ生成
│   ├── services/                  # ビジネスロジック
│   │   ├── analysis_service.py    # 顧客分析サービス（新規）
│   │   ├── csv_analyzer.py        # CSV分析サービス（既存）
│   │   ├── plan_generator.py      # プラン生成サービス
│   │   └── creative_generator.py  # クリエイティブ生成サービス
│   └── schemas/                   # Pydanticスキーマ
│       ├── analysis.py
│       ├── planning.py
│       └── creative.py
├── docs/                          # ドキュメント
│   ├── README.md                  # ドキュメント一覧
│   ├── QUICKSTART.md              # クイックスタートガイド
│   ├── CUSTOMER_ANALYSIS_SPEC.md  # 顧客分析機能仕様書
│   ├── IMPLEMENTATION_GUIDE.md    # 実装ガイド
│   └── API_GUIDE.md               # APIガイド
├── tests/                         # テストコード
│   ├── __init__.py
│   ├── README.md                  # テストガイド
│   └── test_analysis.py           # 顧客分析機能のテスト
├── requirements.txt
├── Dockerfile
└── ENV_SETUP.md
```

## 🗄️ データベース設計

### 1. Hotel（宿泊施設）
- 基本情報（ID, 名前, 住所）
- 宿の特徴や強み（JSON形式）

### 2. AnalysisSession（分析セッション）
- CSV分析結果（統計情報とAIインサイト）
- 市場調査結果（競合リスト、口コミ要約、地域トレンド）

### 3. MarketingPlan（マーケティングプラン）
- ステータス（draft/approved）
- ターゲット層、プラン名、コンセプト
- 価格帯、特典リスト（JSON）
- 3C分析・PEST分析結果

### 4. CreativeAsset（制作物）
- LPのソースコード
- 広告用画像プロンプト
- 広告コピー（JSON）

## 🚀 API エンドポイント

### 分析 API (`/api/analysis`)

#### 宿泊施設管理
- `POST /api/analysis/hotels` - 宿泊施設を登録
- `GET /api/analysis/hotels` - 宿泊施設一覧を取得
- `GET /api/analysis/hotels/{hotel_id}` - 宿泊施設の詳細を取得

#### 顧客分析
- `POST /api/analysis/customer` - CSVファイルをアップロードして顧客データを分析（既存）
  - スキーマ自動推定（Gemini 3.1 Flash-Lite）
  - 統計情報計算（Pandas）
  - AIインサイト生成
- `POST /api/analysis/upload-csv` - CSVファイルをアップロードして顧客データを分析（新規・推奨）
  - エンコーディング自動判別（UTF-8、Shift_JIS等）
  - AIスキーマ推定（Gemini 3.1 Flash-Lite）
  - 統計情報計算（キャンセル率、リードタイム、人気プラン等）
  - マーケティングインサイト生成

#### 市場調査
- `POST /api/analysis/market` - 市場調査を実行
  - 競合リサーチ
  - 口コミ分析
  - 地域トレンド分析

### プラン作成 API (`/api/planning`)

- `POST /api/planning/generate` - マーケティングプランを生成
  - 3C分析・PEST分析を含む戦略的プラン
  - 複数プラン案の自動生成
- `GET /api/planning/plans/{plan_id}` - プラン詳細を取得
- `GET /api/planning/sessions/{session_id}/plans` - セッションのプラン一覧
- `PUT /api/planning/plans/{plan_id}/status` - プランステータス更新
- `DELETE /api/planning/plans/{plan_id}` - プラン削除

### クリエイティブ生成 API (`/api/creative`)

- `POST /api/creative/generate` - クリエイティブアセットを生成
  - LP（React + TypeScript + Tailwind CSS）
  - 広告画像生成用プロンプト
  - 広告コピー（Google Ads、Facebook Ads、Instagram等）
- `GET /api/creative/assets/{asset_id}` - アセット詳細を取得
- `GET /api/creative/plans/{plan_id}/assets` - プランのアセット一覧
- `DELETE /api/creative/assets/{asset_id}` - アセット削除

## 🔧 セットアップ

### 1. 環境変数の設定

環境ごとに `backend/.env` を用意し、必要な値を設定してください。

```bash
# env.example をコピーして .env を作成
cp env.example .env
# .env を編集して必須項目・オプションを設定
```

**必須**: `DATABASE_URL`, `GOOGLE_API_KEY`  
**施設画像利用時**: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`（Docker 内は `S3_ENDPOINT_URL=http://storage:9000`）

詳細は `ENV_SETUP.md` を参照してください。

### 2. Docker環境の起動

```bash
# プロジェクトルートで実行
docker compose up -d
```

### 3. APIドキュメントの確認

起動後、以下のURLでAPIドキュメントを確認できます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 使用例

### 1. 宿泊施設を登録

```bash
curl -X POST "http://localhost:8000/api/analysis/hotels" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "サンプル旅館",
    "address": "東京都新宿区",
    "features": {"温泉": true, "駐車場": true},
    "strengths": {"立地": "駅近"}
  }'
```

### 2. CSVファイルをアップロードして顧客分析

```bash
curl -X POST "http://localhost:8000/api/analysis/customer" \
  -F "hotel_id=1" \
  -F "file=@reservations.csv"
```

### 3. 市場調査を実行

```bash
curl -X POST "http://localhost:8000/api/analysis/market" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "address": "東京都新宿区",
    "radius_km": 5.0
  }'
```

### 4. マーケティングプランを生成

```bash
curl -X POST "http://localhost:8000/api/planning/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_session_id": 1,
    "num_plans": 3
  }'
```

### 5. クリエイティブアセットを生成

```bash
curl -X POST "http://localhost:8000/api/creative/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "marketing_plan_id": 1,
    "generate_lp": true,
    "generate_images": true,
    "generate_ad_copy": true
  }'
```

## 🧪 開発

### 依存関係のインストール

```bash
pip install -r requirements.txt
```

### ローカルで実行

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 ドキュメント

詳細なドキュメントは `docs/` ディレクトリを参照してください：

- **[クイックスタート](docs/QUICKSTART.md)** - 5分で始める顧客分析機能
- **[機能仕様書](docs/CUSTOMER_ANALYSIS_SPEC.md)** - 顧客分析機能の詳細仕様
- **[実装ガイド](docs/IMPLEMENTATION_GUIDE.md)** - 技術的な実装詳細
- **[APIガイド](docs/API_GUIDE.md)** - エンドポイントの詳細

## 🧪 テスト

テストコードは `tests/` ディレクトリにあります。

### 初回セットアップ

```bash
# 依存関係のインストール
docker compose exec backend pip install -r requirements.txt
docker compose exec backend pip install chardet
```

### テスト実行

```bash
# テストスクリプトを実行（サンプルデータで自動テスト）
docker compose exec backend python tests/test_analysis.py

# pytestでの実行（今後追加予定）
docker compose exec backend python -m pytest tests/ -v
```

詳細は [tests/README.md](tests/README.md) を参照してください。

## 🚢 本番デプロイ

自動デプロイスクリプトは [`scripts/deploy.sh`](../scripts/deploy.sh) を使用します。EC2 への手動デプロイ手順の詳細は [DEPLOY.md](../DEPLOY.md) を参照してください（`docker-compose.prod.yml` を使用）。

## 📝 ライセンス

MIT License


