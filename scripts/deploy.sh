#!/usr/bin/env bash
#
# Marketing Planner 本番デプロイスクリプト
#
# アプリの環境変数は docker compose が直接読み込みます（上書きしません）:
#   - backend/.env
#   - .env.db
#   - frontend/.env.local（本番 compose では未使用だが存在確認のみ）
#
# scripts/deploy.env はデプロイ設定専用（任意）です。
#
# 使い方:
#   ./scripts/deploy.sh deploy          # 通常の再デプロイ（デフォルト）
#   ./scripts/deploy.sh check-env       # 環境変数ファイルの確認
#   ./scripts/deploy.sh setup-env       # 不足ファイルのみ example から作成
#   ./scripts/deploy.sh setup-ssl       # 初回 SSL 証明書取得
#   ./scripts/deploy.sh renew-ssl       # SSL 証明書更新
#   ./scripts/deploy.sh migrate         # DB マイグレーション
#   ./scripts/deploy.sh seed-admin      # 初期管理者作成
#   ./scripts/deploy.sh setup-host      # EC2 初回セットアップ（Docker 等）
#   ./scripts/deploy.sh help
#
# 設定（任意）:
#   scripts/deploy.env を作成（deploy.env.example を参照）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DOMAIN_EXPLICIT=0
if [[ -f "${SCRIPT_DIR}/deploy.env" ]] && grep -qE '^DOMAIN=' "${SCRIPT_DIR}/deploy.env"; then
  DOMAIN_EXPLICIT=1
fi

if [[ -f "${SCRIPT_DIR}/deploy.env" ]]; then
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/deploy.env"
fi

DOMAIN="${DOMAIN:-ai-marketing.poseidon-inc.com}"
GIT_BRANCH="${GIT_BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
CERT_PATH="${CERT_PATH:-/etc/letsencrypt/live/${DOMAIN}}"
SKIP_GIT_PULL="${SKIP_GIT_PULL:-0}"
BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-backend/.env}"
DB_ENV_FILE="${DB_ENV_FILE:-.env.db}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-frontend/.env.local}"

COMPOSE_PATH="${PROJECT_ROOT}/${COMPOSE_FILE}"
SSL_DIR="${PROJECT_ROOT}/nginx/ssl"
BACKEND_ENV_PATH=""
DB_ENV_PATH=""
FRONTEND_ENV_PATH=""

log() {
  echo "[deploy] $*"
}

die() {
  echo "[deploy] ERROR: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "コマンドが見つかりません: $1"
}

compose() {
  require_command docker
  docker compose -f "${COMPOSE_PATH}" "$@"
}

ensure_project_root() {
  [[ -f "${COMPOSE_PATH}" ]] || die "Compose ファイルが見つかりません: ${COMPOSE_PATH}"
  cd "${PROJECT_ROOT}"
}

