from __future__ import annotations

import json
from dataclasses import dataclass

from daily_news.models import ArticleContent


@dataclass(frozen=True, slots=True)
class PromptProfile:
    name: str
    system_prompt: str
    user_instructions: str


DEFAULT_PROMPT_PROFILE = PromptProfile(
    name="default",
    system_prompt=(
        "你是一个中文科技内容编辑。"
        "请把英文或中文文章整理成适合个人视频频道使用的中文摘要。"
        "你必须输出严格 JSON，对象包含 headline、summary、key_points、script。"
        "headline 是适合中文视频的短标题；summary 是信息密度高的中文总结；"
        "key_points 是 4 到 6 条中文要点数组；script 是自然中文播报稿。"
    ),
    user_instructions=(
        "重点提炼核心结论、重要背景、关键数据和对读者真正有价值的信息。"
        "避免空话、营销式措辞和重复表述。"
    ),
)


ANTHROPIC_PROMPT_PROFILE = PromptProfile(
    name="anthropic",
    system_prompt=(
        "你是一名中文 AI 技术研究编辑，擅长把研究报告、模型发布说明和工程更新整理成高质量中文技术解读。"
        "请把文章整理成适合个人技术频道使用的中文总结。"
        "你必须输出严格 JSON，对象包含 headline、summary、key_points、script。"
        "对于 Anthropic 内容，重点关注模型能力、技术机制、实验方法、评测数据、工程实现、限制条件、价格/上下文窗口/视觉能力等硬信息。"
        "不要只写结论，要解释为什么它重要、与过去版本相比变化在哪里、对开发者或研究者意味着什么。"
        "summary 需要写成深入技术解读，目标长度约 1800 到 2200 个中文字符；"
        "key_points 需要 6 到 10 条，尽量具体；"
        "script 也应保持技术信息密度，适合作为中文口播长稿，允许略短于 summary，但不要过度简化。"
    ),
    user_instructions=(
        "请优先覆盖：模型版本变化、关键 benchmark、推理/编程/视觉能力、上下文或接口变化、价格与可用性、已知限制、安全机制，以及对实际使用场景的影响。"
    ),
)


PROMPT_PROFILES: dict[str, PromptProfile] = {
    ANTHROPIC_PROMPT_PROFILE.name: ANTHROPIC_PROMPT_PROFILE,
}


def get_prompt_profile(source_name: str) -> PromptProfile:
    return PROMPT_PROFILES.get(source_name, DEFAULT_PROMPT_PROFILE)


def build_summary_messages(article: ArticleContent) -> list[dict[str, str]]:
    profile = get_prompt_profile(article.article.source_name)
    user_prompt = {
        "source_name": article.article.source_name,
        "title": article.article.title,
        "url": article.article.url,
        "published_at": article.article.published_at,
        "author": article.article.author,
        "instructions": profile.user_instructions,
        "content": article.content_text[:24000],
    }
    return [
        {"role": "system", "content": profile.system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
    ]
