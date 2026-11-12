"""
用户业务服务层。

依赖 Repository + security 原语，不依赖 FastAPI/HTTP。
- 注册：用户名已存在 → ValueError（路由映射 400）
- 登录：用户不存在/密码错误 → PermissionError（路由映射 401）
- 个人资料：用户不存在 → LookupError（路由映射 404，理论上 token 有效不会触发）
- 我的作品：查用户参与/创建的链，role 区分 creator/participant

两种异常类型区分，避免路由层用单一 @handle_errors 把 ValueError 统一映射成 400。
"""

from pycore.core import get_logger
from src.core.security import create_access_token, hash_password, verify_password
from src.db.models import User
from src.repositories.user import UserRepository
from src.repositories.work import WorkRepository

logger = get_logger()


class UserService:
    """用户注册/登录/个人资料业务。"""

    def __init__(
        self, repo: UserRepository, work_repo: WorkRepository | None = None
    ) -> None:
        self.repo = repo
        self.work_repo = work_repo

    async def register(self, username: str, password: str, nickname: str) -> tuple[User, str]:
        """
        注册新用户并签发 token。

        Raises:
            ValueError: 用户名已存在（路由映射 400）。
        """
        existing = await self.repo.get_by_username(username)
        if existing:
            raise ValueError("用户名已存在")

        hashed = hash_password(password)
        user = await self.repo.create(username, hashed, nickname)
        token = create_access_token(user.id, user.username)
        logger.info("User registered", user_id=user.id, username=user.username)
        return user, token

    async def login(self, username: str, password: str) -> tuple[User, str]:
        """
        校验凭据并签发 token。

        用户不存在或密码错误均返回 PermissionError（路由映射 401），
        不区分「用户不存在」与「密码错误」，避免用户名枚举。

        Raises:
            PermissionError: 用户名或密码错误（路由映射 401）。
        """
        user = await self.repo.get_by_username(username)
        if user is None:
            raise PermissionError("用户名或密码错误")

        if not verify_password(password, user.password_hash):
            raise PermissionError("用户名或密码错误")

        token = create_access_token(user.id, user.username)
        logger.info("User logged in", user_id=user.id, username=user.username)
        return user, token

    async def get_profile(self, user_id: str) -> dict:
        """个人资料（含参与链数/创建链数统计）。

        Raises:
            LookupError: 用户不存在（路由映射 404，理论上 token 有效不会触发）。
        """
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise LookupError("用户不存在")

        participated = await self.repo.count_participated(user_id)
        created = await self.repo.count_created(user_id)
        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "participated_chains": participated,
            "created_chains": created,
        }

    async def list_my_works(
        self, user_id: str, page: int, page_size: int
    ) -> dict:
        """我的作品列表（参与或创建的链，含 in_progress + completed）。

        返回 {items, total, page, page_size}。
        role: creator（creator_id==user_id）/ participant（仅成员非创建者）。
        thumb_url: 链第一个 draw 节点的 content_url（复用 WorkRepository.get_thumb_url）。
        """
        chains, total = await self.repo.list_my_works(user_id, page, page_size)
        items: list[dict] = []
        for chain in chains:
            role = "creator" if chain.creator_id == user_id else "participant"
            thumb_url = ""
            if self.work_repo is not None:
                thumb_url = await self.work_repo.get_thumb_url(chain.id)
            items.append(
                {
                    "id": chain.id,
                    "title": chain.title or "",  # Chain.title 可空，None → ""（否则 MyWorkListItem.title: str 校验失败 500）
                    "chain_length": chain.chain_length,
                    "status": chain.status,
                    "role": role,
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
