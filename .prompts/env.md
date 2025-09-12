これから、宿泊業界向けのマーケティングAIエージェントを開発するための、ローカル開発環境をセットアップします。以下の指示に従って、プロジェクトのファイルとディレクトリ構造を一度に生成してください。

### **1. 全体のディレクトリ構造**

まず、プロジェクトのルートに以下のディレクトリを作成します。
- `backend`: FastAPIアプリケーション用
- `frontend`: Next.jsアプリケーション用

### **2. バックエンド (`backend`ディレクトリ)**

FastAPIを使用してAPIサーバーを構築します。

- **Pythonのバージョン:** 3.13
- **`backend/Dockerfile`を作成:**
  - ベースイメージは`python:3.13-slim`を使用。
  - `requirements.txt`をインストールする手順を含める。
- **`backend/requirements.txt`を作成:**
  ```txt
  fastapi
  uvicorn[standard]
  psycopg2-binary
  python-dotenv
  
  # LangChain Core
  langchain
  langchain-openai
  langchain-google-genai
  
  # RAG / Vector Store
  pgvector
  ```
- **`backend/app/main.py`を作成:**
  - FastAPIの基本的なインスタンスを作成し、`@app.get("/")`で`{"message": "Hello from FastAPI Backend"}`を返す簡単なエンドポイントを1つ用意する。
- **`backend/.env`を作成:**
  ```dotenv
  DATABASE_URL="postgresql://user:password@db:5432/mydatabase"
  OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"
  GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
  ```

### **3. フロントエンド (`frontend`ディレクトリ)**

Next.js (TypeScript) を使用してフロントエンドを構築します。

- **Node.jsのバージョン:** 22 (LTS)
- **`frontend/Dockerfile`を作成:**
  - ベースイメージは`node:22-alpine`を使用。
  - `npm install`と`npm run dev`を実行する手順を含める。
- **`frontend/.env.local`を作成:**
  ```dotenv
  NEXT_PUBLIC_API_URL="http://localhost:8000"
  ```
- **`frontend`の初期設定:**
  - `create-next-app`を使ってTypeScript, Tailwind CSS, App Routerが有効な状態で初期化する。
  - `app/page.tsx`を編集し、バックエンドAPI(`NEXT_PUBLIC_API_URL`)からデータを取得して表示する簡単な非同期コンポーネントを実装する。

### **4. Docker Compose (プロジェクトルート)**

プロジェクトのルートディレクトリに`docker-compose.yml`を作成します。各コンテナを連携させて開発環境全体を定義します。

- **`docker-compose.yml`を作成:**
  ```yaml
  version: '3.8'

  services:
    backend:
      build:
        context: ./backend
        dockerfile: Dockerfile
      command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      volumes:
        - ./backend:/app
      ports:
        - "8000:8000"
      env_file:
        - ./backend/.env
      depends_on:
        - db

    frontend:
      build:
        context: ./frontend
        dockerfile: Dockerfile
      command: npm run dev
      volumes:
        - ./frontend:/app
        - /app/node_modules
        - /app/.next
      ports:
        - "3000:3000"
      env_file:
        - ./frontend/.env.local
      depends_on:
        - backend

    db:
      image: pgvector/pgvector:pg16
      volumes:
        - postgres_data:/var/lib/postgresql/data/
      env_file:
        - ./.env.db
      ports:
        - "5432:5432"

  volumes:
    postgres_data:
  ```

.env.dbを作成 (プロジェクトルート):
```
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=mydatabase
```
以上のすべてのファイルとディレクトリを生成してください。