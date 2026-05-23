# EC2 デプロイ手順書（Amazon Linux 2023）

このドキュメントでは、Marketing Planner アプリケーションを AWS EC2 (Amazon Linux 2023) に Docker Compose を使用してデプロイする手順を説明します。

**デプロイ先ドメイン**: `ai-marketing.poseidon-inc.com`

> **Note**: デプロイは [`scripts/deploy.sh`](scripts/deploy.sh) で自動化できます。初回セットアップ後の再デプロイは `./scripts/deploy.sh deploy` が基本です。

## 🚀 デプロイスクリプト（推奨）

### EC2 に環境変数ファイルが既にある場合

`backend/.env`、`.env.db`、`frontend/.env.local` は **docker compose が直接読み込み**ます。deploy スクリプトはこれらを **上書きしません**。

```bash
cd ~/marketing-planner

# 既存ファイルが使えるか確認
./scripts/deploy.sh check-env

# そのまま再デプロイ
./scripts/deploy.sh deploy
```

`scripts/deploy.env` は **任意**です。未作成でも deploy 可能で、ドメインは `backend/.env` の `CORS_ORIGINS` から自動検出されます。

### 初回セットアップ / deploy.env を使う場合

```bash
# 1. 設定ファイルを作成（任意）
cp scripts/deploy.env.example scripts/deploy.env
nano scripts/deploy.env   # DOMAIN, CERTBOT_EMAIL など

# 2. EC2 初回のみ: ホストセットアップ
./scripts/deploy.sh setup-host

# 3. 環境変数ファイルが無い場合のみ
./scripts/deploy.sh setup-env

# 4. 初回のみ: SSL 証明書取得
./scripts/deploy.sh setup-ssl

# 5. 初回のみ: 管理者作成
./scripts/deploy.sh seed-admin

# 6. 証明書自動更新 cron 登録（任意）
./scripts/deploy.sh install-ssl-cron

# 通常の再デプロイ
./scripts/deploy.sh deploy
```

| コマンド | 説明 |
|---------|------|
| `check-env` | 既存の `.env` ファイルを確認（上書きしない） |
| `deploy` | git pull → build → up → migrate（通常利用） |
| `setup-env` | **不足ファイルのみ** example から作成（既存は保持） |
| `setup-host` | Docker / Compose / certbot を EC2 にインストール |
| `setup-ssl` | 初回 Let's Encrypt 取得と HTTPS 有効化 |
| `renew-ssl` | 証明書更新 + nginx 再起動 |
| `install-ssl-cron` | `renew-ssl` の cron 登録 |
| `migrate` | DB マイグレーションのみ |
| `seed-admin` | 初期管理者作成 |

詳細は `./scripts/deploy.sh help` を参照してください。

---

- AWS アカウント
- EC2 への SSH アクセス
- ドメイン `ai-marketing.poseidon-inc.com` の DNS 設定権限

## 🌐 DNS 設定（事前準備）

EC2 インスタンス作成後、DNS の A レコードを設定してください：

```
ai-marketing.poseidon-inc.com → EC2のパブリックIP
```

## 🖥️ EC2 インスタンスの準備

### 1. EC2 インスタンスの作成

1. AWS コンソールで EC2 ダッシュボードを開く
2. **インスタンスを起動** をクリック
3. 以下の設定を推奨:
   - **AMI**: Amazon Linux 2023
   - **インスタンスタイプ**: t3.medium 以上（メモリ 4GB 以上推奨）
   - **ストレージ**: 30GB 以上（画像生成機能を使用する場合は 50GB 推奨）
   - **キーペア**: 新規作成または既存のキーペアを選択

### 2. セキュリティグループの設定

以下のインバウンドルールを設定:

| タイプ | ポート | ソース | 説明 |
|-------|-------|--------|------|
| SSH | 22 | 自分のIP | SSH アクセス |
| HTTP | 80 | 0.0.0.0/0 | HTTP アクセス（HTTPSリダイレクト用） |
| HTTPS | 443 | 0.0.0.0/0 | HTTPS アクセス |

## 🔧 EC2 インスタンスのセットアップ

### 1. SSH で接続

```bash
ssh -i your-key.pem ec2-user@EC2のパブリックIP
```

### 2. システムの更新

```bash
sudo dnf update -y
```

### 3. Docker のインストール

```bash
# Docker をインストール
sudo dnf install -y docker

# Docker サービスを起動・自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# ec2-user を docker グループに追加
sudo usermod -aG docker ec2-user

# グループを反映（再ログインでも可）
newgrp docker
```

### 4. Docker Compose のインストール

```bash
# Docker Compose プラグインをインストール
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 動作確認
docker compose version
```

### 5. Git のインストール

```bash
sudo dnf install -y git
```

### 6. 動作確認

```bash
docker --version
docker compose version
git --version
```

## 📦 アプリケーションのデプロイ

### 1. プロジェクトをクローン

```bash
cd ~
git clone https://github.com/your-username/marketing-planner.git
cd marketing-planner
```

