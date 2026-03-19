"""TTS 语音播报 — 使用 edge-tts 生成中文女声语音 (XiaoxiaoNeural)"""
import asyncio
import logging
from pathlib import Path

import edge_tts

from src.models import ProcessedArticle

logger = logging.getLogger(__name__)

VOICE = "zh-CN-XiaoxiaoNeural"
PROJECT_ROOT = Path(__file__).parent.parent.parent
AUDIO_DIR = PROJECT_ROOT / "site" / "audio"


def generate_daily_audio(
    news_list: list[ProcessedArticle],
    paper_list: list[ProcessedArticle],
    date_str: str,
) -> str | None:
    """
    为当日日报生成 MP3 语音播报文件。
    返回相对于 site/ 的音频路径（如 'audio/2026-03-19.mp3'），失败返回 None。
    """
    script = _build_script(news_list, paper_list, date_str)
    if not script:
        logger.warning("TTS 脚本为空，跳过语音生成")
        return None

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{date_str}.mp3"
    output_path = AUDIO_DIR / filename

    try:
        asyncio.run(_synthesize(script, str(output_path)))
        size_kb = output_path.stat().st_size / 1024
        logger.info(f"语音播报已生成: {output_path} ({size_kb:.0f} KB)")
        return f"audio/{filename}"
    except Exception as e:
        logger.error(f"TTS 语音生成失败: {e}")
        return None


async def _synthesize(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE, rate="+10%")
    await communicate.save(output_path)


def _build_script(
    news_list: list[ProcessedArticle],
    paper_list: list[ProcessedArticle],
    date_str: str,
) -> str:
    parts = [f"AI 日报，{date_str}。"]

    if news_list:
        parts.append("首先为您播报今日AI资讯。")
        for i, item in enumerate(news_list, 1):
            parts.append(f"第{i}条，{item.title}。{item.description}")

    if paper_list:
        parts.append("接下来是AI论文解读。")
        for i, item in enumerate(paper_list, 1):
            parts.append(f"第{i}篇，{item.title}。{item.description}")

    parts.append("以上就是今天的AI日报全部内容，感谢收听！")
    return "\n".join(parts)
