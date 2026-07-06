"""AI 分析模块 — 调用 AI 分析代码问题并生成修复方案"""

from __future__ import annotations

import json
import os
from typing import Optional

import httpx

from .chooser import Scheme

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个代码调试专家。你的任务：
1. 分析用户提供的问题代码或错误信息
2. 找出根本原因
3. 给出最多 3 个不同的修复方案

每个方案必须有不同的思路（不是参数微调）。
返回严格 JSON 格式（不要 markdown 代码块）：

{
  "root_cause": "根因的简洁描述",
  "schemes": [
    {
      "name": "方案A: 一句话方案名",
      "description": "核心修复思路和原理说明",
      "risk": "低/中/高",
      "scope": "小/中/大",
      "details": ["具体步骤1", "具体步骤2"]
    }
  ]
}

风险等级说明：
- 低：不影响其他功能，可安全回退
- 中：可能影响周边功能，需验证
- 高：架构级变更，影响面大

改动范围说明：
- 小：1-2 个文件，少量代码
- 中：3-5 个文件，中等改动
- 大：5+ 个文件或架构调整

重要：schemes 数组至少 1 个，最多 3 个方案。
如果只有一个最佳方案，也返回 1 个。
每个方案的思路必须不同！"""


def analyze_with_ai(
    input_text: str,
    config: dict,
    system_override: Optional[str] = None,
) -> Optional[dict]:
    """调用 AI API 分析问题并生成方案

    Args:
        input_text: 用户输入（代码/错误/问题描述）
        config: 配置字典（api_key, api_url, model 等）
        system_override: 可选的系统提示词覆盖

    Returns:
        {"root_cause": str, "schemes": [Scheme, ...]} 或 None
    """
    from rich.console import Console
    console = Console()

    api_key = config.get("api_key") or os.environ.get("FIX_CHOOSE_API_KEY") or ""
    api_url = config.get("api_url") or os.environ.get("FIX_CHOOSE_API_URL") or "https://openrouter.ai/api/v1/chat/completions"
    model = config.get("model") or os.environ.get("FIX_CHOOSE_MODEL") or "google/gemini-2.0-flash-001"

    if not api_key:
        console.print("[red]✗ 未配置 API Key。请设置环境变量或配置文件。[/red]")
        console.print("\n设置方式：")
        console.print("  1. export FIX_CHOOSE_API_KEY=your_key")
        console.print("  2. export FIX_CHOOSE_API_URL=https://openrouter.ai/api/v1/chat/completions")
        console.print("  3. export FIX_CHOOSE_MODEL=model_name")
        console.print("\n或者运行 fix-choose init 交互式配置[/dim]")
        return None

    system_prompt = system_override or DEFAULT_SYSTEM_PROMPT

    try:
        with console.status("[cyan]🔍 调用 AI 分析中...[/cyan]") as _:
            response = httpx.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    **({"HTTP-Referer": "https://github.com/fix-choose"} if "openrouter" in api_url else {}),
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": input_text},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
                timeout=120,
            )

        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]

    except httpx.TimeoutException:
        console.print("[red]✗ AI 请求超时。[/red]")
        return None
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ AI 请求失败 (HTTP {e.response.status_code}): {e.response.text[:200]}[/red]")
        return None
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        console.print(f"[red]✗ AI 响应解析失败: {e}[/red]")
        return None

    # 解析 JSON 响应
    return _parse_ai_response(content, console)


def _parse_ai_response(content: str, console: Console) -> Optional[dict]:
    """解析 AI 的 JSON 响应，处理可能的 markdown 包裹"""
    content = content.strip()
    if content.startswith("```"):
        start = content.find("\n")
        if start != -1:
            end = content.rfind("```")
            if end != -1:
                content = content[start:end].strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 尝试在文本中找 JSON 块
        import re
        match = re.search(
            r'\{[^{}]*"root_cause"[^{}]*"schemes"[^{}]*\}',
            content, re.DOTALL,
        )
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                console.print("[red]✗ AI 响应不是有效的 JSON 格式。[/red]")
                console.print(f"[dim]原始响应:\n{content[:500]}[/dim]")
                return None
        else:
            console.print("[red]✗ 无法从 AI 响应中提取方案数据。[/red]")
            console.print(f"[dim]原始响应:\n{content[:500]}[/dim]")
            return None

    # 构建返回结构
    root_cause = data.get("root_cause", "未找到根因描述")
    raw_schemes = data.get("schemes", [])

    if not raw_schemes:
        console.print("[red]✗ AI 响应中没有包含修复方案。[/red]")
        return None

    schemes = []
    for s in raw_schemes:
        schemes.append(Scheme(
            name=s.get("name", "未命名方案"),
            description=s.get("description", ""),
            risk=s.get("risk", "?"),
            scope=s.get("scope", "?"),
            details=s.get("details", []),
        ))

    return {
        "root_cause": root_cause,
        "schemes": schemes,
    }
