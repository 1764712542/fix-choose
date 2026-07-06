"""配置管理 — 加载 ~/.fix-choose/config.yaml 和环境变量"""

import os
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "model": "google/gemini-2.0-flash-001",
    "api_key": "",
}

CONFIG_PATH = Path.home() / ".fix-choose" / "config.yaml"


def _ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """加载配置，优先级：环境变量 > 配置文件 > 默认值"""
    config = dict(DEFAULT_CONFIG)

    # 加载配置文件
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                file_config = yaml.safe_load(f)
            if file_config:
                config.update(file_config)
        except Exception:
            pass

    # 环境变量覆盖
    env_map = {
        "FIX_CHOOSE_API_KEY": "api_key",
        "FIX_CHOOSE_API_URL": "api_url",
        "FIX_CHOOSE_MODEL": "model",
    }
    for env_var, config_key in env_map.items():
        val = os.environ.get(env_var)
        if val:
            config[config_key] = val

    return config


def init_config():
    """初始化配置文件（交互式）"""
    from rich.console import Console
    from rich.panel import Panel
    import questionary

    console = Console()
    console.print(Panel(
        "[bold cyan]fix-choose 配置初始化[/bold cyan]\n\n"
        "需要配置 AI API 才能自动分析代码问题。\n"
        "支持：OpenRouter、DeepSeek、OpenAI 等兼容接口。",
        border_style="cyan",
    ))

    _ensure_config_dir()

    # 如果已有配置文件，询问是否覆盖
    if CONFIG_PATH.exists():
        overwrite = questionary.confirm("配置文件已存在，是否覆盖？", default=False).ask()
        if not overwrite:
            console.print("[yellow]保留现有配置。[/yellow]")
            return

    # 收集配置
    api_url = questionary.text(
        "API 地址（OpenAI 兼容格式）：",
        default="https://openrouter.ai/api/v1/chat/completions",
    ).ask()

    model = questionary.text(
        "默认模型：",
        default="google/gemini-2.0-flash-001",
    ).ask()

    api_key = questionary.password(
        "API Key：",
    ).ask()

    config = {
        "api_url": api_url,
        "model": model,
        "api_key": api_key,
    }

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    console.print(f"\n[green]✅ 配置文件已保存到 {CONFIG_PATH}[/green]")
    console.print("\n[dim]提示：你也可以通过环境变量设置：")
    console.print("  export FIX_CHOOSE_API_KEY=your_key")
    console.print("  export FIX_CHOOSE_API_URL=your_url")
    console.print("  export FIX_CHOOSE_MODEL=model_name[/dim]")
