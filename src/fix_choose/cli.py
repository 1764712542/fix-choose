"""fix-choose CLI 入口 — 交互式修复方案选择器"""

import sys
from pathlib import Path

import click

from .chooser import interactive_loop, Scheme
from .config import load_config
from .analyzer import analyze_with_ai
from .executor import apply_scheme


def _print_banner():
    """打印启动横幅"""
    from rich.console import Console
    from rich.panel import Panel
    from rich import box

    console = Console()
    console.print()
    console.print(
        Panel(
            "[bold cyan]🛠 fix-choose[/bold cyan]  —  交互式修复方案选择器",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()


@click.group()
@click.version_option(prog_name="fix-choose")
def main():
    """🛠 fix-choose — 交互式修复方案选择工具

    调试时自动分析根因 → 提出多个方案 → 用 Yes/No 按钮选择 → 自动执行。
    """
    pass


@main.command()
def init():
    """⚙ 初始化配置文件（交互式）"""
    from .config import init_config
    init_config()


@main.command()
@click.argument("target", required=False, default="")
@click.option("-m", "--model", help="AI 模型名称（覆盖配置文件）")
@click.option("--api-key", help="API Key（覆盖配置文件）")
@click.option("--api-url", help="API 地址（覆盖配置文件）")
@click.option("--diff", is_flag=True, help="使用 git diff 作为分析输入")
def analyze(target, model, api_key, api_url, diff):
    """🔍 分析代码问题 → 提方案 → 交互式选择 → 执行

    TARGET 可以是：文件路径、错误信息、或留空（读取剪贴板 / git diff）
    """
    _print_banner()

    config = load_config()
    if model:
        config["model"] = model
    if api_key:
        config["api_key"] = api_key
    if api_url:
        config["api_url"] = api_url

    # 收集分析输入
    input_text = _collect_input(target, diff)

    if not input_text:
        from rich.console import Console
        console = Console()
        console.print("[yellow]⚠ 未提供分析目标。请输入问题描述或代码路径：[/yellow]")
        input_text = sys.stdin.read().strip()
        if not input_text:
            console.print("[red]✗ 没有输入，退出。[/red]")
            sys.exit(1)

    # AI 分析
    from rich.console import Console
    console = Console()
    console.print("\n[cyan]🔍 正在分析问题...[/cyan]")
    console.print("[dim]调用 AI 分析根因并生成修复方案...[/dim]\n")

    result = analyze_with_ai(input_text, config)

    if not result or "root_cause" not in result:
        console.print("[red]✗ AI 分析失败，请检查 API 配置或稍后重试。[/red]")
        sys.exit(1)

    # 显示根因
    console.rule("[bold yellow]📋 根因分析")
    console.print(f"\n[white]{result['root_cause']}[/white]\n")

    schemes = result.get("schemes", [])
    if not schemes:
        console.print("[red]✗ AI 未能生成修复方案。[/red]")
        sys.exit(1)

    # 交互式选择循环
    chosen = interactive_loop(schemes, console)

    if chosen is None:
        console.print("\n[yellow]已尝试所有方案，均已拒绝。请补充更多信息后重试。[/yellow]")
        sys.exit(0)

    # 执行
    console.rule("[bold green]✅ 开始执行修复")
    apply_scheme(chosen, console)


@main.command()
@click.option("-a", "--scheme-a", multiple=True, help='方案A，格式："方案名: 描述"')
@click.option("-b", "--scheme-b", multiple=True, help='方案B，格式："方案名: 描述"')
@click.option("-c", "--scheme-c", multiple=True, help='方案C，格式："方案名: 描述"')
@click.option("--json", "json_output", is_flag=True, help="JSON 输出模式（供 Claude Code 自动解析）")
@click.argument("extra_schemes", nargs=-1)
def pick(scheme_a, scheme_b, scheme_c, json_output, extra_schemes):
    """🎯 辅助模式：手动输入方案，只做交互式选择

    配合 Claude Code / OpenCode 使用：把它们分析出的方案输入本工具做选择。

    示例：

        fix-choose pick \\
          -a "加索引: 在 orders 表加联合索引" \\
          -b "异步查询: 用 asyncio 并发执行" \\
          -c "加缓存: 用 Redis 缓存结果"
    """
    if not json_output:
        _print_banner()

    from rich.console import Console
    console = Console()

    # 解析方案
    schemes = []
    for group in [scheme_a, scheme_b, scheme_c]:
        for item in group:
            if ":" in item:
                name, desc = item.split(":", 1)
                schemes.append(Scheme(name=name.strip(), description=desc.strip(), risk="?", scope="?"))
            else:
                schemes.append(Scheme(name=item.strip(), description="", risk="?", scope="?"))

    for item in extra_schemes:
        if ":" in item:
            name, desc = item.split(":", 1)
            schemes.append(Scheme(name=name.strip(), description=desc.strip(), risk="?", scope="?"))
        else:
            schemes.append(Scheme(name=item.strip(), description="", risk="?", scope="?"))

    if not schemes:
        console.print("[yellow]⚠ 未提供任何方案。用法见 fix-choose pick --help[/yellow]")
        sys.exit(1)

    # 显示方案概览
    console.print(f"\n[cyan]共收到 {len(schemes)} 个方案，开始交互式选择...[/cyan]\n")

    chosen = interactive_loop(schemes, console)

    if chosen is None:
        if json_output:
            import json as _json
            print(_json.dumps({"selected": None, "reason": "all_rejected"}, ensure_ascii=False))
        else:
            console.print("\n[yellow]已尝试所有方案，均已拒绝。[/yellow]")
        sys.exit(0)

    if json_output:
        import json as _json
        print(_json.dumps({
            "selected": chosen.name,
            "description": chosen.description,
            "risk": chosen.risk,
            "scope": chosen.scope,
        }, ensure_ascii=False))
    else:
        console.rule("[bold green]✅ 选择结果")
        print(f"[SELECTED] {chosen.name}")
        console.print(f"\n选中的方案：[bold cyan]{chosen.name}[/bold cyan]")
        console.print(f"方案描述：[white]{chosen.description}[/white]")
        console.print(f"\n[dim]提示：将方案名告知 Claude Code 即可执行。[/dim]")


@main.command()
@click.option("-m", "--model", help="AI 模型名称")
@click.option("--diff", is_flag=True, default=True, help="审查 git diff（默认）")
@click.option("--files", help="指定文件路径（逗号分隔）")
def review(model, diff, files):
    """📝 代码审查模式：审查 git diff 并交互式选择修复方案"""
    _print_banner()

    from rich.console import Console
    console = Console()
    config = load_config()
    if model:
        config["model"] = model

    # 获取审查输入
    input_text = ""
    if files:
        for fp in files.split(","):
            fp = fp.strip()
            if Path(fp).exists():
                input_text += f"\n--- {fp} ---\n" + Path(fp).read_text()
    else:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True, text=True, timeout=10
            )
            input_text = result.stdout
            if not input_text:
                result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True, text=True, timeout=10
                )
                input_text = result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            console.print("[red]✗ 无法获取 git diff，请确保在 git 仓库中运行。[/red]")
            sys.exit(1)

    if not input_text:
        console.print("[yellow]⚠ 没有变更需要审查。[/yellow]")
        sys.exit(1)

    console.print(f"[cyan]📄 获取到 {len(input_text)} 字符的 diff[/cyan]")
    console.print("[cyan]🔍 正在分析...[/cyan]\n")

    result = analyze_with_ai(
        f"请审查以下代码变更并给出修复方案：\n\n{input_text}",
        config,
        system_override="你是一个代码审查专家。分析以下代码变更中的问题，"
        "给出根因和最多3个不同的修复方案。"
    )

    if not result or "root_cause" not in result:
        console.print("[red]✗ 分析失败。[/red]")
        sys.exit(1)

    console.rule("[bold yellow]📋 审查结果")
    console.print(f"\n[white]{result['root_cause']}[/white]\n")

    schemes = result.get("schemes", [])
    if not schemes:
        console.print("[red]✗ 未能生成方案。[/red]")
        sys.exit(1)

    chosen = interactive_loop(schemes, console)

    if chosen is None:
        console.print("\n[yellow]已尝试所有方案。[/yellow]")
        sys.exit(0)

    console.rule("[bold green]✅ 开始执行修复")
    apply_scheme(chosen, console)


def _collect_input(target: str, use_diff: bool) -> str:
    """收集分析输入"""
    from pathlib import Path

    if use_diff:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True, text=True, timeout=10
            )
            text = result.stdout
            if not text:
                result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True, text=True, timeout=10
                )
                text = result.stdout
            if text:
                return f"代码变更 diff：\n{text}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    if target:
        path = Path(target)
        if path.exists():
            return f"文件 {target} 的内容：\n```\n{path.read_text()}\n```\n请分析这段代码中的 Bug 或改进点。"
        else:
            return target  # 当作错误信息处理

    return ""
