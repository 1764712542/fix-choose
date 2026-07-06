"""交互式方案选择器 — 带 Yes/No 按钮的循环选择"""

from dataclasses import dataclass, field
from typing import Optional, List

from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.table import Table
import questionary


@dataclass
class Scheme:
    """修复方案数据模型"""
    name: str                              # 方案名
    description: str = ""                  # 方案描述
    risk: str = "?"                        # 风险等级: 低/中/高
    scope: str = "?"                       # 改动范围: 小/中/大
    details: List[str] = field(default_factory=list)  # 具体改动步骤


def _render_scheme_card(scheme: Scheme, index: int, total: int) -> None:
    """渲染方案卡片"""
    console = Console()

    # 风险颜色
    risk_color = {
        "低": "green",
        "中": "yellow",
        "高": "red",
    }.get(scheme.risk, "white")

    scope_color = {
        "小": "green",
        "中": "yellow",
        "大": "red",
    }.get(scheme.scope, "white")

    # 方案信息
    info = (
        f"[bold cyan]方案 {scheme.name}[/bold cyan]\n\n"
        f"[white]{scheme.description}[/white]\n\n"
        f"[{risk_color}]📊 风险等级：[bold]{scheme.risk}[/bold][/{risk_color}]      "
        f"[{scope_color}]📏 改动范围：[bold]{scheme.scope}[/bold][/{scope_color}]"
    )

    # 如果有具体步骤
    if scheme.details:
        steps = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(scheme.details))
        info += f"\n\n[dim]具体步骤：[/dim]\n{steps}"

    console.print(
        Panel(
            info,
            title=f"[bold]🔧 方案 ({index}/{total})[/bold]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def _ask_yes_no(console: Console, prompt: str = "是否按此方案执行？") -> bool:
    """显示 Yes/No 选择器（方向键 + 回车）"""
    console.print()  # 空行

    choice = questionary.select(
        prompt,
        choices=[
            questionary.Choice(title="✅ 是的，就这个方案，执行吧", value=True),
            questionary.Choice(title="❌ 不，换一个方案", value=False),
        ],
        qmark="🔧",
        use_indicator=True,
        pointer="→",
    ).ask()

    return choice


def interactive_loop(schemes: List[Scheme], console: Console) -> Optional[Scheme]:
    """交互式方案选择循环

    依次展示每个方案，让用户 Yes/No 选择。
    Yes → 返回该方案
    No  → 展示下一个方案
    全部被拒 → 返回 None
    """
    total = len(schemes)
    rejected_reasons = []

    for i, scheme in enumerate(schemes, 1):
        _render_scheme_card(scheme, i, total)

        if i < total:
            choice = _ask_yes_no(console, "是否按此方案执行？")
        else:
            choice = _ask_yes_no(console, "最后一个方案了，怎么样？")

        if choice is True:
            return scheme

        # 记录拒绝原因
        console.print("[dim]👀 能说一下为什么不想用这个方案吗？[/dim]")
        reason = questionary.text(
            "或者直接回车跳过：",
            default="",
            qmark="💬",
        ).ask()
        if reason:
            rejected_reasons.append(f"{scheme.name}: {reason}")
        console.print()

    # 所有方案都被拒
    if rejected_reasons:
        console.rule("[bold yellow]📋 已尝试的方案总结")
        for r in rejected_reasons:
            console.print(f"  [dim]• {r}[/dim]")
        console.print()

    return None
