"""
数据库会话管理。

基于 pycore/integrations/db/session.py 模板扩展，使用项目 src.core.config 的配置。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.db.models import Base

# 从项目配置读取数据库 URL（已解析为绝对路径）
DATABASE_URL = settings.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于 FastAPI Depends）。

    成功时提交，异常时回滚。路由层只需 add/flush，commit 由本依赖统一处理。
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库（创建表）。在 main.py lifespan 中调用。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接。在 main.py lifespan 中调用。"""
    await engine.dispose()
