"""
数据库 ORM 模型。

基于 pycore/integrations/db/models.py 模板扩展，按 PRD 6.1 数据契约定义业务模型：
User / Chain / ChainMember / Node / Vote / Notification。

字段与 PRD「6.1 业务数据契约」对齐。
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    """生成 UUID 字符串（默认值用，避免 DB 端 uuid 生成依赖）。"""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""

    pass


class User(Base):
    """用户模型（PRD 6.1 用户体系）。"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="user")  # user / admin
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Chain(Base):
    """链模型（PRD 6.1 链体系）。"""

    __tablename__ = "chains"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chain_length: Mapped[int] = mapped_column(Integer, nullable=False)  # 4-10
    prompt_source: Mapped[str] = mapped_column(String(16), nullable=False)  # manual / ai
    prompt_text: Mapped[str] = mapped_column(String(20), nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False)  # invite / public
    room_code: Mapped[str] = mapped_column(String(6), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="in_progress"
    )  # in_progress / completed / closed / expired
    creator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    current_seq: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChainMember(Base):
    """链成员（用于投票权限校验 BR-08）。"""

    __tablename__ = "chain_members"
    __table_args__ = (UniqueConstraint("chain_id", "user_id", name="uq_chain_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chains.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Node(Base):
    """节点模型（PRD 6.1 节点体系）。"""

    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chains.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # 从 0
    type: Mapped[str] = mapped_column(String(8), nullable=False)  # draw / describe
    author_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )  # AI 补位时为 null
    content_type: Mapped[str | None] = mapped_column(
        String(8), nullable=True
    )  # image / text
    content_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_text: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    author_label: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending / in_progress / submitted / ai_filled / timeout
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Vote(Base):
    """投票模型（PRD 6.1 投票体系）。"""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "chain_id", "user_id", "dimension", name="uq_vote_chain_user_dim"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chains.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(16), nullable=False)
    # most_drift / best_draw / best_describe
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nodes.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Notification(Base):
    """通知模型（PRD 6.1 通知体系）。"""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # your_turn / chain_done / node_submitted
    chain_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("chains.id"), nullable=True
    )
    chain_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
