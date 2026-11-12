"""
数据库初始化脚本。

创建 SQLite 数据库文件、建表、写入 seed 数据。
从 backend/ 目录执行：cd backend && PYTHONPATH=.. python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# 确保 backend/ 在 sys.path（作为包根，src.* 可导入）
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.core.config import settings  # noqa: E402
from src.db.models import Base, Chain, ChainMember, Node, Notification, User  # noqa: E402
from src.db.session import async_session_maker, engine  # noqa: E402

# seed 用户密码（明文，仅 seed 用；真实注册走 bcrypt 哈希）
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


SEED_USERS = [
    {
        "id": "mock-uuid",
        "username": "mockuser",
        "nickname": "小A",
        "password": "mockpass",
        "role": "user",
    },
    {
        "id": "mock-uuid-b",
        "username": "userB",
        "nickname": "小B",
        "password": "pass1234",
        "role": "user",
    },
    {
        "id": "mock-uuid-c",
        "username": "userC",
        "nickname": "小C",
        "password": "pass1234",
        "role": "user",
    },
]

SEED_CHAIN = {
    "id": "chain-0001",
    "title": "戴帽子的猫",
    "chain_length": 6,
    "prompt_source": "ai",
    "prompt_text": "戴帽子的猫",
    "visibility": "public",
    "room_code": "ABC123",
    "status": "completed",
    "creator_id": "mock-uuid",
    "current_seq": 6,
}

SEED_NODES = [
    {
        "id": "node-0001",
        "seq": 0,
        "type": "draw",
        "author_id": "mock-uuid",
        "content_type": "image",
        "content_url": "/mock-thumbs/cat.svg",
        "content_text": None,
        "is_ai": False,
        "author_label": "小A",
        "status": "submitted",
    },
    {
        "id": "node-0002",
        "seq": 1,
        "type": "describe",
        "author_id": "mock-uuid-b",
        "content_type": "text",
        "content_url": None,
        "content_text": "一只戴礼帽的猫",
        "is_ai": False,
        "author_label": "小B",
        "status": "submitted",
    },
    {
        "id": "node-0003",
        "seq": 2,
        "type": "draw",
        "author_id": "mock-uuid-c",
        "content_type": "image",
        "content_url": "/mock-thumbs/cat-hat.svg",
        "content_text": None,
        "is_ai": False,
        "author_label": "小C",
        "status": "submitted",
    },
    {
        "id": "node-0004",
        "seq": 3,
        "type": "describe",
        "author_id": "mock-uuid",
        "content_type": "text",
        "content_url": None,
        "content_text": "猫的礼帽里飞出一只鸽子",
        "is_ai": False,
        "author_label": "小A",
        "status": "submitted",
    },
    {
        "id": "node-0005",
        "seq": 4,
        "type": "draw",
        "author_id": None,
        "content_type": "image",
        "content_url": "/mock-thumbs/dove.svg",
        "content_text": None,
        "is_ai": True,
        "author_label": "AI 续",
        "status": "ai_filled",
    },
    {
        "id": "node-0006",
        "seq": 5,
        "type": "describe",
        "author_id": "mock-uuid",
        "content_type": "text",
        "content_url": None,
        "content_text": "鸽子衔着月亮飞向云端",
        "is_ai": False,
        "author_label": "小A",
        "status": "submitted",
    },
]

SEED_NOTIFICATIONS = [
    {
        "id": "notif-0001",
        "user_id": "mock-uuid",
        "type": "your_turn",
        "chain_id": "chain-0001",
        "chain_title": "戴帽子的猫",
        "read": False,
    },
    {
        "id": "notif-0002",
        "user_id": "mock-uuid",
        "type": "node_submitted",
        "chain_id": "chain-0001",
        "chain_title": "戴帽子的猫",
        "read": False,
    },
    {
        "id": "notif-0003",
        "user_id": "mock-uuid",
        "type": "chain_done",
        "chain_id": "chain-0001",
        "chain_title": "戴帽子的猫",
        "read": True,
    },
]


async def init_db() -> None:
    """建表 + seed。"""
    # 建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"[init_db] 表已创建，数据库: {settings.database_url}")

    # seed 数据
    async with async_session_maker() as session:
        # 用户
        for u in SEED_USERS:
            user = User(
                id=u["id"],
                username=u["username"],
                password_hash=hash_password(u["password"]),
                nickname=u["nickname"],
                role=u["role"],
            )
            session.add(user)
        # 链
        import datetime

        chain = Chain(
            id=SEED_CHAIN["id"],
            title=SEED_CHAIN["title"],
            chain_length=SEED_CHAIN["chain_length"],
            prompt_source=SEED_CHAIN["prompt_source"],
            prompt_text=SEED_CHAIN["prompt_text"],
            visibility=SEED_CHAIN["visibility"],
            room_code=SEED_CHAIN["room_code"],
            status=SEED_CHAIN["status"],
            creator_id=SEED_CHAIN["creator_id"],
            current_seq=SEED_CHAIN["current_seq"],
            expires_at=datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=7),
            completed_at=datetime.datetime.now(datetime.timezone.utc),
        )
        session.add(chain)
        # 链成员
        for uid in ["mock-uuid", "mock-uuid-b", "mock-uuid-c"]:
            session.add(ChainMember(chain_id=SEED_CHAIN["id"], user_id=uid))
        # 节点
        for n in SEED_NODES:
            node = Node(
                id=n["id"],
                chain_id=SEED_CHAIN["id"],
                seq=n["seq"],
                type=n["type"],
                author_id=n["author_id"],
                content_type=n["content_type"],
                content_url=n["content_url"],
                content_text=n["content_text"],
                is_ai=n["is_ai"],
                author_label=n["author_label"],
                status=n["status"],
            )
            session.add(node)
        # 通知
        for nt in SEED_NOTIFICATIONS:
            session.add(
                Notification(
                    id=nt["id"],
                    user_id=nt["user_id"],
                    type=nt["type"],
                    chain_id=nt["chain_id"],
                    chain_title=nt["chain_title"],
                    read=nt["read"],
                )
            )
        await session.commit()
    print(f"[init_db] seed 数据已写入: {len(SEED_USERS)} 用户, 1 链, {len(SEED_NODES)} 节点, {len(SEED_NOTIFICATIONS)} 通知")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
