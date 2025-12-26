"""初期システムアドミン作成スクリプト

使用方法:
    python -m app.scripts.seed_admin

環境変数で初期アドミンを設定:
    INITIAL_ADMIN_EMAIL: 初期アドミンのメールアドレス
    INITIAL_ADMIN_PASSWORD: 初期アドミンのパスワード

または対話式で入力することも可能です。
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from app.core.database import engine, create_db_and_tables
from app.core.config import settings
from app.models import SystemAdmin
from app.auth.password import hash_password, validate_password_strength


def create_initial_admin():
    """初期システムアドミンを作成"""
    
    # テーブル作成
    create_db_and_tables()
    
    with Session(engine) as session:
        # 既存のアドミンを確認
        existing_admin = session.exec(select(SystemAdmin)).first()
        
        if existing_admin:
            print("⚠️  システムアドミンは既に存在します。")
            print(f"   既存アドミン: {existing_admin.email}")
            return
        
        # 環境変数から取得を試みる
        email = settings.INITIAL_ADMIN_EMAIL
        password = settings.INITIAL_ADMIN_PASSWORD
        
        # 環境変数がない場合は対話式で入力
        if not email:
            email = input("システムアドミンのメールアドレスを入力してください: ").strip()
        
        if not password:
            import getpass
            password = getpass.getpass("システムアドミンのパスワードを入力してください: ")
        
        # メールアドレスの簡易バリデーション
        if not email or "@" not in email:
            print("❌ 無効なメールアドレスです。")
            return
        
        # パスワード強度チェック
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            print("❌ パスワードが要件を満たしていません:")
            for error in errors:
                print(f"   - {error}")
            return
        
        # アドミン作成
        admin = SystemAdmin(
            email=email,
            password_hash=hash_password(password),
            name="System Administrator",
            is_active=True,
        )
        
        session.add(admin)
        session.commit()
        session.refresh(admin)
        
        print("✅ システムアドミンを作成しました。")
        print(f"   メールアドレス: {admin.email}")
        print(f"   ID: {admin.id}")


if __name__ == "__main__":
    create_initial_admin()


