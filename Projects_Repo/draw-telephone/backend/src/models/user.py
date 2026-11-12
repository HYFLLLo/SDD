"""
用户相关 Pydantic 模型（API/领域模型，与 api-contracts.md 对齐）。

- UserCreate / LoginRequest：请求体入参
- UserPublic：响应出参（不含 password_hash）
- AuthData：注册/登录成功响应 data（access_token + user）
"""

from pydantic import BaseModel, ConfigDict, Field


class UserPublic(BaseModel):
    """用户公开信息（响应序列化，不含密码）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    nickname: str
    avatar_url: str | None = None


class RegisterRequest(BaseModel):
    """POST /api/auth/register 请求体。"""

    username: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1, max_length=128)
    nickname: str = Field(..., min_length=1, max_length=50)


class LoginRequest(BaseModel):
    """POST /api/auth/login 请求体。"""

    username: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1, max_length=128)


class AuthData(BaseModel):
    """注册/登录成功响应 data。"""

    access_token: str
    user: UserPublic


class UserProfileResponse(BaseModel):
    """GET /api/users/me 响应（个人资料 + 参与链数/创建链数统计）。"""

    id: str
    username: str
    nickname: str
    avatar_url: str | None = None
    created_at: str
    participated_chains: int
    created_chains: int


class MyWorkItemResponse(BaseModel):
    """GET /api/users/me/works 列表项（我参与或创建的链）。"""

    id: str
    title: str
    chain_length: int
    status: str  # in_progress / completed
    role: str  # creator / participant
    thumb_url: str
    created_at: str


class MyWorkListResponse(BaseModel):
    """GET /api/users/me/works 响应。"""

    items: list[MyWorkItemResponse]
    total: int
    page: int
    page_size: int
