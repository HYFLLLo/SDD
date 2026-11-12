"""作品业务服务层（只读）。

依赖 WorkRepository，不依赖 FastAPI/HTTP。
- list_works：广场作品列表（分页 + 排序），含 member_count/like_count/thumb_url
- get_work_detail：作品详情（只读全链，含所有已提交节点 + 作者 + is_ai）
"""

from pycore.core import get_logger
from src.repositories.work import WorkRepository

logger = get_logger()


class WorkService:
    """作品只读业务。"""

    def __init__(self, repo: WorkRepository) -> None:
        self.repo = repo

    async def list_works(
        self, page: int, page_size: int, sort: str
    ) -> dict:
        """广场作品列表（分页 + 排序）。

        Returns:
            {"items": [...], "total": N, "page": page, "page_size": page_size}
        """
        chains, total = await self.repo.list_completed_chains(
            page, page_size, sort
        )
        items: list[dict] = []
        for chain in chains:
            member_count = await self.repo.count_members(chain.id)
            like_count = await self.repo.count_likes(chain.id)
            thumb_url = await self.repo.get_thumb_url(chain.id)
            items.append(
                {
                    "id": chain.id,
                    "title": chain.title or "",
                    "chain_length": chain.chain_length,
                    "member_count": member_count,
                    "like_count": like_count,
                    "thumb_url": thumb_url,
                    "created_at": chain.created_at.isoformat()
                    if chain.created_at
                    else "",
                }
            )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_work_detail(self, chain_id: str) -> dict:
        """作品详情（只读全链）。

        Raises:
            LookupError: 链不存在或未完成（→404）。
        """
        chain = await self.repo.get_chain(chain_id)
        if chain is None:
            raise LookupError("作品不存在")
        # 只读全链要求链已完成（未完成的不展示作品详情）
        if chain.status != "completed":
            raise LookupError("作品不存在")

        creator = await self.repo.get_creator(chain.creator_id)
        nodes = await self.repo.get_nodes(chain.id)
        # 批量查节点作者
        author_ids = [n.author_id for n in nodes if n.author_id]
        author_map = await self.repo.get_node_authors(author_ids)

        node_list: list[dict] = []
        for node in nodes:
            author_id = node.author_id or ""
            author_user = author_map.get(author_id) if author_id else None
            nickname = (
                author_user.nickname
                if author_user
                else node.author_label
            )
            node_list.append(
                {
                    "id": node.id,
                    "seq": node.seq,
                    "type": node.type,
                    "author": {"id": author_id, "nickname": nickname},
                    "content_type": node.content_type or "",
                    "content_url": node.content_url,
                    "content_text": node.content_text,
                    "is_ai": node.is_ai,
                    "submitted_at": node.submitted_at.isoformat()
                    if node.submitted_at
                    else "",
                }
            )

        logger.info(
            "Work detail queried",
            chain_id=chain.id,
            node_count=len(node_list),
        )
        return {
            "id": chain.id,
            "title": chain.title or "",
            "chain_length": chain.chain_length,
            "creator": {
                "id": creator.id if creator else chain.creator_id,
                "nickname": creator.nickname if creator else "未知",
            },
            "prompt_source": chain.prompt_source,
            "prompt_text": chain.prompt_text,
            "status": chain.status,
            "created_at": chain.created_at.isoformat()
            if chain.created_at
            else "",
            "completed_at": chain.completed_at.isoformat()
            if chain.completed_at
            else None,
            "nodes": node_list,
        }
