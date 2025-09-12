# 宿泊業界向けマーケティングAIエージェント

## 概要
宿泊業界向けのマーケティングAIエージェントの開発環境です。FastAPI（バックエンド）、Next.js（フロントエンド）、PostgreSQL with pgvector（データベース）を使用しています。

## 技術スタック
- **フロントエンド**: Next.js 15 (TypeScript + Tailwind CSS)
- **バックエンド**: FastAPI (Python 3.13)
- **データベース**: PostgreSQL with pgvector
- **AI**: LangChain + OpenAI + Google Gemini
- **コンテナ**: Docker & Docker Compose

## セットアップ手順

### 1. 環境変数ファイルの作成

以下の環境変数ファイルを作成してください：

#### `backend/.env`
```env
DATABASE_URL="postgresql://user:password@db:5432/mydatabase"
OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
```

#### `frontend/.env.local`
```env
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

#### `.env.db` (プロジェクトルート)
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=mydatabase
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
├── backend/                 # FastAPI バックエンド
│   ├── app/
│   │   └── main.py         # メインアプリケーション
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env               # 環境変数（要作成）
├── frontend/               # Next.js フロントエンド
│   ├── src/
│   │   └── app/
│   │       └── page.tsx   # メインページ
│   ├── Dockerfile
│   ├── package.json
│   └── .env.local         # 環境変数（要作成）
├── docker-compose.yml     # Docker Compose設定
├── .env.db               # データベース環境変数（要作成）
└── README.md
```

## 開発時の注意事項

1. **API キーの設定**: OpenAI API キーと Google API キーを `backend/.env` に設定してください
2. **ホットリロード**: 開発モードでは、コードの変更が自動的に反映されます
3. **データベース**: 初回起動時にPostgreSQLコンテナが自動的に作成されます
4. **CORS**: フロントエンドとバックエンド間の通信は適切に設定されています

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
