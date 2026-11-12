"""T-018 图片上传功能闭环 测试。

测试 POST /api/upload/image（PNG 校验 + 本地存储 + 返回 url），使用独立测试库。
上传目录用 monkeypatch 指向临时目录，避免污染真实 uploads/。
"""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

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


@pytest.fixture()
def temp_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """临时上传目录，避免污染真实 backend/uploads/。

    monkeypatch settings.upload_dir 指向 tmp_path/uploads，
    settings.upload_path 属性会基于此解析并创建目录。
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    from src.core.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    return upload_dir


async def _create_test_user(db: AsyncSession, username: str = "uploaduser") -> User:
    """在测试库中创建用户并返回。"""
    user = User(
        username=username,
        password_hash=hash_password("pass1234"),
        nickname="上传者",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# PNG 文件头魔数 + 最小 PNG 数据
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MINIMAL_PNG = PNG_MAGIC + b"\x00\x00\x00\x0cIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"


@pytest.mark.asyncio
async def test_upload_png_success(
    override_db: None, temp_upload_dir: Path, test_db: AsyncSession
) -> None:
    """上传 PNG → 200 + {url, size}，文件存到上传目录。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/upload/image",
            files={"file": ("drawing.png", MINIMAL_PNG, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["url"].startswith("/uploads/")
    assert data["url"].endswith(".png")
    assert data["size"] == len(MINIMAL_PNG)

    # 验证文件存到上传目录
    stored_name = data["url"].split("/")[-1]
    stored_path = temp_upload_dir / stored_name
    assert stored_path.exists()
    assert stored_path.read_bytes() == MINIMAL_PNG


@pytest.mark.asyncio
async def test_upload_non_png_400(
    override_db: None, temp_upload_dir: Path, test_db: AsyncSession
) -> None:
    """上传非 PNG → 400「文件格式不支持」。"""
    user = await _create_test_user(test_db, "user2")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # JPEG 文件头 + content_type
        jpeg_data = b"\xff\xd8\xff\xe0JFIF\x00\x01"
        resp = await client.post(
            "/api/upload/image",
            files={"file": ("photo.jpg", jpeg_data, "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == 400
    assert "文件格式不支持" in resp.json()["message"]


@pytest.mark.asyncio
async def test_upload_png_by_magic_only(
    override_db: None, temp_upload_dir: Path, test_db: AsyncSession
) -> None:
    """content_type 非 image/png 但文件头是 PNG 魔数 → 200（魔数校验通过）。"""
    user = await _create_test_user(test_db, "user3")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # content_type 为空/错误，但文件头是 PNG 魔数
        resp = await client.post(
            "/api/upload/image",
            files={"file": ("drawing.png", MINIMAL_PNG, "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["url"].endswith(".png")


@pytest.mark.asyncio
async def test_upload_no_token_401(override_db: None, temp_upload_dir: Path) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/upload/image",
            files={"file": ("drawing.png", MINIMAL_PNG, "image/png")},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_empty_file_400(
    override_db: None, temp_upload_dir: Path, test_db: AsyncSession
) -> None:
    """空文件 → 400（非 PNG，魔数校验失败）。"""
    user = await _create_test_user(test_db, "user4")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/upload/image",
            files={"file": ("empty.png", b"", "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "文件格式不支持" in resp.json()["message"]


@pytest.mark.asyncio
async def test_upload_url_format(
    override_db: None, temp_upload_dir: Path, test_db: AsyncSession
) -> None:
    """上传返回的 url 格式为 /uploads/{uuid}.png。"""
    user = await _create_test_user(test_db, "user5")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/upload/image",
            files={"file": ("中文文件名.png", MINIMAL_PNG, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    url = resp.json()["data"]["url"]
    # UUID 文件名（32 hex + .png），不含原始中文文件名
    stored_name = url.split("/")[-1]
    assert stored_name.endswith(".png")
    assert len(stored_name) == 36  # 32 hex + 4 (.png)
