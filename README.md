# 宿泊業界向けマーケティングAIエージェント

## 概要
宿泊業界向けのマーケティングAIエージェントの開発環境です。FastAPI（バックエンド）、Next.js（フロントエンド）、PostgreSQL with pgvector（データベース）を使用しています。

## 技術スタック
- **フロントエンド**: Next.js 15 (TypeScript + Tailwind CSS)
- **バックエンド**: FastAPI (Python 3.13)
- **データベース**: PostgreSQL with pgvector
- **ORM**: SQLModel
- **AI**: Google Gemini（Google AI API 直接呼び出し）
- **データ分析**: Pandas
- **ストレージ**: S3互換（RustFS / 施設画像保存用）
- **コンテナ**: Docker & Docker Compose

### アーキテクチャの特徴
- **LangChainを使用しない設計**: シンプルで保守性の高いアーキテクチャ
- **直接API呼び出し**: 各AIモデルのSDKを直接使用
- **JSONカラム活用**: 柔軟なデータ構造の保存
- **エンコーディング自動判別**: CSV処理で複数エンコーディングに対応

## セットアップ手順

### 1. 環境変数ファイルの作成

以下の環境変数ファイルを作成してください：

#### `backend/.env`
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/marketing_planner
GOOGLE_API_KEY=your_google_api_key_here

# Optional - for future use
MANUS_API_KEY=your_manus_api_key_here
V0_API_KEY=your_v0_api_key_here
NANO_BANANA_API_KEY=your_nano_banana_api_key_here

APP_NAME=Marketing Planner API
APP_VERSION=1.0.0
DEBUG=True
CORS_ORIGINS=http://localhost:3000
```

**必須**: `GOOGLE_API_KEY` は [Google AI Studio](https://makersuite.google.com/app/apikey) から取得してください。

#### `frontend/.env.local`
```env
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

#### `.env.db` (プロジェクトルート)
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=marketing_planner
```

#### S3互換ストレージ（施設画像保存用）

施設画像のアップロード・表示を使う場合は、`backend/.env` に以下を追加してください（Docker Compose の `storage` を使う場合の例）。

```env
# Docker 内: http://storage:9000 / ローカル単体実行: http://localhost:9000
S3_ENDPOINT_URL=http://storage:9000
S3_ACCESS_KEY=rustfsadmin
S3_SECRET_KEY=rustfsadmin
S3_BUCKET=facility-images
```

未設定のまま施設画像にアクセスすると「ストレージ接続に失敗しました」となります。`backend/env.example` にも同じ項目が記載されています。

### 2. Docker環境の起動

```bash
# 全サービスを起動
docker compose up --build

# バックグラウンドで起動
docker compose up -d --build
```

### 3. アクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **APIドキュメント（Swagger）**: http://localhost:8000/docs
- **APIドキュメント（ReDoc）**: http://localhost:8000/redoc
- **データベース**: localhost:5432
- **S3互換ストレージ（RustFS）コンソール**: http://localhost:9001

### 4. 開発コマンド

```bash
# ログの確認
docker compose logs -f

# 特定のサービスのログ
docker compose logs -f backend
docker compose logs -f frontend

# サービスの停止
docker compose down

