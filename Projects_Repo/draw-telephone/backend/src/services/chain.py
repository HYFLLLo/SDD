"""
链业务服务层。

依赖 Repository + User（创建者信息），不依赖 FastAPI/HTTP。
- 创建链：校验 prompt_source=manual 时 prompt_text 必填，生成房间码+第一节点
- 查询链（房间码）：加入前校验，返回 ChainLookup
- 加入链：校验未满/未过期/未重复加入
- 链大厅详情：需成员权限，返回 ChainDetail（含推导的进度节点链）
"""

import datetime

from sqlalchemy import select

from pycore.core import get_logger
from src.core.config import settings
from src.db.models import Chain, Node, User
from src.repositories.chain import ChainRepository

logger = get_logger()

# 节点类型交替规则：seq 偶数为 draw，奇数为 describe（起手为画）
def _node_type(seq: int) -> str:
    return "draw" if seq % 2 == 0 else "describe"


class ChainService:
    """链创建/查询/加入业务。"""

    def __init__(self, repo: ChainRepository) -> None:
        self.repo = repo

    async def create_chain(
        self,
        creator: User,
        title: str | None,
        chain_length: int,
        visibility: str,
        prompt_source: str,
        prompt_text: str | None,
    ) -> Chain:
        """
        创建链 + 创建者成员 + 第一节点。

        Raises:
            ValueError: prompt_source=manual 但 prompt_text 为空，或房间码生成失败。
        """
        # prompt_source=manual 时 prompt_text 必填
        if prompt_source == "manual":
            if not prompt_text or not prompt_text.strip():
                raise ValueError("手动起手题必须填写题词")
            prompt_text = prompt_text.strip()

        # prompt_source=ai 时 prompt_text 可为空（T-015 AI 生成时填充），暂用占位
        if prompt_source == "ai" and not prompt_text:
            prompt_text = ""  # T-015 AI 生成后回填
        # 此时 prompt_text 必为 str（manual 已校验非空，ai 空值已置 ""）
        assert prompt_text is not None

        chain = await self.repo.create_chain_with_first_node(
            creator_id=creator.id,
            title=title,
            chain_length=chain_length,
            visibility=visibility,
            prompt_source=prompt_source,
            prompt_text=prompt_text,
            creator_nickname=creator.nickname,
        )
        logger.info(
            "Chain created",
            chain_id=chain.id,
            room_code=chain.room_code,
            creator_id=creator.id,
            chain_length=chain_length,
        )
        return chain

    async def lookup_chain(self, room_code: str) -> dict:
        """
        按房间码查询链（加入前校验）。

        Raises:
            ValueError: 房间码无效或链已过期（→404）。
        """
        chain = await self.repo.get_by_room_code(room_code)
        if chain is None:
            raise ValueError("房间码无效或链已过期")
        if _is_expired(chain):
            raise ValueError("房间码无效或链已过期")

        member_count = await self.repo.count_members(chain.id)
        is_full = member_count >= chain.chain_length
        return {
            "id": chain.id,
            "title": chain.title,
            "chain_length": chain.chain_length,
            "current_seq": chain.current_seq,
            "status": chain.status,
            "is_full": is_full,
            "remaining_slots": max(0, chain.chain_length - member_count),
            "expires_at": chain.expires_at.isoformat() if chain.expires_at else "",
        }

    async def join_chain(self, chain_id: str, user: User) -> dict:
        """
        加入链。

        Raises:
            LookupError: 链不存在（→404）。
            ValueError: 链已满或已过期，或已是成员（→403）。
        """
        chain = await self.repo.get_by_id(chain_id)
        if chain is None:
            raise LookupError("链不存在")

        if _is_expired(chain) or chain.status == "expired":
            raise ValueError("链已满或已过期")
        if chain.status in ("completed", "closed"):
            raise ValueError("链已满或已过期")

        member_count = await self.repo.count_members(chain.id)
        if member_count >= chain.chain_length:
            raise ValueError("链已满或已过期")

        existing = await self.repo.get_member(chain.id, user.id)
        if existing is not None:
            raise ValueError("你已是该链成员")

        await self.repo.add_member(chain.id, user.id)
        logger.info(
            "User joined chain",
            chain_id=chain.id,
            user_id=user.id,
            member_count=member_count + 1,
        )
        return {"chain_id": chain.id, "joined": True}

    async def get_chain_detail(self, chain_id: str, user: User) -> dict:
        """
        链大厅详情（需成员权限）。

        Raises:
            LookupError: 链不存在（→404）。
            PermissionError: 非链成员（→403）。
        """
        chain = await self.repo.get_by_id(chain_id)
        if chain is None:
            raise LookupError("链不存在")

        member = await self.repo.get_member(chain.id, user.id)
        if member is None:
            raise PermissionError("无权访问该链")

        members = await self.repo.get_members(chain.id)
        # 查成员用户信息（nickname/avatar_url）
        member_users = await self._get_member_users([m.user_id for m in members])

        nodes = await self.repo.get_nodes(chain.id)
        current_node = await self.repo.get_current_node(chain.id, chain.current_seq)

        # 推导进度节点链：已建节点 + 未建节点占位
        node_list = _build_node_list(chain, nodes)

        # 当前责任人：current_seq 节点的 author（创建后 current_seq=0 author=创建者）
        current_author = _get_current_author(chain, current_node, member_users)

        # AI 补位倒计时：当前 pending 节点 created_at + 24h（前端算与 now 的差显示）
        ai_countdown_at = _get_ai_countdown_at(chain, current_node)

        return {
            "id": chain.id,
            "title": chain.title,
            "chain_length": chain.chain_length,
            "visibility": chain.visibility,
            "room_code": chain.room_code,
            "prompt_source": chain.prompt_source,
            "prompt_text": chain.prompt_text,
            "status": chain.status,
            "current_seq": chain.current_seq,
            "current_node_type": _node_type(chain.current_seq),
            "current_author": current_author,
            "ai_countdown_at": ai_countdown_at,
            "members": member_users,
            "nodes": node_list,
            "created_at": chain.created_at.isoformat() if chain.created_at else "",
            "expires_at": chain.expires_at.isoformat() if chain.expires_at else "",
        }

    async def _get_member_users(self, user_ids: list[str]) -> list[dict]:
        """查询成员用户信息（id/nickname/avatar_url）。"""
        if not user_ids:
            return []
        result = await self.repo.db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = list(result.scalars().all())
        # 按传入顺序保持稳定
        user_map = {u.id: u for u in users}
        return [
            {
                "id": u.id,
                "nickname": u.nickname,
                "avatar_url": u.avatar_url,
            }
            for uid in user_ids
            if (u := user_map.get(uid)) is not None
        ]


