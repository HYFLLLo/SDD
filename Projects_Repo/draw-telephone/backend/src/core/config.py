"""
应用配置。

基于 pydantic-settings 的 BaseSettings 从 backend/.env 读取配置。
所有敏感配置（API Key、JWT Secret、数据库路径等）必须从 .env 读取，禁止硬编码。

注意：pycore.core.ConfigManager 仅支持 TOML，而项目要求 .env 配置。
因此使用 pydantic-settings 的 BaseSettings 直接读取 backend/.env，
符合「配置必须通过后端配置文件获取」的规范，且不继承进程环境变量。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录绝对路径（本文件位于 backend/src/core/config.py）
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
# 项目根目录（backend/ 的父目录，pycore/ 在此）
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """应用设置。从 backend/.env 读取，不继承进程环境变量。"""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        # 不从进程环境变量读取，只从 .env 文件读取
        env_nested_delimiter="__",
    )

    # 服务
    host: str = "127.0.0.1"
    port: int = 8099
    debug: bool = True

    # CORS：同时允许 localhost/127.0.0.1 的 5199（Agent 验证）和 5175（用户门禁）
    cors_origins: list[str] = [
        "http://localhost:5199",
        "http://127.0.0.1:5199",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]

    # 数据库：项目根相对路径，运行时解析为绝对路径
    database_path: str = "backend/data/draw_telephone.db"

    # JWT
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 168  # 7 天

    # AI/LLM 文本生成（公司内网 MaaS / 海康）—— 起手题词生成（T-015）
    # MaaS 兼容 OpenAI /chat/completions 格式，DeepSeek 模型做文本生成
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://maas.hikvision.com.cn/v1"
    deepseek_model: str = "DeepSeek-V4-Flash-0731"

    # 图像生成（公司内网 MaaS / 海康 Qwen-Image）—— 文生图，AI 补位画节点（T-024）
    image_api_key: str = ""
    image_base_url: str = "https://maas.hikvision.com.cn/v1"
    image_model: str = "Qwen-Image"

    # 多模态看图（公司内网 MaaS / 海康）—— 看图生成文字，AI 补位述节点（T-024）
    vlm_api_key: str = ""
    vlm_base_url: str = "https://maas.hikvision.com.cn/v1"
    vlm_model: str = "Qwen3.6-35B-A3B-FP8"

    # AI 补位定时任务
    ai_fill_timeout_hours: int = 24
    chain_expire_days: int = 7

    # 图片上传（T-018）：本地文件存储目录 + URL 前缀
    # 目录基于 backend/，URL 前缀用于前端访问（Vite proxy /uploads → 后端 StaticFiles）
    upload_dir: str = "uploads"
    upload_url_prefix: str = "/uploads"

    @property
    def upload_path(self) -> Path:
        """上传目录绝对路径，自动创建。"""
        p = Path(self.upload_dir)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def database_url(self) -> str:
        """构造 SQLite 异步数据库 URL，解析为绝对路径并创建父目录。"""
        db_path = Path(self.database_path)
        # 若为相对路径，基于项目根目录解析
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path
        # 自动创建父目录，避免 cd backend 启动时路径解析错误
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # SQLAlchemy 异步 SQLite URL 需要 4 个斜杠（绝对路径）
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"


# 全局单例
settings = Settings()
