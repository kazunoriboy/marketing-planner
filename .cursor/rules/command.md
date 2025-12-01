---
description: 
globs: 
alwaysApply: true
---
# コマンド実行ルール

## 🚨 重要：すべてのコマンドはコンテナ内で実行する

このプロジェクトでは、**すべてのコマンドをDockerコンテナ内で実行する必要があります**。

## プロジェクト構成
- **Backend**: FastAPI + Python + LangChain
- **Frontend**: Next.js + TypeScript + Tailwind CSS  
- **Database**: PostgreSQL with pgvector

## 基本的なコマンド実行パターン

### 1. Python/FastAPIコマンド
```bash
# ❌ 間違い
python main.py
pip install package
uvicorn app.main:app

# ✅ 正しい
docker compose exec backend python main.py
docker compose exec backend pip install package
docker compose exec backend uvicorn app.main:app
```

### 2. Node.js/npmコマンド（フロントエンド）
```bash
# ❌ 間違い
npm install
npm run dev
npm run build

# ✅ 正しい
docker compose exec frontend npm install
docker compose exec frontend npm run dev
docker compose exec frontend npm run build
```

### 3. データベースコマンド
```bash
# ❌ 間違い
psql -U postgres
python manage.py migrate

# ✅ 正しい
docker compose exec db psql -U postgres
docker compose exec backend python -c "from app.main import *"
```

## よく使用するコマンド例

### 開発サーバー起動
```bash
# 全コンテナ起動
docker compose up -d

# 特定のサービス起動
docker compose up -d backend
docker compose up -d frontend
docker compose up -d db
```

### Python/FastAPI関連コマンド
```bash
# FastAPIサーバー起動
docker compose exec backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Pythonスクリプト実行
docker compose exec backend python -c "print('Hello from backend')"

# Pythonインタラクティブシェル
docker compose exec backend python

# パッケージ管理
docker compose exec backend pip install [package]
docker compose exec backend pip install -r requirements.txt
docker compose exec backend pip freeze > requirements.txt
```

### フロントエンド開発
```bash
# 開発サーバー起動
docker compose exec frontend npm run dev

# 本番用ビルド
docker compose exec frontend npm run build

# 本番サーバー起動
docker compose exec frontend npm run start

# Linting
docker compose exec frontend npm run lint
```

### パッケージ管理
```bash
# Pythonパッケージ
docker compose exec backend pip install [package]
docker compose exec backend pip install -r requirements.txt
docker compose exec backend pip freeze > requirements.txt

# Node.jsパッケージ
docker compose exec frontend npm install [package]
docker compose exec frontend npm install
docker compose exec frontend npm update
docker compose exec frontend npm uninstall [package]
```

### データベース管理
```bash
# PostgreSQL接続
docker compose exec db psql -U postgres

# データベース一覧確認
docker compose exec db psql -U postgres -c "\l"

# テーブル一覧確認
docker compose exec db psql -U postgres -d [database_name] -c "\dt"

# データベースダンプ
docker compose exec db pg_dump -U postgres [database_name] > backup.sql

# データベース復元
docker compose exec db psql -U postgres [database_name] < backup.sql

# pgvector拡張確認
docker compose exec db psql -U postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### ログ確認
```bash
# 全サービスのログ
docker compose logs -f

# 特定のサービスログ
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db

# リアルタイムログ確認
docker compose logs -f backend
docker compose logs -f frontend

# 最新のログのみ確認
docker compose logs --tail=50 backend
docker compose logs --tail=50 frontend
```

### デバッグ・トラブルシューティング
```bash
# コンテナ状態確認
docker compose ps

# コンテナ内部に入る
docker compose exec backend bash
docker compose exec frontend bash
docker compose exec db bash

# プロセス確認
docker compose exec backend ps aux
docker compose exec frontend ps aux

# ファイル確認
docker compose exec backend ls -la /app
docker compose exec frontend ls -la /app

# 環境変数確認
docker compose exec backend env
docker compose exec frontend env
```

## 開発ワークフロー別コマンド

### 新機能開発開始時
```bash
# 最新の状態に更新
docker compose pull
docker compose up -d --build

