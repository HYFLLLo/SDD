"""AI 补位业务服务层。

定时扫描 in_progress 链的 pending 节点，created_at + 24h 未提交则 AI 补位：
- draw 节点：Qwen-Image 文生图（输入=上一节点 content_text 或 chain.prompt_text）
- describe 节点：Qwen3.6 VLM 看图生成文字（输入=上一节点 content_url）

补位后与人工 submit 同语义：更新节点 is_ai=true+status=ai_filled，推进链，
创建下一节点（轮转下一位责任人），notify 下一位 + 成员。
7 天未完成的链标记 expired + 通知成员。

补位失败（MaaS 调用失败）记日志跳过，下次扫描重试，不中断整个扫描。
"""

import datetime

from pycore.core import get_logger
from src.core.config import settings
from src.db.models import Chain, Node
from src.repositories.chain import ChainRepository
from src.repositories.node import NodeRepository
from src.repositories.notification import NotificationRepository
from src.services.ai import AiService

logger = get_logger()


class AiFillService:
    """AI 补位业务：扫描超时节点 → 生成内容 → 写节点 → 推进链 → 通知。"""

    def __init__(self, db) -> None:  # type: ignore[no-untyped-def]  # db: AsyncSession
        self.db = db
        self.node_repo = NodeRepository(db)
        self.chain_repo = ChainRepository(db)
        self.notif_repo = NotificationRepository(db)
        self.ai_service = AiService()

    async def scan_and_fill(self) -> dict:
        """扫描所有 in_progress 链，AI 补位超时节点 + 过期 7 天链。

        返回 {filled: N, expired: N, errors: N}。
        """
        now = datetime.datetime.now(datetime.UTC)
        timeout = datetime.timedelta(hours=settings.ai_fill_timeout_hours)
        expire = datetime.timedelta(days=settings.chain_expire_days)

        chains = await self.chain_repo.list_in_progress()
        filled = 0
        expired = 0
        errors = 0

        for chain in chains:
            # 7 天过期检查（优先于补位）
            if self._is_chain_expired(chain, now, expire):
                await self._expire_chain(chain)
                expired += 1
                continue

            # 当前节点超时补位
            current_node = await self.node_repo.get_current_node(chain)
            if current_node is None:
                continue
            if current_node.status != "pending":
                continue
            if not self._is_node_timeout(current_node, now, timeout):
                continue

            try:
                await self._fill_node(chain, current_node)
                filled += 1
            except RuntimeError as e:
                # MaaS 调用失败，记日志跳过，下次扫描重试
                logger.warning(
                    "AI fill failed, skipping",
                    chain_id=chain.id,
                    node_id=current_node.id,
                    error_msg=str(e),
                )
                errors += 1

        logger.info(
            "AI fill scan complete",
            chains=len(chains),
            filled=filled,
            expired=expired,
            errors=errors,
        )
        return {"filled": filled, "expired": expired, "errors": errors}

    async def _fill_node(self, chain: Chain, node: Node) -> None:
        """AI 补位单个节点：生成内容 → 更新节点 → 推进链 → 建下一节点 → 通知。"""
        prev_node = await self.node_repo.get_previous_node(chain)

        if node.type == "draw":
            # draw 节点：输入=上一节点 content_text（描述→画图）；seq=0 用起手题
            prompt = chain.prompt_text
            if prev_node is not None and prev_node.content_text:
                prompt = prev_node.content_text
            content_url = await self.ai_service.generate_image(prompt)
            await self.node_repo.update_node_ai_fill(
                node, content_type="image", content_url=content_url, content_text=None
            )
        else:
            # describe 节点：输入=上一节点 content_url（画→描述）
            image_url = ""
            if prev_node is not None and prev_node.content_url:
                image_url = prev_node.content_url
            content_text = await self.ai_service.describe_image(image_url)
            await self.node_repo.update_node_ai_fill(
                node, content_type="text", content_url=None, content_text=content_text
            )

        logger.info(
            "AI filled node",
            chain_id=chain.id,
            node_id=node.id,
            seq=node.seq,
            type=node.type,
        )

        # 推进链 + 创建下一节点（与人工 submit 同语义）
        chain, is_completed = await self.node_repo.advance_chain(chain)
        next_author_id: str | None = None
        next_author_label = "待接"
        if not is_completed:
            members = await self.chain_repo.get_members(chain.id)
            members.sort(key=lambda m: m.joined_at)
            if members:
                idx = chain.current_seq % len(members)
                next_member = members[idx]
                next_user = await self.node_repo.get_user(next_member.user_id)
                if next_user is not None:
                    next_author_id = next_user.id
                    next_author_label = next_user.nickname
            await self.node_repo.create_next_node(
                chain, author_id=next_author_id, author_label=next_author_label
            )

        # 通知（与 nodes.py submit 路由同语义）
        await self._notify_chain_event(chain, is_completed, next_author_id)

    async def _notify_chain_event(
        self, chain: Chain, is_completed: bool, next_author_id: str | None
    ) -> None:
        """补位后通知：链完成→成员 chain_done；否则→下一位 your_turn + 成员 node_submitted。"""
        members = await self.chain_repo.get_members(chain.id)
        member_user_ids = [m.user_id for m in members]
        chain_title = chain.title or ""

        if is_completed:
            if member_user_ids:
                await self.notif_repo.create_many(
                    [
                        {
                            "user_id": uid,
                            "type": "chain_done",
                            "chain_id": chain.id,
                            "chain_title": chain_title,
                        }
                        for uid in member_user_ids
                    ]
                )
        else:
            if next_author_id:
                await self.notif_repo.create(
                    next_author_id, "your_turn", chain.id, chain_title
                )
            if member_user_ids:
                await self.notif_repo.create_many(
                    [
                        {
                            "user_id": uid,
                            "type": "node_submitted",
                            "chain_id": chain.id,
                            "chain_title": chain_title,
                        }
                        for uid in member_user_ids
                    ]
                )

    async def _expire_chain(self, chain: Chain) -> None:
        """7 天未完成链标记 expired + 通知成员。"""
        await self.chain_repo.mark_expired(chain)
        members = await self.chain_repo.get_members(chain.id)
        member_user_ids = [m.user_id for m in members]
        chain_title = chain.title or ""
        if member_user_ids:
            await self.notif_repo.create_many(
                [
                    {
                        "user_id": uid,
                        "type": "chain_done",
                        "chain_id": chain.id,
                        "chain_title": chain_title,
                    }
                    for uid in member_user_ids
                ]
            )
        logger.info("Chain expired", chain_id=chain.id, title=chain_title)

    @staticmethod
    def _is_node_timeout(
        node: Node, now: datetime.datetime, timeout: datetime.timedelta
    ) -> bool:
        """节点是否超时（created_at + timeout < now）。"""
        if node.created_at is None:
            return False
        created = node.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=datetime.UTC)
        return created + timeout < now

    @staticmethod
    def _is_chain_expired(
        chain: Chain, now: datetime.datetime, expire: datetime.timedelta
    ) -> bool:
        """链是否 7 天过期（created_at + expire < now 且未完成）。"""
        if chain.created_at is None:
            return False
        created = chain.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=datetime.UTC)
        return created + expire < now
