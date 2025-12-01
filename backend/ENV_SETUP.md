# 環境変数設定ガイド

バックエンドを起動する前に、以下の環境変数を設定する必要があります。

## backend/.env ファイルを作成

`backend/.env` ファイルを作成し、以下の内容を設定してください：

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@db:5432/marketing_planner

# AI API Keys
GOOGLE_API_KEY=your_google_api_key_here

# External API Keys (Optional - for future use)
MANUS_API_KEY=your_manus_api_key_here
V0_API_KEY=your_v0_api_key_here
NANO_BANANA_API_KEY=your_nano_banana_api_key_here

# Application Settings
APP_NAME=Marketing Planner API
APP_VERSION=1.0.0
DEBUG=True

# CORS Settings
CORS_ORIGINS=http://localhost:3000
```

## 必須の設定

### 1. GOOGLE_API_KEY

Google Gemini 2.0 Flashを使用するために必要です。

1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. APIキーを取得
3. `GOOGLE_API_KEY` に設定

### 2. DATABASE_URL

PostgreSQLデータベースの接続URL。
Docker Composeを使用する場合は、デフォルトの設定で動作します。

## オプション設定

以下のAPIキーは、将来的な機能拡張で使用する予定です：

- `MANUS_API_KEY`: Manus APIによる検索機能
- `V0_API_KEY`: V0による高度なLP生成
- `NANO_BANANA_API_KEY`: Nano Banana Proによる画像生成

現時点では設定不要です。

## データベース設定（.env.db）

プロジェクトルートに `.env.db` ファイルを作成：

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=marketing_planner
```

## 起動方法

環境変数設定後、以下のコマンドでDocker環境を起動：

```bash
docker compose up -d
```

APIは http://localhost:8000 でアクセス可能になります。


