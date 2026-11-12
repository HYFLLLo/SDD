"""AI 起手题生成服务。

调用 DeepSeek 生成具象但开放的起手题词。Key 缺失或调用失败时降级到本地题词池，
不静默吞错：Key 缺失抛 RuntimeError（路由层映射 503），调用失败记日志后降级。
"""

import base64
import random

import httpx

from pycore.core import get_logger
from src.core.config import settings

logger = get_logger()

# fallback 题词池：具象但开放，易被误读（适合画意接龙的「漂移」效果）
FALLBACK_PROMPTS = [
    "戴帽子的猫",
    "会飞的鱼",
    "山与日",
    "眼睛里的海",
    "三棵树",
    "会跳舞的灯泡",
    "吃云朵的鲸",
    "打伞的蜗牛",
    "月亮上的信箱",
    "长翅膀的钟",
]

# DeepSeek 系统提示：生成具象但开放的短题词，适合绘画接力
SYSTEM_PROMPT = (
    "你是画意接龙游戏的起手题词生成器。请生成具象但开放、容易被误读的短题词，"
    "2-6 个汉字，适合作为绘画接力起点。只输出题词本身，每行一个，不要编号和解释。"
)


class AiService:
    """AI 起手题生成服务。"""

    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        self.image_api_key = settings.image_api_key
        self.image_base_url = settings.image_base_url
        self.image_model = settings.image_model
        self.vlm_api_key = settings.vlm_api_key
        self.vlm_base_url = settings.vlm_base_url
        self.vlm_model = settings.vlm_model

    def _fallback(self, count: int) -> list[str]:
        """从本地题词池随机取 count 个（不重复，若池不够则允许重复）。"""
        if count >= len(FALLBACK_PROMPTS):
            return random.sample(FALLBACK_PROMPTS, len(FALLBACK_PROMPTS)) + [
                random.choice(FALLBACK_PROMPTS) for _ in range(count - len(FALLBACK_PROMPTS))
            ]
        return random.sample(FALLBACK_PROMPTS, count)  # noqa: S311

    async def generate_prompts(self, count: int) -> list[str]:
        """生成 count 个起手题词。

        - Key 缺失：抛 RuntimeError（路由层映射 503），不静默降级
        - Key 存在：调 DeepSeek，成功返回真实题词；失败记日志后降级到本地池
        """
        if not self.api_key:
            logger.warning("DeepSeek API key missing, cannot generate real prompts")
            raise RuntimeError("AI 服务暂不可用，请手动输入题词")

        try:
            prompts = await self._call_deepseek(count)
            logger.info("DeepSeek prompts generated", count=len(prompts))
            return prompts
        except httpx.HTTPError as e:
            logger.warning("DeepSeek call failed, degrading to fallback", error_msg=str(e))
            return self._fallback(count)

    async def _call_deepseek(self, count: int) -> list[str]:
        """调用 DeepSeek chat completions，返回 count 个题词。

        httpx.AsyncClient 显式 trust_env=False，不继承环境变量/代理/证书。
        """
        async with httpx.AsyncClient(trust_env=False, timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"请生成 {count} 个起手题词"},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.9,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # 按行分割，去空行，取前 count 个
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            prompts = lines[:count]
            # 若模型返回不足 count 个，用 fallback 补齐
            if len(prompts) < count:
                prompts.extend(self._fallback(count - len(prompts)))
            return prompts

    async def generate_image(self, prompt: str) -> str:
        """Qwen-Image 文生图。返回图片 URL（MaaS 存储 URL）。

        - Key 缺失：抛 RuntimeError（补位任务记日志后跳过，下次重试）
        - 调用失败：抛 RuntimeError

        返回的 URL 是 MaaS 存储 URL，前端 img src 可直接用（浏览器访问）。
        """
        if not self.image_api_key:
            logger.warning("Image API key missing, cannot generate image")
            raise RuntimeError("图像生成服务暂不可用")

        try:
            async with httpx.AsyncClient(trust_env=False, timeout=90.0) as client:
                resp = await client.post(
                    f"{self.image_base_url}/images/generations",
                    headers={"Authorization": f"Bearer {self.image_api_key}"},
                    json={
                        "model": self.image_model,
                        "prompt": prompt,
                        "n": 1,
                        "size": "1024x1024",
                    },
                )
                if resp.status_code != 200:
                    # 403 限流/鉴权、5xx 服务不可用 → 转可读消息，路由层映射 503
                    body = resp.text[:200]
                    logger.warning("Image generation failed", status=resp.status_code, body=body)
                    if resp.status_code == 403:
                        raise RuntimeError("图像生成服务繁忙（频率受限），请稍后重试")
                    raise RuntimeError(f"图像生成服务异常（{resp.status_code}）")
                data = resp.json()
                url = str(data["data"][0]["url"])
                logger.info("Image generated", prompt=prompt, url=url[:80])
                return url
        except httpx.HTTPError as e:
            # 超时/连接失败是网络层错误，转可读 RuntimeError => 路由映射 503（不 500）
            logger.warning("Image generation network error", error_msg=str(e))
            raise RuntimeError("图像生成服务暂时不可用，请稍后重试") from e

    async def describe_image(self, image_url: str) -> str:
        """Qwen3.6 VLM 看图生成文字描述（≤30 字，Node.content_text 限制）。

        - Key 缺失：抛 RuntimeError
        - 看图失败（图片不可访问）：降级为纯文本续写（基于 image_url 不可见，
          用通用提示让模型生成一段描述性文字，保证补位闭环可用）

        image_url 若是本地 /uploads/ 路径，读文件 base64 传 VLM（本地可读）；
        若是远程 URL（MaaS 存储链接下载不了），降级纯文本续写。
        """
        if not self.vlm_api_key:
            logger.warning("VLM API key missing, cannot describe image")
            raise RuntimeError("图像理解服务暂不可用")

        # 尝试获取图片 base64（本地文件可直接读，远程 URL 尝试下载）
        b64 = await self._fetch_image_base64(image_url)

        if b64 is not None:
            # 看图模式：base64 传 VLM
            try:
                return await self._call_vlm(
                    [
                        {"type": "image_url", "image_url": {"url": b64}},
                        {"type": "text", "text": "用一句话描述这张图片，不超过20个字"},
                    ]
                )
            except RuntimeError as e:
                # 限流/服务异常 → 直接抛（不降级，让用户知道繁忙）
                if "繁忙" in str(e):
                    raise
                # 其他 RuntimeError（看图调用失败）→ 降级纯文本续写
                logger.warning("VLM image understanding failed, degrading to text", error_msg=str(e))

        # 降级：纯文本续写（VLM 看图不可用时，生成一段描述性文字兜底）
        logger.info("VLM degrading to text continuation", image_url=image_url[:80])
        return await self._call_vlm(
            [{"type": "text", "text": "请用一句话描述一个画面，不超过20个字，作为画意接龙的描述节点"}]
        )

    async def _fetch_image_base64(self, image_url: str) -> str | None:
        """获取图片 base64 data URL。本地 /uploads/ 文件直接读，远程 URL 尝试下载。

        下载失败（远程图片不可访问）返回 None，调用方降级纯文本。
        """
        # 本地 /uploads/ 路径：直接读文件
        if image_url.startswith(settings.upload_url_prefix):
            file_path = settings.upload_path / image_url.removeprefix(
                settings.upload_url_prefix + "/"
            )
            if file_path.is_file():
                data = file_path.read_bytes()
                ext = file_path.suffix.lstrip(".") or "png"
                return f"data:image/{ext};base64,{base64.b64encode(data).decode()}"
            return None

        # 远程 URL：尝试下载（MaaS 存储链接可能下载不了）
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=60.0) as client:
                resp = await client.get(
                    image_url,
                    headers={"Authorization": f"Bearer {self.image_api_key}"},
                    follow_redirects=True,
                )
                if resp.status_code == 200 and len(resp.content) > 1000:
                    return f"data:image/jpeg;base64,{base64.b64encode(resp.content).decode()}"
        except httpx.HTTPError:
            pass
        return None

    async def _call_vlm(self, content: list[dict]) -> str:
        """调用 Qwen3.6 VLM chat completions，返回文本内容（截断 ≤30 字）。"""
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=60.0) as client:
                resp = await client.post(
                    f"{self.vlm_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.vlm_api_key}"},
                    json={
                        "model": self.vlm_model,
                        "messages": [{"role": "user", "content": content}],
                        "max_tokens": 100,
                    },
                )
                if resp.status_code != 200:
                    body = resp.text[:200]
                    logger.warning("VLM call failed", status=resp.status_code, body=body)
                    if resp.status_code == 403:
                        raise RuntimeError("图像理解服务繁忙（频率受限），请稍后重试")
                    raise RuntimeError(f"图像理解服务异常（{resp.status_code}）")
                data = resp.json()
                text = str(data["choices"][0]["message"]["content"]).strip()
                # Node.content_text 限制 30 字，截断
                if len(text) > 30:
                    text = text[:30]
                logger.info("VLM described", text=text)
                return text
        except httpx.HTTPError as e:
            # 超时/连接失败是网络层错误，转可读 RuntimeError => 路由映射 503（不 500）
            logger.warning("VLM network error", error_msg=str(e))
            raise RuntimeError("图像理解服务暂时不可用，请稍后重试") from e
