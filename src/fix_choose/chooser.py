"""交互式方案选择器 — 持续循环：方案A/B/C + 自定义 + AI重思考 + No"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple

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
    done: bool = False                     # 是否已执行


@dataclass
class ChoiceResult:
    """交互选择结果"""
    action: str                            # execute | rethink | custom | none
    scheme: Optional[Scheme] = None        # 选中的方案
    # action=custom 时自定义的方案
    custom: Optional[Scheme] = None


def _risk_icon(risk: str) -> str:
    return {"低": "🟢", "中": "🟡", "高": "🔴"}.get(risk, "⚪")


def _scope_icon(scope: str) -> str:
    return {"小": "📏", "中": "📐", "大": "🏗️"}.get(scope, "📋")


def _render_schemes_overview(schemes: List[Scheme], console: Console) -> None:
    """表格展示所有方案"""
    table = Table(box=box.ROUNDED, border_style="cyan",
                  title="📋 修复方案", title_style="bold cyan")
    table.add_column("#", style="bold", width=6)
    table.add_column("方案名称", style="bold cyan", no_wrap=True)
    table.add_column("风险", justify="center")
    table.add_column("改动", justify="center")
    table.add_column("说明", style="white", max_width=50)
    table.add_column("状态", justify="center", width=8)

    emojis = ["🔧", "💡", "⭐", "🔹"]
    for i, s in enumerate(schemes, 1):
        emoji = emojis[i - 1] if i <= len(emojis) else "▫️"
        status = "[green]✓ 已执行[/green]" if s.done else "[dim]待选择[/dim]"
        table.add_row(
            f"{emoji} {i}",
            (s.name[:20] + "…") if len(s.name) > 20 else s.name,
            f"{_risk_icon(s.risk)} {s.risk}",
            f"{_scope_icon(s.scope)} {s.scope}",
            s.description[:48] + ("…" if len(s.description) > 48 else ""),
            status,
        )

    console.print()
    console.print(table)
    console.print()


def interactive_loop(schemes: List[Scheme], console: Console) -> ChoiceResult:
    """持续方案选择循环

    展示所有方案 + 自定义 + AI重思考 + No 四个按钮。
    重复选择直到用户选 No 或 AI 重思考。
    返回 ChoiceResult。
    """
    _render_schemes_overview(schemes, console)

    # 可用方案（未执行的）
    available = [(i, s) for i, s in enumerate(schemes) if not s.done]
    has_available = len(available) > 0

    choices = []

    # 可选方案
    if has_available:
        emojis = ["🔧", "💡", "⭐", "🔹"]
        for idx, (orig_i, s) in enumerate(available):
            order = idx + 1
            emoji = emojis[idx] if idx < len(emojis) else "▫️"
            label = f"{emoji} {s.name}  {_risk_icon(s.risk)} {s.risk}  {_scope_icon(s.scope)} {s.scope}"
            choices.append(questionary.Choice(title=label, value=("scheme", orig_i)))
    else:
        choices.append(questionary.Choice(
            title="[dim]（所有方案已执行）[/dim]",
            value=("noop", None),
            disabled=True,
        ))

    choices.append(questionary.Separator("─" * 44))

    # 自定义方案
    choices.append(questionary.Choice(
        title="✏️ 我自己来输入一个方案",
        value=("custom", None),
    ))

    # AI 重新思考其他方案
    choices.append(questionary.Choice(
        title="🤖 让 AI 再想想其他方案",
        value=("rethink", None),
    ))

    # No — 结束
    choices.append(questionary.Choice(
        title="❌ 不修了，结束",
        value=("none", None),
    ))

    console.print("[dim]按 ↑↓ 方向键选择，回车确认[/dim]")
    result = questionary.select(
        "请选择你要执行的操作：",
        choices=choices,
        qmark="🔧",
        use_indicator=True,
        pointer="→",
    ).ask()

    if result is None:
        return ChoiceResult(action="none")

    action, value = result

    if action == "scheme":
        return ChoiceResult(action="execute", scheme=schemes[value])

    if action == "custom":
        custom = _custom_scheme_input(console)
        if custom is None:
            # 取消自定义输入，重新回到选择
            return ChoiceResult(action="skip")
        return ChoiceResult(action="custom", scheme=custom)

    if action == "rethink":
        return ChoiceResult(action="rethink")

    return ChoiceResult(action="none")


def _custom_scheme_input(console: Console) -> Optional[Scheme]:
    """用户自定义方案输入"""
    console.print("\n[bold cyan]✏️ 输入你的修复方案：[/bold cyan]")

    name = questionary.text("方案名称（简短）：", qmark="📌").ask()
    if not name:
        return None

    desc = questionary.text("方案描述：", qmark="📝").ask() or ""

    risk = questionary.select(
        "风险等级：",
        choices=[
            questionary.Choice(title="🟢 低（不影响其他功能）", value="低"),
            questionary.Choice(title="🟡 中（可能影响周边功能）", value="中"),
            questionary.Choice(title="🔴 高（架构级变更）", value="高"),
        ],
        qmark="📊",
        default="低",
    ).ask()

    scope = questionary.select(
        "改动范围：",
        choices=[
            questionary.Choice(title="📏 小（1-2 个文件）", value="小"),
            questionary.Choice(title="📐 中（3-5 个文件）", value="中"),
            questionary.Choice(title="🏗️ 大（5+ 文件或架构）", value="大"),
        ],
        qmark="📐",
        default="小",
    ).ask()

    details_input = questionary.text(
        "具体步骤（可选，逗号分隔）：",
        qmark="📋",
        default="",
    ).ask()

    details = [s.strip() for s in details_input.split(",")] if details_input else []

    return Scheme(name=name, description=desc, risk=risk, scope=scope, details=details)