### 2. 環境変数の設定

```bash
# バックエンド環境変数
cp backend/env.example backend/.env

# データベース環境変数
cp env.db.example .env.db

# フロントエンド環境変数（空でOK、ビルド引数で設定済み）
touch frontend/.env.local
```

#### backend/.env を編集

```bash
nano backend/.env
```

> **nano がない場合**: `sudo dnf install -y nano` でインストール、または `vi` を使用

以下の値を設定:

```env
# データベース（パスワードを変更）
DATABASE_URL=postgresql://postgres:YOUR_SECURE_PASSWORD@db:5432/marketing_planner

# Google API キー（必須）
GOOGLE_API_KEY=your_actual_google_api_key

# JWT シークレット（以下のコマンドで生成）
# openssl rand -hex 32
JWT_SECRET_KEY=生成したシークレットキー

# CORS（このまま）
CORS_ORIGINS=https://ai-marketing.poseidon-inc.com

# デバッグ無効
DEBUG=False

# 初期管理者（必要に応じて設定）
INITIAL_ADMIN_EMAIL=admin@poseidon-inc.com
INITIAL_ADMIN_PASSWORD=安全なパスワード
```

#### .env.db を編集

```bash
nano .env.db
```

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD  # backend/.env と同じパスワード
POSTGRES_DB=marketing_planner
```

### 3. SSL証明書の取得（Let's Encrypt）

#### Step 1: 初期設定でNginxを起動

```bash
# 初期設定ファイルを使用
cp nginx/nginx.initial.conf nginx/nginx.conf

# certbot用ディレクトリを作成
mkdir -p nginx/ssl

# アプリケーションをビルド・起動
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

#### Step 2: certbotでSSL証明書を取得

```bash
# certbot をインストール（AL2023）
sudo dnf install -y certbot

# webroot認証用ディレクトリを作成
sudo mkdir -p /var/www/certbot

# 一時的にNginxを停止してスタンドアロンモードで証明書取得
docker compose -f docker-compose.prod.yml stop nginx

# 証明書を取得（スタンドアロンモード）
sudo certbot certonly --standalone -d ai-marketing.poseidon-inc.com

# または webroot モードを使用する場合（Nginxが動いている状態で）
# sudo certbot certonly --webroot -w /var/www/certbot -d ai-marketing.poseidon-inc.com
```

#### Step 3: 証明書をコピー

```bash
# SSL証明書をプロジェクトにコピー
sudo cp /etc/letsencrypt/live/ai-marketing.poseidon-inc.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/ai-marketing.poseidon-inc.com/privkey.pem nginx/ssl/
sudo chown -R ec2-user:ec2-user nginx/ssl
```

#### Step 4: HTTPS設定に切り替え

```bash
# HTTPS用の設定ファイルをコピー
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    client_max_body_size 50M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml application/javascript application/json;

    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name ai-marketing.poseidon-inc.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name ai-marketing.poseidon-inc.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;

        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        location /api/ {
            rewrite ^/api/(.*) /$1 break;
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
        }

        location /static/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_cache_valid 200 1d;
            add_header Cache-Control "public, max-age=86400";
        }

        location /health {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }
    }
}
EOF

# 全サービスを起動
docker compose -f docker-compose.prod.yml up -d
```

### 4. 初期管理者ユーザーの作成

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.seed_admin
```

### 5. 動作確認

```bash
# コンテナのステータス確認
docker compose -f docker-compose.prod.yml ps

# ログの確認
docker compose -f docker-compose.prod.yml logs -f
```

ブラウザでアクセス:
- **バックエンドAPI**: https://ai-marketing.poseidon-inc.com/api/docs

## 🔄 SSL証明書の自動更新

Let's Encrypt の証明書は90日で期限切れになります。

```bash
# cron 登録（推奨）
./scripts/deploy.sh install-ssl-cron

