#!/usr/bin/env python3
"""
データベースマイグレーション実行スクリプト

使用方法:
    # マイグレーション実行
    python -m app.scripts.migrate upgrade
    
    # 1つ前に戻す
    python -m app.scripts.migrate downgrade
    
    # 現在の状態を確認
    python -m app.scripts.migrate current
    
    # 履歴を表示
    python -m app.scripts.migrate history
    
    # 新しいマイグレーションを自動生成
    python -m app.scripts.migrate generate "add_column_name"
    
    # 特定のリビジョンにマイグレーション
    python -m app.scripts.migrate upgrade <revision>
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from alembic.config import Config
from alembic import command

def get_alembic_config():
    """Alembic設定を取得"""
    # alembic.iniのパスを取得
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_ini = os.path.join(base_path, "alembic.ini")
    
    config = Config(alembic_ini)
    config.set_main_option("script_location", os.path.join(base_path, "migrations"))
    
    return config


def upgrade(revision: str = "head"):
    """マイグレーションを実行"""
    config = get_alembic_config()
    command.upgrade(config, revision)
    print(f"✅ マイグレーション完了: {revision}")


def downgrade(revision: str = "-1"):
    """マイグレーションをロールバック"""
    config = get_alembic_config()
    command.downgrade(config, revision)
    print(f"✅ ロールバック完了: {revision}")


def current():
    """現在のリビジョンを表示"""
    config = get_alembic_config()
    command.current(config)


def history():
    """マイグレーション履歴を表示"""
    config = get_alembic_config()
    command.history(config)


def generate(message: str):
    """モデルの変更から自動的にマイグレーションを生成"""
    config = get_alembic_config()
    command.revision(config, message=message, autogenerate=True)
    print(f"✅ マイグレーションファイルを生成しました: {message}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade(revision)
    elif cmd == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        downgrade(revision)
    elif cmd == "current":
        current()
    elif cmd == "history":
        history()
    elif cmd == "generate":
        if len(sys.argv) < 3:
            print("エラー: マイグレーション名を指定してください")
            print("例: python -m app.scripts.migrate generate 'add_ota_text_column'")
            sys.exit(1)
        generate(sys.argv[2])
    else:
        print(f"不明なコマンド: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