# 依存関係更新
docker compose exec backend pip install -r requirements.txt
docker compose exec frontend npm install

# サービス起動確認
docker compose exec backend python -c "import fastapi; print('FastAPI OK')"
docker compose exec frontend npm run build
```

### Python/FastAPI開発
```bash
# 新しいPythonパッケージ追加
docker compose exec backend pip install [package]
docker compose exec backend pip freeze > requirements.txt

# FastAPIアプリケーション確認
docker compose exec backend python -c "from app.main import app; print('App loaded successfully')"

# エンドポイント確認
curl http://localhost:8000/docs

# Pythonスクリプト実行
docker compose exec backend python -c "print('Hello from backend')"
```

### フロントエンド開発
```bash
# 新しいnpmパッケージ追加
docker compose exec frontend npm install [package]

# TypeScript型チェック
docker compose exec frontend npx tsc --noEmit

# ビルド確認
docker compose exec frontend npm run build

# 開発サーバー確認
curl http://localhost:3000
```

### AI/LangChain開発
```bash
# LangChain動作確認
docker compose exec backend python -c "import langchain; print('LangChain OK')"

# OpenAI接続確認
docker compose exec backend python -c "from langchain_openai import ChatOpenAI; print('OpenAI OK')"

# Google Gemini接続確認
docker compose exec backend python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('Gemini OK')"
```

## 環境管理コマンド

### コンテナ管理
```bash
# 全コンテナ起動
docker compose up -d

# 特定のサービス起動
docker compose up -d backend
docker compose up -d frontend
docker compose up -d db

# コンテナ停止
docker compose down

# コンテナ再起動
docker compose restart
docker compose restart backend
docker compose restart frontend

# コンテナ削除（データ保持）
docker compose down

# コンテナ削除（データも削除）
docker compose down -v

# 強制的な再構築
docker compose up -d --build --force-recreate
```

### パフォーマンス・監視
```bash
# コンテナリソース使用量確認
docker stats

# メモリ使用量確認
docker compose exec backend free -h
docker compose exec frontend free -h

# ストレージ使用量確認
docker compose exec backend df -h
docker compose exec frontend df -h

# プロセス確認
docker compose exec backend top
docker compose exec frontend top
```

## 覚えておくべきこと

- **Python/FastAPIコマンド**: `docker compose exec backend [コマンド]`
- **Node.js/npmコマンド**: `docker compose exec frontend [コマンド]`
- **PostgreSQLコマンド**: `docker compose exec db [コマンド]`
- **コンテナ管理**: `docker compose [コマンド]`

## 注意事項

1. **絶対にホストマシンで直接コマンドを実行しない**
2. **常に `docker compose exec [service]` を使用**
3. **コンテナが起動していない場合は先に `docker compose up -d` を実行**
4. **ファイル編集はホストマシンで行い、コマンド実行のみコンテナ内で行う**
5. **フロントエンドのライブラリインストールは必ずDockerコンテナ内で実行し、その後ローカルでnpm ciを実行して環境を同期する**

## トラブルシューティング

### コンテナが起動しない場合
```bash
# コンテナ状態確認
docker compose ps

# ログ確認
docker compose logs backend
docker compose logs frontend
docker compose logs db

# 強制的な再起動
docker compose down -v
docker compose up -d --build
```

### 依存関係エラーの場合
```bash
# バックエンド依存関係再インストール
docker compose exec backend pip install -r requirements.txt

# フロントエンド依存関係再インストール
docker compose exec frontend npm install
# その後ローカルで同期
cd frontend && npm ci
```

### データベース接続エラーの場合
```bash
# データベースコンテナ確認
docker compose exec db psql -U postgres

# 接続確認
docker compose exec backend python -c "import psycopg2; print('PostgreSQL OK')"

# 環境変数確認
docker compose exec backend env | grep DATABASE
```

### ポート競合エラーの場合
```bash
# 使用中のポート確認
lsof -i :3000
lsof -i :8000
lsof -i :5432

# 競合するプロセスを停止
sudo kill -9 [PID]
```

このルールを守らないと、環境の不一致や権限エラーが発生する可能性があります。

