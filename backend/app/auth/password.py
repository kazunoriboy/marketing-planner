"""パスワードハッシュ・検証モジュール"""
import re
import bcrypt


def hash_password(password: str) -> str:
    """
    パスワードをハッシュ化
    
    Args:
        password: 平文パスワード
    
    Returns:
        ハッシュ化されたパスワード
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワードを検証
    
    Args:
        plain_password: 平文パスワード
        hashed_password: ハッシュ化されたパスワード
    
    Returns:
        検証結果（True: 一致、False: 不一致）
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    パスワード強度を検証
    
    ポリシー:
    - 最低8文字以上
    - 英大文字を含む
    - 英小文字を含む
    - 数字を含む
    
    Args:
        password: 検証するパスワード
    
    Returns:
        (検証結果, エラーメッセージリスト)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("パスワードは8文字以上である必要があります")
    
    if not re.search(r"[A-Z]", password):
        errors.append("パスワードには英大文字を含める必要があります")
    
    if not re.search(r"[a-z]", password):
        errors.append("パスワードには英小文字を含める必要があります")
    
    if not re.search(r"\d", password):
        errors.append("パスワードには数字を含める必要があります")
    
    return (len(errors) == 0, errors)
