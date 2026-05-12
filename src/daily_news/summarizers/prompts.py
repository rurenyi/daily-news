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
        "请把英文或中文文章整理成适合个人视频频道使用的中文翻译与讲解。"
        "你必须输出严格 JSON，对象包含 headline、summary、key_points、script。"
        "headline 是适合中文视频的短标题，优先使用准确自然的中文译名；"
        "summary 是信息密度高的中文翻译讲解正文，不要只做结论式摘要；"
        "key_points 是 4 到 6 条帮助理解原文的中文讲解要点数组；"
        "script 是自然中文口播稿，要像在向观众解释原文。"
        "summary 必须保留原文中的方法、流程、数据、实验设计、实现细节与限制条件；不要把具体内容压缩成空泛结论。"
        "如果原文包含步骤、机制或实践方法，summary 里要明确写出这些步骤和方法是怎样做的。"
        "不要人为控制字数；只要原文里有重要细节，就应完整展开讲解。"
    ),
    user_instructions=(
        "先忠实转述原文的核心信息，再补充必要的背景解释、术语说明和上下文。"
        "避免空话、营销式措辞和只有结论没有过程的简写。"
        "优先解释：作者到底做了什么、怎么做、为什么这样做、实验或实践里观察到了什么。"
    ),
)


ANTHROPIC_PROMPT_PROFILE = PromptProfile(
    name="anthropic",
    system_prompt=(
        "你是一名中文 AI 技术研究编辑，擅长把研究报告、模型发布说明和工程更新整理成高质量中文技术解读。"
        "请把文章整理成适合个人技术频道使用的中文翻译与讲解。"
        "你必须输出严格 JSON，对象包含 headline、summary、key_points、script。"
        "对于 Anthropic 内容，重点关注模型能力、技术机制、实验方法、评测数据、工程实现、限制条件、价格/上下文窗口/视觉能力等硬信息。"
        "不要只写结论，要把关键内容翻译成自然中文，并解释为什么它重要、与过去版本相比变化在哪里、对开发者或研究者意味着什么。"
        "summary 需要写成深入技术翻译讲解，不要人为限制篇幅；"
        "summary 必须覆盖研究目标、核心假设、方法设计、关键实验、评测设置、结果数据、失败模式、局限与实际意义；"
        "如果原文出现训练流程、审计流程、对齐方法、实验 protocol、benchmark、消融实验、系统提示或部署策略，必须明确写出，不要只写成一句概括；"
        "可以按主题分段，例如：研究问题、方法机制、实验设置、结果与发现、局限与启发；"
        "key_points 需要 8 到 12 条，尽量具体，并包含技术做法而不只是结论；"
        "script 也应保持技术信息密度，适合作为中文口播长稿，允许略短于 summary，但不要过度简化；script 要像在逐段给听众讲解论文/博文，而不是报摘要。"
    ),
    user_instructions=(
        "请优先覆盖：模型版本变化、关键 benchmark、推理/编程/视觉能力、上下文或接口变化、价格与可用性、已知限制、安全机制，以及对实际使用场景的影响。"
        "如果原文出现容易误解的术语、基准或产品描述，先准确翻译，再补一层解释。"
        "尤其不要遗漏技术要点和实践细节：如果文中提到具体训练信号、评测场景、对齐策略、失败案例、数据规模、执行流程、工具链或落地方式，请逐项讲清楚。"
        "输出 summary 时，尽量把重要细节翻译进正文，而不是把大量信息藏到 key_points 里。"
        "只要原文还在提供有效技术信息，就继续讲清楚，不要为了控制长度而主动省略。"
    ),
)


PROMPT_PROFILES: dict[str, PromptProfile] = {
    ANTHROPIC_PROMPT_PROFILE.name: ANTHROPIC_PROMPT_PROFILE,
}


def get_prompt_profile(source_name: str) -> PromptProfile:
    if source_name in PROMPT_PROFILES:
        return PROMPT_PROFILES[source_name]
    if source_name.startswith("anthropic"):
        return ANTHROPIC_PROMPT_PROFILE
    return DEFAULT_PROMPT_PROFILE


def build_summary_messages(article: ArticleContent) -> list[dict[str, str]]:
    profile = get_prompt_profile(article.article.source_name)
    user_prompt = {
        "source_name": article.article.source_name,
        "title": article.article.title,
        "url": article.article.url,
        "published_at": article.article.published_at,
        "author": article.article.author,
        "instructions": profile.user_instructions,
        "content": article.content_text,
    }
    return [
        {"role": "system", "content": profile.system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
    ]
