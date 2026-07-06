"""方案执行模块 — 执行选中的修复方案"""

import subprocess
from pathlib import Path
from typing import List

from rich.console import Console

from .chooser import Scheme


def apply_scheme(scheme: Scheme, console: Console) -> None:
    """执行选中的修复方案

    根据方案内容决定执行方式：
    - 如果有具体文件修改命令，执行文件修改
    - 否则输出方案详情供用户手动执行
    """
    console.print(f"\n开始执行: [bold cyan]{scheme.name}[/bold cyan]\n")

    if scheme.details:
        console.print("[bold]执行步骤：[/bold]")
        for i, step in enumerate(scheme.details, 1):
            console.print(f"  {i}. {step}")
        console.print()

    # 交互确认是否自动执行
    import questionary
    auto_exec = questionary.confirm(
        "是否自动执行上述步骤？（需要 git 仓库）",
        default=False,
    ).ask()

    if auto_exec:
        _auto_execute(scheme, console)
    else:
        _manual_guide(scheme, console)


def _auto_execute(scheme: Scheme, console: Console) -> None:
    """自动执行方案"""
    console.print("[cyan]自动执行模式...[/cyan]")

    # 检查是否在 git 仓库
    try:
        subprocess.run(["git", "status"], capture_output=True, check=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        console.print("[yellow]⚠ 不在 git 仓库中，切换到手动模式。[/yellow]")
        _manual_guide(scheme, console)
        return

    results = []
    for step in scheme.details:
        # 尝试识别 git 操作
        if step.startswith("git ") or step.startswith("patch ") or step.startswith("sed "):
            console.print(f"  [dim]→ {step}[/dim]")
            try:
                result = subprocess.run(
                    step.split(),
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    results.append((step, True, result.stdout[:200]))
                    console.print(f"    [green]✓ 成功[/green]")
                else:
                    results.append((step, False, result.stderr[:200]))
                    console.print(f"    [red]✗ 失败: {result.stderr[:100]}[/red]")
            except Exception as e:
                results.append((step, False, str(e)))
                console.print(f"    [red]✗ 错误: {e}[/red]")
        else:
            console.print(f"  [dim]⏭ 跳过（无法自动执行）: {step}[/dim]")
            results.append((step, None, "手动步骤"))

    # 报告
    console.rule("[bold]📊 执行结果")
    success_count = sum(1 for _, ok, _ in results if ok is True)
    fail_count = sum(1 for _, ok, _ in results if ok is False)
    if fail_count == 0:
        console.print(f"\n[green]✅ 执行完成！{success_count}/{len(results)} 步成功[/green]")
    else:
        console.print(f"\n[yellow]⚠ 完成，{fail_count} 步失败，请手动检查。[/yellow]")


def _manual_guide(scheme: Scheme, console: Console) -> None:
    """手动执行指引"""
    from rich.table import Table
    from rich import box

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("步骤", style="bold cyan")
    table.add_column("操作", style="white")

    for i, step in enumerate(scheme.details, 1):
        table.add_row(str(i), step)

    console.print(table)
    console.print(f"\n[bold green]📋 方案: {scheme.name}[/bold green]")
    console.print(f"[white]{scheme.description}[/white]")
    console.print("\n[dim]💡 将上述步骤告知 Claude Code 或手动执行即可。[/dim]")