resolve_path() {
  local path="$1"
  if [[ "${path}" == /* ]]; then
    echo "${path}"
  else
    echo "${PROJECT_ROOT}/${path}"
  fi
}

read_env_value() {
  local file="$1"
  local key="$2"
  local line value

  [[ -f "${file}" ]] || return 1
  line="$(grep -E "^${key}=" "${file}" | tail -1 || true)"
  [[ -n "${line}" ]] || return 1
  value="${line#*=}"
  value="${value%$'\r'}"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  echo "${value}"
}

detect_domain_from_backend_env() {
  local backend_env="$1"
  local cors origin

  cors="$(read_env_value "${backend_env}" "CORS_ORIGINS" || true)"
  [[ -n "${cors}" ]] || return 1

  origin="${cors%%,*}"
  origin="${origin#https://}"
  origin="${origin#http://}"
  origin="${origin%%/*}"
  [[ -n "${origin}" ]] || return 1
  echo "${origin}"
}

init_runtime_config() {
  ensure_project_root

  BACKEND_ENV_PATH="$(resolve_path "${BACKEND_ENV_FILE}")"
  DB_ENV_PATH="$(resolve_path "${DB_ENV_FILE}")"
  FRONTEND_ENV_PATH="$(resolve_path "${FRONTEND_ENV_FILE}")"

  if [[ "${DOMAIN_EXPLICIT}" -eq 0 && -f "${BACKEND_ENV_PATH}" ]]; then
    local detected_domain
    detected_domain="$(detect_domain_from_backend_env "${BACKEND_ENV_PATH}" || true)"
    if [[ -n "${detected_domain}" ]]; then
      DOMAIN="${detected_domain}"
    fi
  fi

  CERT_PATH="${CERT_PATH:-/etc/letsencrypt/live/${DOMAIN}}"

  if [[ -z "${CERTBOT_EMAIL:-}" && -f "${BACKEND_ENV_PATH}" ]]; then
    CERTBOT_EMAIL="$(read_env_value "${BACKEND_ENV_PATH}" "INITIAL_ADMIN_EMAIL" || true)"
  fi
}

log_env_sources() {
  log "使用する環境変数ファイル:"
  log "  backend : ${BACKEND_ENV_PATH} $([[ -f "${BACKEND_ENV_PATH}" ]] && echo '[OK]' || echo '[MISSING]')"
  log "  database: ${DB_ENV_PATH} $([[ -f "${DB_ENV_PATH}" ]] && echo '[OK]' || echo '[MISSING]')"
  log "  frontend: ${FRONTEND_ENV_PATH} $([[ -f "${FRONTEND_ENV_PATH}" ]] && echo '[OK]' || echo '[optional]')"
  log "  domain  : ${DOMAIN}"
}

ensure_env_files() {
  init_runtime_config

  if [[ ! -f "${BACKEND_ENV_PATH}" ]]; then
    die "backend 環境変数ファイルが見つかりません: ${BACKEND_ENV_PATH}
docker compose は ${BACKEND_ENV_FILE} を参照します。
既存ファイルのパスが異なる場合は scripts/deploy.env に BACKEND_ENV_FILE を設定してください。"
  fi

  if [[ ! -f "${DB_ENV_PATH}" ]]; then
    die "DB 環境変数ファイルが見つかりません: ${DB_ENV_PATH}
docker compose は ${DB_ENV_FILE} を参照します。
既存ファイルのパスが異なる場合は scripts/deploy.env に DB_ENV_FILE を設定してください。"
  fi

  log_env_sources
}

copy_ssl_certs() {
  [[ -f "${CERT_PATH}/fullchain.pem" ]] || die "証明書が見つかりません: ${CERT_PATH}/fullchain.pem"
  [[ -f "${CERT_PATH}/privkey.pem" ]] || die "証明書が見つかりません: ${CERT_PATH}/privkey.pem"

  mkdir -p "${SSL_DIR}"
  sudo cp "${CERT_PATH}/fullchain.pem" "${SSL_DIR}/"
  sudo cp "${CERT_PATH}/privkey.pem" "${SSL_DIR}/"
  sudo chown -R "$(whoami):$(whoami)" "${SSL_DIR}"
  log "SSL 証明書を ${SSL_DIR} にコピーしました"
}

restore_https_nginx() {
  if git -C "${PROJECT_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "${PROJECT_ROOT}" checkout -- nginx/nginx.conf
    log "nginx/nginx.conf を HTTPS 設定に復元しました"
    return
  fi

  die "git リポジトリ外では nginx/nginx.conf を自動復元できません"
}

cmd_check_env() {
  init_runtime_config
  log_env_sources

  [[ -f "${BACKEND_ENV_PATH}" ]] || die "backend 環境変数ファイルがありません"
  [[ -f "${DB_ENV_PATH}" ]] || die "DB 環境変数ファイルがありません"

  local key missing=0
  for key in GOOGLE_API_KEY JWT_SECRET_KEY DATABASE_URL; do
    if [[ -z "$(read_env_value "${BACKEND_ENV_PATH}" "${key}" || true)" ]]; then
      log "  WARN: backend/.env に ${key} が未設定です"
      missing=1
    fi
  done

  for key in POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB; do
    if [[ -z "$(read_env_value "${DB_ENV_PATH}" "${key}" || true)" ]]; then
      log "  WARN: .env.db に ${key} が未設定です"
      missing=1
    fi
  done

  if [[ ! -f "${FRONTEND_ENV_PATH}" ]]; then
    log "  INFO: frontend/.env.local は未作成です（本番 compose では未使用）"
  fi

  if [[ "${missing}" -eq 1 ]]; then
    die "必須の環境変数が不足しています"
  fi

  log "環境変数ファイルは deploy 可能な状態です"
  log "そのまま ./scripts/deploy.sh deploy を実行できます"
}

cmd_setup_env() {
  init_runtime_config

  if [[ ! -f "${BACKEND_ENV_PATH}" ]]; then
    cp "${PROJECT_ROOT}/backend/env.example" "${BACKEND_ENV_PATH}"
    log "${BACKEND_ENV_FILE} を env.example から作成しました（値を編集してください）"
  else
    log "${BACKEND_ENV_FILE} は既に存在するため変更しません"
  fi

  if [[ ! -f "${DB_ENV_PATH}" ]]; then
    cp "${PROJECT_ROOT}/env.db.example" "${DB_ENV_PATH}"
    log "${DB_ENV_FILE} を env.db.example から作成しました（値を編集してください）"
  else
    log "${DB_ENV_FILE} は既に存在するため変更しません"
  fi

  if [[ ! -f "${FRONTEND_ENV_PATH}" ]]; then
    touch "${FRONTEND_ENV_PATH}"
    log "${FRONTEND_ENV_FILE} を作成しました"
  else
    log "${FRONTEND_ENV_FILE} は既に存在するため変更しません"
  fi

  mkdir -p "${SSL_DIR}"

  log "setup-env 完了（既存ファイルは上書きしていません）"
  cmd_check_env
}

cmd_setup_host() {
  log "EC2 ホストの初回セットアップを開始します（Amazon Linux 2023 想定）"

  sudo dnf update -y
  sudo dnf install -y docker git certbot

  if ! systemctl is-active --quiet docker; then
    sudo systemctl start docker
  fi
  sudo systemctl enable docker

  if ! groups "$(whoami)" | grep -q '\bdocker\b'; then
    sudo usermod -aG docker "$(whoami)"
    log "docker グループに追加しました。反映のため再ログインするか 'newgrp docker' を実行してください"
  fi

  if ! docker compose version >/dev/null 2>&1; then
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  fi

  docker --version
  docker compose version
  git --version
  certbot --version

  log "ホストセットアップが完了しました"
}

cmd_migrate() {
  ensure_project_root
  ensure_env_files
  compose exec -T backend python -m app.scripts.migrate upgrade
}

cmd_seed_admin() {
  ensure_project_root
  ensure_env_files
  compose exec -T backend python -m app.scripts.seed_admin
}

cmd_build() {
  ensure_project_root
  ensure_env_files
  compose build
}

cmd_up() {
  ensure_project_root
  ensure_env_files
  compose up -d
}

cmd_down() {
  ensure_project_root
  compose down
}

cmd_restart() {
  ensure_project_root
  ensure_env_files
  if [[ $# -gt 0 ]]; then
    compose restart "$@"
  else
    compose restart
  fi
}

cmd_ps() {
  ensure_project_root
  compose ps
}

cmd_logs() {
  ensure_project_root
  if [[ $# -gt 0 ]]; then
    compose logs -f "$@"
  else
    compose logs -f
  fi
}

cmd_deploy() {
  ensure_project_root
  ensure_env_files

  if [[ "${SKIP_GIT_PULL}" != "1" ]]; then
    require_command git
    log "git pull origin ${GIT_BRANCH}"
    git pull origin "${GIT_BRANCH}"
  else
    log "SKIP_GIT_PULL=1 のため git pull をスキップします"
  fi

  log "Docker イメージをビルドします"
  compose build

  log "コンテナを起動します"
  compose up -d

  log "DB マイグレーションを実行します"
  compose exec -T backend python -m app.scripts.migrate upgrade

  log "未使用 Docker イメージを削除します"
  docker image prune -f

  compose ps
  log "デプロイが完了しました: https://${DOMAIN}"
}

cmd_setup_ssl() {
  ensure_project_root
  ensure_env_files

  [[ -n "${CERTBOT_EMAIL:-}" ]] || die "CERTBOT_EMAIL が未設定です。scripts/deploy.env に CERTBOT_EMAIL を設定するか、backend/.env の INITIAL_ADMIN_EMAIL を設定してください。"

  log "HTTP 用 nginx 設定で起動します"
  cp "${PROJECT_ROOT}/nginx/nginx.initial.conf" "${PROJECT_ROOT}/nginx/nginx.conf"
  mkdir -p "${SSL_DIR}"

  compose build
  compose up -d

  log "nginx を停止して certbot standalone で証明書を取得します"
  compose stop nginx

  sudo certbot certonly \
    --standalone \
    -d "${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    -m "${CERTBOT_EMAIL}"

  copy_ssl_certs
  restore_https_nginx

  log "HTTPS 設定で全サービスを起動します"
  compose up -d
  compose ps

  log "SSL セットアップが完了しました: https://${DOMAIN}"
  log "証明書自動更新: ./scripts/deploy.sh install-ssl-cron"
}

cmd_renew_ssl() {
  ensure_project_root
  ensure_env_files

  require_command certbot
  sudo certbot renew --quiet
  copy_ssl_certs
  compose restart nginx
  log "SSL 証明書を更新し nginx を再起動しました"
}

cmd_install_ssl_cron() {
  ensure_project_root

  local cron_line
  cron_line="0 3 1,15 * * ${PROJECT_ROOT}/scripts/deploy.sh renew-ssl >> ${PROJECT_ROOT}/logs/ssl-renew.log 2>&1"

  mkdir -p "${PROJECT_ROOT}/logs"

  if crontab -l 2>/dev/null | grep -Fq "${PROJECT_ROOT}/scripts/deploy.sh renew-ssl"; then
    log "SSL 更新 cron は既に登録されています"
    return
  fi

  (crontab -l 2>/dev/null; echo "${cron_line}") | crontab -
  log "SSL 更新 cron を登録しました"
  log "${cron_line}"
}

usage() {
  cat <<EOF
Marketing Planner 本番デプロイスクリプト

使い方:
  ./scripts/deploy.sh <command>

アプリの環境変数（deploy スクリプトは上書きしません）:
  backend/.env
  .env.db
  frontend/.env.local

docker compose.prod.yml が上記パスを直接参照します。
EC2 に既存ファイルがある場合は setup-env 不要で deploy できます。

コマンド:
  deploy          通常の再デプロイ（git pull → build → up → migrate）
  check-env       環境変数ファイルの存在・必須キー確認
  setup-env       不足ファイルのみ example から作成（既存は上書きしない）
  setup-host      EC2 初回セットアップ（Docker / Compose / certbot）
  setup-ssl       初回 SSL 証明書取得と HTTPS 有効化
  renew-ssl       SSL 証明書更新と nginx 再起動
  install-ssl-cron  SSL 自動更新 cron を登録
  migrate         DB マイグレーション
  seed-admin      初期管理者ユーザー作成
  build           イメージビルドのみ
  up              コンテナ起動
  down            コンテナ停止
  restart [svc]   コンテナ再起動
  ps              コンテナ状態確認
  logs [svc]      ログ表示
  help            このヘルプ

設定（任意）:
  scripts/deploy.env.example → scripts/deploy.env
  DOMAIN は未指定時 backend/.env の CORS_ORIGINS から自動検出
  CERTBOT_EMAIL は未指定時 backend/.env の INITIAL_ADMIN_EMAIL を使用

例（EC2 に .env がある場合）:
  ./scripts/deploy.sh check-env
  ./scripts/deploy.sh deploy

例（初回セットアップ）:
  cp scripts/deploy.env.example scripts/deploy.env
  ./scripts/deploy.sh setup-env
  ./scripts/deploy.sh setup-ssl
  ./scripts/deploy.sh seed-admin
  ./scripts/deploy.sh deploy
EOF
}

main() {
  local command="${1:-deploy}"
  shift || true

  case "${command}" in
    deploy) cmd_deploy ;;
    check-env) cmd_check_env ;;
    setup-env) cmd_setup_env ;;
    setup-host) cmd_setup_host ;;
    setup-ssl) cmd_setup_ssl ;;
    renew-ssl) cmd_renew_ssl ;;
    install-ssl-cron) cmd_install_ssl_cron ;;
    migrate) cmd_migrate ;;
    seed-admin) cmd_seed_admin ;;
    build) cmd_build ;;
    up) cmd_up ;;
    down) cmd_down ;;
    restart) cmd_restart "$@" ;;
    ps|status) cmd_ps ;;
    logs) cmd_logs "$@" ;;
    help|-h|--help) usage ;;
    *)
      die "不明なコマンド: ${command}（help で一覧を確認）"
      ;;
  esac
}

main "$@"