# ボリュームも含めて完全削除
docker compose down -v
```

## プロジェクト構造

```
marketing-planner/
├── backend/                         # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py                  # メインアプリケーション
│   │   ├── models.py                # SQLModelデータベースモデル
│   │   ├── core/                    # コア機能
│   │   │   ├── database.py          # データベース接続
│   │   │   ├── config.py            # 設定管理
│   │   │   └── llm.py               # LLMクライアント（Google Gemini）
│   │   ├── api/                     # APIエンドポイント
│   │   │   ├── analysis.py          # 顧客分析・市場調査
│   │   │   ├── planning.py          # プラン作成
│   │   │   └── creative.py          # クリエイティブ生成
│   │   ├── services/                # ビジネスロジック
│   │   │   ├── analysis_service.py  # 顧客分析サービス（新規）
│   │   │   ├── csv_analyzer.py      # CSV分析サービス（既存）
│   │   │   ├── plan_generator.py    # プラン生成サービス
│   │   │   └── creative_generator.py # クリエイティブ生成
│   │   └── schemas/                 # Pydanticスキーマ
│   ├── docs/                        # ドキュメント
│   │   ├── README.md                # ドキュメント一覧
│   │   ├── QUICKSTART.md            # クイックスタートガイド
│   │   ├── CUSTOMER_ANALYSIS_SPEC.md # 顧客分析機能仕様書
│   │   ├── IMPLEMENTATION_GUIDE.md  # 実装ガイド
│   │   └── API_GUIDE.md             # APIガイド
│   ├── tests/                       # テストコード
│   │   ├── __init__.py
│   │   ├── README.md                # テストガイド
│   │   └── test_analysis.py         # 顧客分析機能のテスト
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── README.md                    # バックエンド詳細ドキュメント
│   ├── ENV_SETUP.md                 # 環境変数設定ガイド
│   └── .env                         # 環境変数（要作成）
├── frontend/                        # Next.js フロントエンド
│   ├── src/
│   │   └── app/
│   │       └── page.tsx             # メインページ
│   ├── Dockerfile
│   ├── package.json
│   └── .env.local                   # 環境変数（要作成）
├── docker-compose.yml               # Docker Compose設定
├── .env.db                          # データベース環境変数（要作成）
└── README.md                        # このファイル
```

## 主な機能

### 1. 顧客データ分析 (`/api/analysis/upload-csv` 🆕)
- **CSVファイルのアップロード**: 複数エンコーディング自動判別（UTF-8、Shift_JIS等）
- **AIスキーマ推定**: Gemini 3.1 Flash-Lite が CSV 構造を自動解析
- **統計分析**: キャンセル率、リードタイム、人気プラン、曜日別稼働率、価格統計
- **マーケティングインサイト生成**: 実践的な施策提案

**詳細**: [顧客分析機能クイックスタート](backend/docs/QUICKSTART.md)

### 2. 市場調査 (`/api/analysis/market`)
- 競合施設のリサーチ
- 口コミ分析
- 地域トレンド分析

### 3. マーケティングプラン生成 (`/api/planning`)
- 3C分析（Customer, Competitor, Company）
- PEST分析（Political, Economic, Social, Technological）
- 複数のプラン案を自動生成
- ターゲット層、価格設定、特典の提案

### 4. クリエイティブアセット生成 (`/api/creative`)
- **ランディングページ**: React + TypeScript + Tailwind CSSのコード生成
- **広告画像**: 画像生成AIプロンプトの作成
- **広告コピー**: Google Ads、Facebook Ads、Instagram等の広告文生成

## 使用 AI モデル

Google Gemini API を用途別に使い分けています（`backend/app/core/llm.py`）。

| モデル ID | 用途 |
|-----------|------|
| `gemini-3.1-flash-lite` | デフォルト（顧客分析、市場調査、プラン生成、運用チャット、画像分析など） |
| `gemini-3.5-flash` | LP 生成、プラン修正、高品質テキスト生成 |
| `gemini-3.1-flash-image-preview` | 広告・LP 用画像生成 |

## 📚 ドキュメント

詳細なドキュメントは以下を参照してください：

- **[バックエンドREADME](backend/README.md)** - API全体の概要
- **[クイックスタート](backend/docs/QUICKSTART.md)** - 5分で始める顧客分析機能
- **[機能仕様書](backend/docs/CUSTOMER_ANALYSIS_SPEC.md)** - 顧客分析機能の詳細仕様
- **[実装ガイド](backend/docs/IMPLEMENTATION_GUIDE.md)** - 技術的な実装詳細
- **[EC2 デプロイ手順](DEPLOY.md)** - 本番環境デプロイ（[`scripts/deploy.sh`](scripts/deploy.sh) 推奨）

## 🧪 テスト

### 初回セットアップ

```bash
# 依存関係のインストール
docker compose exec backend pip install -r requirements.txt
docker compose exec backend pip install chardet
```

### テスト実行

```bash
# 顧客分析機能のテスト（サンプルデータで自動実行）
docker compose exec backend python tests/test_analysis.py

# pytestでの実行（今後追加予定）
docker compose exec backend python -m pytest tests/ -v
```

## 開発時の注意事項

1. **Google API キーの設定**: `backend/.env` に `GOOGLE_API_KEY` を必ず設定してください
2. **ホットリロード**: 開発モードでは、コードの変更が自動的に反映されます
3. **データベース**: 初回起動時にテーブルが自動作成されます
4. **CORS**: フロントエンドとバックエンド間の通信は適切に設定されています
5. **メモリ使用**: Pandasでの大容量CSV処理時はメモリ使用量に注意してください
6. **エンコーディング**: CSVファイルは自動判別されますが、推奨はUTF-8です

## トラブルシューティング

### ポートが既に使用されている場合
```bash
# 使用中のポートを確認
lsof -i :3000
lsof -i :8000
lsof -i :5432

# プロセスを終了
kill -9 <PID>
```

### コンテナの再ビルド
```bash
# キャッシュを無視して再ビルド
docker compose build --no-cache
docker compose up
```

### データベースのリセット
```bash
# ボリュームを削除してデータベースをリセット
docker compose down -v
docker compose up
```
