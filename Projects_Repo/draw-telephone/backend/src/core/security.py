"""
认证安全原语。

密码哈希使用 bcrypt（禁止 passlib）；JWT 签发/解码为纯函数，不引入 HTTP 语义。
HTTP 层（401 等）由 src/api/deps.py 负责，保持本模块可被 Service 层无反向依赖调用。
"""

import datetime

import bcrypt
import jwt

from src.core.config import settings


def hash_password(plain: str) -> str:
    """bcrypt 哈希密码。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, username: str) -> str:
    """签发 JWT（exp 由 settings.jwt_expire_hours 控制）。"""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    """解码并验证 JWT。无效/过期返回 None（不抛 HTTP 异常）。"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
