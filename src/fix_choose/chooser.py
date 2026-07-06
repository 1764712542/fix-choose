"""交互式方案选择器 — 多选按钮：方案A/B/C + 自定义输入"""

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


def _risk_icon(risk: str) -> str:
    return {"低": "🟢", "中": "🟡", "高": "🔴"}.get(risk, "⚪")


def _scope_icon(scope: str) -> str:
    return {"小": "📏", "中": "📐", "大": "🏗️"}.get(scope, "📋")


def _render_schemes_overview(schemes: List[Scheme], console: Console) -> None:
    """一次性展示所有方案"""
    from rich.table import Table
    from rich import box

    table = Table(box=box.ROUNDED, border_style="cyan", title="📋 可选修复方案", title_style="bold cyan")
    table.add_column("#", style="bold", width=4)
    table.add_column("方案名称", style="bold cyan", no_wrap=True)
    table.add_column("风险", justify="center")
    table.add_column("改动", justify="center")
    table.add_column("说明", style="white", max_width=60)

    emojis = ["🔧", "💡", "⭐"]
    for i, s in enumerate(schemes, 1):
        emoji = emojis[i - 1] if i <= len(emojis) else "▫️"
        table.add_row(
            f"{emoji} {i}",
            s.name,
            f"{_risk_icon(s.risk)} {s.risk}",
            f"{_scope_icon(s.scope)} {s.scope}",
            s.description[:60] + ("…" if len(s.description) > 60 else ""),
        )

    console.print()
    console.print(table)
    console.print()


def interactive_loop(schemes: List[Scheme], console: Console) -> Optional[Scheme]:
    """交互式方案选择

    一次性展示所有方案，让用户从 方案A/B/C + "其他" 中选择。
    选"其他"则弹出输入框让用户自定义方案。
    返回选中的 Scheme，全部放弃则返回 None。
    """
    if not schemes:
        return None

    _render_schemes_overview(schemes, console)

    # 构建选项
    choices = []
    emojis = ["🔧", "💡", "⭐"]
    for i, s in enumerate(schemes, 1):
        emoji = emojis[i - 1] if i <= len(emojis) else "▫️"
        risk_icon = _risk_icon(s.risk)
        scope_icon = _scope_icon(s.scope)
        label = f"{emoji} 方案{i}：{s.name}  {risk_icon} {s.risk}  {scope_icon} {s.scope}"
        choices.append(questionary.Choice(title=label, value=("scheme", i - 1)))

    choices.append(questionary.Separator("─" * 40))
    choices.append(questionary.Choice(
        title="✏️ 我来说一个方案（自定义输入）",
        value=("custom", None),
    ))
    choices.append(questionary.Choice(
        title="🚫 都不选，算了",
        value=("none", None),
    ))

    console.print("[dim]按 ↑↓ 方向键选择，回车确认[/dim]")
    result = questionary.select(
        "请选择你想要的方案：",
        choices=choices,
        qmark="🔧",
        use_indicator=True,
        pointer="→",
    ).ask()

    if result is None:
        return None

    action, value = result

    if action == "scheme":
        return schemes[value]

    if action == "custom":
        return _custom_scheme_input(console)

    return None


def _custom_scheme_input(console: Console) -> Optional[Scheme]:
    """用户自定义方案输入"""
    console.print("\n[bold cyan]✏️ 请描述你的修复方案：[/bold cyan]")

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
