"""节点业务服务层（接力）。

依赖 NodeRepository + ChainRepository（成员校验）+ User，不依赖 FastAPI/HTTP。
- get_previous：防剧透，只返回上一节点；非当前责任人 → PermissionError（→403）
- submit_node：校验当前责任人，提交内容，推进链，创建下一节点
"""


from pycore.core import get_logger
from src.db.models import Node, User
from src.repositories.chain import ChainRepository
from src.repositories.node import NodeRepository

logger = get_logger()


class NodeService:
    """节点接力业务。"""

    def __init__(self, node_repo: NodeRepository, chain_repo: ChainRepository) -> None:
        self.node_repo = node_repo
        self.chain_repo = chain_repo

    async def get_previous(self, chain_id: str, user: User) -> dict:
        """获取上一节点内容（防剧透）。

        Raises:
            LookupError: 链不存在（→404）。
            PermissionError: 非链成员，或非当前节点责任人（→403）。
        """
        chain = await self.node_repo.get_chain(chain_id)
        if chain is None:
            raise LookupError("链不存在")

        # 成员校验
        member = await self.chain_repo.get_member(chain.id, user.id)
        if member is None:
            raise PermissionError("无权访问该链")

        # 链已完成 → 无当前节点可接力
        if chain.status == "completed":
            raise PermissionError("链已完成")

        current_node = await self.node_repo.get_current_node(chain)
        # 当前节点责任人校验（防剧透核心：只有当前责任人能看上一节点）
        if current_node is None or current_node.author_id != user.id:
            raise PermissionError("当前未轮到你")

        # 上一节点
        prev_node = await self.node_repo.get_previous_node(chain)
        if prev_node is not None:
            return _node_to_previous(prev_node)

        # seq=0 无上一节点 → 返回起手题作为"上一节点"（content_type=text）
        # 起手题是文字，当前节点 seq=0 是 draw，isDrawMode=true（看文字画图）
        return {
            "node_id": "",
            "seq": -1,
            "type": "describe",
            "content_type": "text",
            "content_url": None,
            "content_text": chain.prompt_text,
        }

    async def submit_node(
        self,
        chain_id: str,
        user: User,
        content_type: str,
        content_url: str | None,
        content_text: str | None,
    ) -> dict:
        """提交节点（接力）。

        Raises:
            LookupError: 链不存在（→404）。
            PermissionError: 非成员，或非当前责任人，或链已完成（→403）。
            ValueError: 内容类型与节点类型不匹配（→400）。
        """
        chain = await self.node_repo.get_chain(chain_id)
        if chain is None:
            raise LookupError("链不存在")

        member = await self.chain_repo.get_member(chain.id, user.id)
        if member is None:
            raise PermissionError("无权访问该链")

        if chain.status == "completed":
            raise PermissionError("链已完成，无法提交")

        current_node = await self.node_repo.get_current_node(chain)
        if current_node is None or current_node.author_id != user.id:
            raise PermissionError("当前未轮到你")

        # 内容类型与节点类型校验
        # draw 节点 → content_type=image；describe 节点 → content_type=text
        if current_node.type == "draw":
            if content_type != "image":
                raise ValueError("画节点必须提交图片")
            if not content_url:
                raise ValueError("图片地址不能为空")
        else:  # describe
            if content_type != "text":
                raise ValueError("描述节点必须提交文字")
            if not content_text or not content_text.strip():
                raise ValueError("描述文字不能为空")
            content_text = content_text.strip()

        # 更新节点提交内容
        await self.node_repo.update_node_submit(
            current_node, content_type, content_url, content_text
        )

        # 推进链 current_seq +1
        chain, is_completed = await self.node_repo.advance_chain(chain)

        # 创建下一节点（下一位承接），链完成则不创建
        # 下一位按成员加入顺序轮转：next_seq 对应成员索引 = next_seq % member_count
        # 成员不足时 author=None（待接，T-024 AI 补位）
        next_author_id: str | None = None
        if not is_completed:
            members = await self.chain_repo.get_members(chain.id)
            members.sort(key=lambda m: m.joined_at)
            next_author_label = "待接"
            if members:
                idx = chain.current_seq % len(members)
                next_member = members[idx]
                # 查该成员用户信息取 nickname
                next_user = await self.node_repo.get_user(next_member.user_id)
                if next_user is not None:
                    next_author_id = next_user.id
                    next_author_label = next_user.nickname
            await self.node_repo.create_next_node(
                chain,
                author_id=next_author_id,
                author_label=next_author_label,
            )
        next_seq = chain.current_seq if not is_completed else chain.chain_length

        logger.info(
            "Node submitted",
            chain_id=chain.id,
            node_id=current_node.id,
            seq=current_node.seq,
            next_seq=next_seq,
            chain_status=chain.status,
        )

        return {
            "node_id": current_node.id,
            "seq": current_node.seq,
            "status": current_node.status,
            "next_seq": next_seq,
            "next_author_id": next_author_id,
            "chain_status": chain.status,
        }


def _node_to_previous(node: Node) -> dict:
    """Node ORM → 上一节点 dict。"""
    return {
        "node_id": node.id,
        "seq": node.seq,
        "type": node.type,
        "content_type": node.content_type or "",
        "content_url": node.content_url,
        "content_text": node.content_text,
    }