# 手動更新（nginx を一時停止して certbot を実行）
./scripts/deploy.sh renew-ssl
```

手動で crontab を編集する場合:

```cron
# 毎月1日と15日の午前3時に証明書を更新
0 3 1,15 * * sudo certbot renew --quiet && sudo cp /etc/letsencrypt/live/ai-marketing.poseidon-inc.com/fullchain.pem /home/ec2-user/marketing-planner/nginx/ssl/ && sudo cp /etc/letsencrypt/live/ai-marketing.poseidon-inc.com/privkey.pem /home/ec2-user/marketing-planner/nginx/ssl/ && sudo chown ec2-user:ec2-user /home/ec2-user/marketing-planner/nginx/ssl/* && docker compose -f /home/ec2-user/marketing-planner/docker-compose.prod.yml restart nginx
```

## 🔄 更新・再デプロイ

```bash
cd ~/marketing-planner
./scripts/deploy.sh deploy
```

手動で実行する場合:

```bash
cd ~/marketing-planner

# 最新コードを取得
git pull origin main

# イメージを再ビルド
docker compose -f docker-compose.prod.yml build

# コンテナを再起動
docker compose -f docker-compose.prod.yml up -d

# マイグレーション
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.migrate upgrade

# 古いイメージを削除
docker image prune -f
```

## 🛠️ トラブルシューティング

### ログの確認

```bash
# 全サービスのログ
docker compose -f docker-compose.prod.yml logs

# 特定のサービスのログ
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs frontend
docker compose -f docker-compose.prod.yml logs nginx
docker compose -f docker-compose.prod.yml logs db

# リアルタイムでログを追跡
docker compose -f docker-compose.prod.yml logs -f
```

### コンテナへのアクセス

```bash
# バックエンドコンテナにアクセス
docker compose -f docker-compose.prod.yml exec backend bash

# データベースにアクセス
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d marketing_planner
```

### 再起動

```bash
# 特定のサービスを再起動
docker compose -f docker-compose.prod.yml restart backend

# 全サービスを再起動
docker compose -f docker-compose.prod.yml restart
```

### データのバックアップ

```bash
# データベースのバックアップ
docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres marketing_planner > backup_$(date +%Y%m%d).sql

# バックアップからリストア
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U postgres marketing_planner
```

### コンテナとボリュームの完全リセット

```bash
# 全て停止・削除（データも削除されます）
docker compose -f docker-compose.prod.yml down -v

# 再度起動
docker compose -f docker-compose.prod.yml up -d
```

## 📊 モニタリング

### ディスク使用量の確認

```bash
# Docker のディスク使用量
docker system df

# 不要なリソースの削除
docker system prune -a
```

### リソース使用状況

```bash
# コンテナのリソース使用状況
docker stats
```

## 🔐 セキュリティチェックリスト

- [ ] JWT_SECRET_KEY を `openssl rand -hex 32` で生成した値に変更
- [ ] データベースパスワードを推測困難な値に変更
- [ ] セキュリティグループで不要なポートを閉じる（22, 80, 443のみ）
- [ ] DEBUG=False に設定
- [ ] SSL証明書の自動更新を設定
- [ ] 定期的なバックアップを設定

## 📝 環境変数一覧

### バックエンド (backend/.env)

| 変数名 | 必須 | 設定値 |
|--------|------|--------|
| DATABASE_URL | ✅ | postgresql://postgres:PASSWORD@db:5432/marketing_planner |
| GOOGLE_API_KEY | ✅ | Google Gemini API キー（下記モデル利用） |
| JWT_SECRET_KEY | ✅ | `openssl rand -hex 32` で生成 |
| CORS_ORIGINS | ✅ | https://ai-marketing.poseidon-inc.com |
| DEBUG | - | False |
| INITIAL_ADMIN_EMAIL | - | 初期管理者メールアドレス |
| INITIAL_ADMIN_PASSWORD | - | 初期管理者パスワード |

### データベース (.env.db)

| 変数名 | 必須 | 設定値 |
|--------|------|--------|
| POSTGRES_USER | ✅ | postgres |
| POSTGRES_PASSWORD | ✅ | DATABASE_URL と同じパスワード |
| POSTGRES_DB | ✅ | marketing_planner |

### 使用 AI モデル

本番・開発ともに `GOOGLE_API_KEY` 1 つで以下のモデルを利用します。

| モデル ID | 用途 |
|-----------|------|
| `gemini-3.1-flash-lite` | デフォルト（分析、プラン生成、運用チャットなど） |
| `gemini-3.5-flash` | LP 生成、プラン修正、高品質テキスト |
| `gemini-3.1-flash-image-preview` | 画像生成 |

---

## 🚀 クイックスタートコマンド一覧（AL2023）

```bash
# 1. EC2にSSH接続
ssh -i your-key.pem ec2-user@EC2のIP

# 2. システム更新とDockerインストール（初回のみ）
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
newgrp docker

# 3. Docker Composeインストール
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 4. プロジェクトクローン
git clone https://github.com/your-username/marketing-planner.git
cd marketing-planner

# 5. 環境変数設定
cp backend/env.example backend/.env
cp env.db.example .env.db
touch frontend/.env.local
nano backend/.env  # 編集
nano .env.db       # 編集

# 6. 初期起動（HTTP）
cp nginx/nginx.initial.conf nginx/nginx.conf
mkdir -p nginx/ssl
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 7. SSL証明書取得
sudo dnf install -y certbot
docker compose -f docker-compose.prod.yml stop nginx
sudo certbot certonly --standalone -d ai-marketing.poseidon-inc.com
sudo cp /etc/letsencrypt/live/ai-marketing.poseidon-inc.com/*.pem nginx/ssl/
sudo chown -R ec2-user:ec2-user nginx/ssl

# 8. HTTPS有効化（nginx/nginx.conf を上記の内容に更新）
docker compose -f docker-compose.prod.yml up -d

# 9. 管理者作成
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.seed_admin
```

完了後、https://ai-marketing.poseidon-inc.com にアクセスしてください！