def _is_expired(chain: Chain) -> bool:
    """链是否已过期（expires_at 早于现在 或 status=expired）。

    SQLite 读回的 datetime 可能为 offset-naive，比较前统一转 aware（UTC）。
    """
    if chain.status == "expired":
        return True
    if chain.expires_at is None:
        return False
    expires = chain.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=datetime.UTC)
    return expires < datetime.datetime.now(datetime.UTC)


def _build_node_list(chain: Chain, existing_nodes: list[Node]) -> list[dict]:
    """构建进度节点链：已建节点从 DB 取，未建节点按 seq 推导占位。

    返回 chain_length 个节点，每个含 seq/type/author/is_ai/submitted_at。
    已建节点带真实 author，未建节点 author 为 null（待接）。
    """
    node_map = {n.seq: n for n in existing_nodes}
    result: list[dict] = []
    for seq in range(chain.chain_length):
        node = node_map.get(seq)
        if node is not None:
            result.append(
                {
                    "seq": node.seq,
                    "type": node.type,
                    "author": {
                        "id": node.author_id or "",
                        "nickname": node.author_label,
                    },
                    "is_ai": node.is_ai,
                    "submitted_at": node.submitted_at.isoformat()
                    if node.submitted_at
                    else "",
                }
            )
        else:
            # 未建节点占位：type 按 seq 推导，author 待接
            result.append(
                {
                    "seq": seq,
                    "type": _node_type(seq),
                    "author": {"id": "", "nickname": "待接"},
                    "is_ai": False,
                    "submitted_at": "",
                }
            )
    return result


def _get_current_author(
    chain: Chain, current_node: Node | None, member_users: list[dict]
) -> dict:
    """获取当前责任人。current_node 存在时用其 author，否则用创建者兜底。"""
    if current_node is not None and current_node.author_id:
        # 从成员列表找 author
        for m in member_users:
            if m["id"] == current_node.author_id:
                return m
        # author 可能不在成员列表（理论上不会），用 author_label 兜底
        return {
            "id": current_node.author_id,
            "nickname": current_node.author_label,
        }
    # current_node 未创建（不应发生于创建后 current_seq=0 已建），用创建者兜底
    if member_users:
        return member_users[0]
    return {"id": "", "nickname": "未知"}


def _get_ai_countdown_at(chain: Chain, current_node: Node | None) -> str | None:
    """当前 pending 节点的 AI 补位时间点 = created_at + ai_fill_timeout_hours。

    链 in_progress 且当前节点 pending 时返回倒计时目标时间（ISO 字符串），
    前端算与 now 的差显示倒计时。其他情况返回 None（不显示倒计时）。
    """
    if chain.status != "in_progress":
        return None
    if current_node is None or current_node.status != "pending":
        return None
    if current_node.created_at is None:
        return None
    created = current_node.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=datetime.UTC)
    countdown_at = created + datetime.timedelta(
        hours=settings.ai_fill_timeout_hours
    )
    return countdown_at.isoformat()
