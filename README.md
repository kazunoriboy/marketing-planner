# 宿泊業界向けマーケティングAIエージェント

## 概要
宿泊業界向けのマーケティングAIエージェントの開発環境です。FastAPI（バックエンド）、Next.js（フロントエンド）、PostgreSQL with pgvector（データベース）を使用しています。

## 技術スタック
- **フロントエンド**: Next.js 15 (TypeScript + Tailwind CSS)
- **バックエンド**: FastAPI (Python 3.13)
- **データベース**: PostgreSQL with pgvector
- **ORM**: SQLModel
- **AI**: Google Gemini 2.0 Flash (Google AI API直接呼び出し)
- **データ分析**: Pandas
- **コンテナ**: Docker & Docker Compose

### アーキテクチャの特徴
- **LangChainを使用しない設計**: シンプルで保守性の高いアーキテクチャ
- **直接API呼び出し**: 各AIモデルのSDKを直接使用
- **JSONカラム活用**: 柔軟なデータ構造の保存

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
├── backend/                      # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py               # メインアプリケーション
│   │   ├── models.py             # SQLModelデータベースモデル
│   │   ├── core/                 # コア機能
│   │   │   ├── database.py       # データベース接続
│   │   │   ├── config.py         # 設定管理
│   │   │   └── llm.py            # LLMクライアント
│   │   ├── api/                  # APIエンドポイント
│   │   │   ├── analysis.py       # 顧客分析・市場調査
│   │   │   ├── planning.py       # プラン作成
│   │   │   └── creative.py       # クリエイティブ生成
│   │   ├── services/             # ビジネスロジック
│   │   │   ├── csv_analyzer.py   # CSV分析サービス
│   │   │   ├── plan_generator.py # プラン生成サービス
│   │   │   └── creative_generator.py # クリエイティブ生成
│   │   └── schemas/              # Pydanticスキーマ
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── README.md                 # バックエンド詳細ドキュメント
│   ├── ENV_SETUP.md              # 環境変数設定ガイド
│   └── .env                      # 環境変数（要作成）
├── frontend/                     # Next.js フロントエンド
│   ├── src/
│   │   └── app/
│   │       └── page.tsx          # メインページ
│   ├── Dockerfile
│   ├── package.json
│   └── .env.local                # 環境変数（要作成）
├── docker-compose.yml            # Docker Compose設定
├── .env.db                       # データベース環境変数（要作成）
└── README.md
```

## 主な機能

### 1. 顧客データ分析 (`/api/analysis/customer`)
- CSVファイルのアップロード
- LLMによるスキーマ自動推定
- Pandasによる統計分析（キャンセル率、リードタイム、年齢分布等）
- AIによるマーケティングインサイト生成

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

## 開発時の注意事項

1. **Google API キーの設定**: `backend/.env` に `GOOGLE_API_KEY` を必ず設定してください
2. **ホットリロード**: 開発モードでは、コードの変更が自動的に反映されます
3. **データベース**: 初回起動時にテーブルが自動作成されます
4. **CORS**: フロントエンドとバックエンド間の通信は適切に設定されています
5. **メモリ使用**: Pandasでの大容量CSV処理時はメモリ使用量に注意してください

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
