"""投票业务服务层。

依赖 VoteRepository + ChainRepository（成员校验），不依赖 FastAPI/HTTP。
- submit_votes：校验链完成 + 成员 + 三维度齐全 + target 属于链 + 未投过，批量插入
- get_result：按维度分组统计票数 + 批量查 target_author
"""

from pycore.core import get_logger
from src.db.models import User
from src.repositories.chain import ChainRepository
from src.repositories.vote import VoteRepository

logger = get_logger()

# 三维度枚举
DIMENSIONS = {"most_drift", "best_draw", "best_describe"}


class VoteService:
    """投票业务。"""

    def __init__(
        self, vote_repo: VoteRepository, chain_repo: ChainRepository
    ) -> None:
        self.vote_repo = vote_repo
        self.chain_repo = chain_repo

    async def submit_votes(
        self, chain_id: str, user: User, votes: list[dict]
    ) -> dict:
        """提交投票（三维度各一票）。

        Raises:
            LookupError: 链不存在（→404）。
            PermissionError: 非成员，或链未完成，或已投过（→403）。
            ValueError: 三维度不齐/重复 dimension/target 不属于链（→400）。
        """
        chain = await self.chain_repo.get_by_id(chain_id)
        if chain is None:
            raise LookupError("链不存在")

        # 成员校验
        member = await self.chain_repo.get_member(chain.id, user.id)
        if member is None:
            raise PermissionError("链未完成或无权投票")

        # 链完成校验
        if chain.status != "completed":
            raise PermissionError("链未完成或无权投票")

        # 已投过校验（每人每链只能投一次三维度）
        if await self.vote_repo.has_voted(chain.id, user.id):
            raise PermissionError("链未完成或无权投票")

        # 三维度齐全校验
        dims = {v["dimension"] for v in votes}
        if dims != DIMENSIONS:
            raise ValueError("必须为三个维度各投一票")

        # target_node 属于该链 + 已提交校验
        target_ids = {v["target_node_id"] for v in votes}
        for target_id in target_ids:
            node = await self.vote_repo.get_node(target_id)
            if node is None or node.chain_id != chain.id:
                raise ValueError("投票目标节点不属于该链")
            if node.status != "submitted":
                raise ValueError("投票目标节点不属于该链")

        # 批量插入（IntegrityError → ValueError「已投过票」）
        await self.vote_repo.create_votes(chain.id, user.id, votes)

        logger.info(
            "Votes submitted",
            chain_id=chain.id,
            user_id=user.id,
            dimensions=sorted(dims),
        )

        # 返回提交后的统计
        counts = await self.vote_repo.count_by_chain(chain.id)
        return {"results": counts}

    async def get_result(self, chain_id: str) -> dict:
        """投票结果统计（含 target_author）。

        Raises:
            LookupError: 链不存在（→404）。
        """
        chain = await self.chain_repo.get_by_id(chain_id)
        if chain is None:
            raise LookupError("链不存在")

        counts = await self.vote_repo.count_by_chain(chain.id)
        if not counts:
            return {"results": []}

        # 批量查节点（取 author_id + author_label）
        node_ids = list({c["target_node_id"] for c in counts})
        node_map = await self.vote_repo.get_nodes_by_ids(node_ids)

        # 批量查节点作者（author_id 非空的）
        author_ids = list(
            {n.author_id for n in node_map.values() if n.author_id}
        )
        author_map = await self.vote_repo.get_node_authors(author_ids)

        # 组装结果（author_id 为空时 fallback 到 node.author_label）
        results: list[dict] = []
        for c in counts:
            node = node_map.get(c["target_node_id"])
            author_id = node.author_id if node else ""
            author_user = author_map.get(author_id) if author_id else None
            nickname = (
                author_user.nickname if author_user else (node.author_label if node else "未知")
            )
            results.append(
                {
                    "dimension": c["dimension"],
                    "target_node_id": c["target_node_id"],
                    "target_author": {"id": author_id, "nickname": nickname},
                    "vote_count": c["vote_count"],
                }
            )
        return {"results": results}
