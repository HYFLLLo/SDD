"""APScheduler 定时任务。

每小时扫描 AI 补位（24h 未提交节点）+ 7 天过期链。
独立 session（不持有请求级 session），与 T-019 WS stroke 校验同模式。
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from pycore.core import get_logger
from src.db.session import async_session_maker
from src.services.ai_fill import AiFillService

logger = get_logger()

_scheduler: AsyncIOScheduler | None = None


def init_scheduler() -> None:
    """启动定时任务（每小时扫描 AI 补位）。main.py on_startup 调用。"""
    global _scheduler
    if _scheduler is not None:
        return  # 防止重复启动（reload 时）
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _ai_fill_job, IntervalTrigger(hours=1), id="ai_fill", replace_existing=True
    )
    _scheduler.start()
    logger.info("AI fill scheduler started (every 1 hour)")


async def _ai_fill_job() -> None:
    """AI 补位扫描任务。独立 session。"""
    async with async_session_maker() as db:
        try:
            service = AiFillService(db)
            result = await service.scan_and_fill()
            await db.commit()
            logger.info("AI fill job done", **result)
        except Exception:
            await db.rollback()
            logger.exception("AI fill job failed")


async def shutdown_scheduler() -> None:
    """关闭定时任务。main.py on_shutdown 调用。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("AI fill scheduler stopped")
