"""T-012 数据库骨架 + 依赖注入 + 健康检查 测试。

使用独立测试库（内存 SQLite + 事务回滚夹具），不污染运行时业务库。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect
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
async def test_health_check() -> None:
    """GET /health 返回 200 且响应格式正确。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    assert body["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_tables_created(test_db: AsyncSession) -> None:
    """所有业务表已创建。"""
    async with test_engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    expected = {"users", "chains", "chain_members", "nodes", "votes", "notifications"}
    assert expected.issubset(set(table_names)), f"缺失表: {expected - set(table_names)}"


@pytest.mark.asyncio
async def test_get_current_user_no_token(test_db: AsyncSession) -> None:
    """无凭证访问 → 401。"""
    from src.api.deps import get_current_user

    with pytest.raises(Exception) as exc_info:
        await get_current_user(credentials=None, db=test_db)
    assert exc_info.value.status_code == 401  # type: ignore[attr-defined]
