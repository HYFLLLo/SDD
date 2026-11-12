"""T-015 AI 起手题生成功能闭环 测试。

真实 DeepSeek 未验收（用户暂未提供 Key）。测试覆盖：
- Key 缺失 → 503 降级
- 无 token → 401
- count 校验
- DeepSeek 调用路径（mock httpx，不依赖真实 Key）
- DeepSeek 调用失败 → fallback 降级
"""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import create_access_token, hash_password
from src.db.models import Base, User
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


async def _create_test_user(
    db: AsyncSession, username: str = "aiuser", nickname: str = "AI用户"
) -> User:
    """在测试库中创建用户并返回。"""
    user = User(
        username=username,
        password_hash=hash_password("pass1234"),
        nickname=nickname,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_ai_prompt_no_token(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ai/prompt", json={"count": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_prompt_key_missing_returns_503(
    override_db: None, test_db: AsyncSession
) -> None:
    """Key 缺失 → 503 + 降级提示（不静默吞错）。

    mock settings.deepseek_api_key 为空，独立验证 Key 缺失分支，
    不依赖 .env 真实配置（.env 可能已填真实 Key）。
    """
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("src.services.ai.settings") as mock_settings:
            mock_settings.deepseek_api_key = ""
            resp = await client.post(
                "/api/ai/prompt",
                json={"count": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == 503
    assert "不可用" in body["message"]
    assert body["data"] is None


@pytest.mark.asyncio
async def test_ai_prompt_count_validation(override_db: None, test_db: AsyncSession) -> None:
    """count 超范围（0 或 6）→ 400（Pydantic 校验经全局 handler）。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # count=0（<1）
        resp = await client.post(
            "/api/ai/prompt",
            json={"count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == 400


@pytest.mark.asyncio
async def test_ai_prompt_deepseek_success(
    override_db: None, test_db: AsyncSession
) -> None:
    """DeepSeek 调用成功路径（mock，不依赖真实 Key）。

    patch settings.deepseek_api_key 模拟 Key 存在，mock _call_deepseek 返回真实题词。
    AiService.__init__ 读 settings.deepseek_api_key，故 patch settings 属性即可。
    """
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from src.services.ai import AiService

        with (
            patch("src.services.ai.settings") as mock_settings,
            patch.object(
                AiService,
                "_call_deepseek",
                new_callable=AsyncMock,
                return_value=["戴帽子的猫", "会飞的鱼"],
            ),
        ):
            mock_settings.deepseek_api_key = "fake-key-for-test"
            resp = await client.post(
                "/api/ai/prompt",
                json={"count": 2},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["prompts"] == ["戴帽子的猫", "会飞的鱼"]


@pytest.mark.asyncio
async def test_ai_prompt_deepseek_failure_degrades(
    override_db: None, test_db: AsyncSession
) -> None:
    """DeepSeek 调用失败 → 降级到 fallback 题词池（不 503，返回 200 + 本地题词）。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        import httpx as httpx_mod
        from src.services.ai import AiService

        with (
            patch("src.services.ai.settings") as mock_settings,
            patch.object(
                AiService,
                "_call_deepseek",
                new_callable=AsyncMock,
                side_effect=httpx_mod.HTTPError("connection refused"),
            ),
        ):
            mock_settings.deepseek_api_key = "fake-key-for-test"
            resp = await client.post(
                "/api/ai/prompt",
                json={"count": 2},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    prompts = body["data"]["prompts"]
    assert len(prompts) == 2
    # 降级题词来自 FALLBACK_PROMPTS
    from src.services.ai import FALLBACK_PROMPTS

    assert all(p in FALLBACK_PROMPTS for p in prompts)


@pytest.mark.asyncio
async def test_ai_prompt_trust_env_false(override_db: None) -> None:
    """httpx.AsyncClient 必须显式 trust_env=False（不继承环境变量）。"""
    import inspect

    from src.services.ai import AiService

    source = inspect.getsource(AiService._call_deepseek)
    assert "trust_env=False" in source, "DeepSeek 调用必须显式 trust_env=False"
