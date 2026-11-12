"""T-013 用户认证功能闭环 测试。

测试注册/登录/JWT 全链路，使用独立测试库（内存 SQLite + dependency_overrides）。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.db.models import Base
from src.db.session import get_db
from src.main import app

# 独立测试库（内存 SQLite，与运行时业务库物理隔离）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """每测试函数建表 + 销毁，不污染运行时库。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
def override_db(test_db: AsyncSession) -> Generator[None, None, None]:
    """通过 dependency_overrides 注入测试库 session。"""

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_success(override_db: None) -> None:
    """注册成功 → 200，返回 access_token + user。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "pass1234", "nickname": "新用户"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    data = body["data"]
    assert "access_token" in data
    assert data["user"]["username"] == "newuser"
    assert data["user"]["nickname"] == "新用户"
    assert data["user"]["avatar_url"] is None


@pytest.mark.asyncio
async def test_register_duplicate(override_db: None) -> None:
    """重复用户名注册 → 400 用户名已存在。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 第一次注册成功
        await client.post(
            "/api/auth/register",
            json={"username": "dupuser", "password": "pass1234", "nickname": "重复"},
        )
        # 第二次同用户名 → 400
        resp = await client.post(
            "/api/auth/register",
            json={"username": "dupuser", "password": "otherpass", "nickname": "另一个"},
        )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "用户名已存在"
    assert body["data"] is None


@pytest.mark.asyncio
async def test_login_success(override_db: None) -> None:
    """登录成功 → 200，返回 access_token + user。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 先注册
        await client.post(
            "/api/auth/register",
            json={"username": "loginuser", "password": "pass1234", "nickname": "登录用户"},
        )
        # 登录
        resp = await client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "pass1234"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "access_token" in data
    assert data["user"]["username"] == "loginuser"


@pytest.mark.asyncio
async def test_login_wrong_password(override_db: None) -> None:
    """密码错误 → 401 用户名或密码错误。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 先注册
        await client.post(
            "/api/auth/register",
            json={"username": "wrongpw", "password": "correct123", "nickname": "错密码"},
        )
        # 用错误密码登录 → 401
        resp = await client.post(
            "/api/auth/login",
            json={"username": "wrongpw", "password": "wrongpassword"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 401
    assert body["message"] == "用户名或密码错误"
    assert body["data"] is None


@pytest.mark.asyncio
async def test_login_nonexistent_user(override_db: None) -> None:
    """用户不存在 → 401（与密码错误同消息，避免枚举）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            json={"username": "ghostuser", "password": "whatever"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 401
    assert body["message"] == "用户名或密码错误"


@pytest.mark.asyncio
async def test_token_persists_across_requests(override_db: None) -> None:
    """注册获得的 token 可用于后续受保护请求（JWT 真实签发与校验）。"""
    from src.api.deps import get_current_user
    from src.db.models import User

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 注册拿 token
        resp = await client.post(
            "/api/auth/register",
            json={"username": "tokenuser", "password": "pass1234", "nickname": "Token用户"},
        )
        token = resp.json()["data"]["access_token"]

    # 直接用 get_current_user 依赖验证 token 解析出真实用户
    async with TestSessionLocal() as session:
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user: User = await get_current_user(credentials=creds, db=session)
        assert user.username == "tokenuser"
        assert user.nickname == "Token用户"
