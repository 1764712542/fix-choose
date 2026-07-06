# 🛠 fix-choose — 交互式修复方案选择器

调试时自动分析根因 → 提出多个方案 → **用 Yes/No 按钮选择** → 自动执行。

> 配合 Claude Code / OpenCode / 任何 AI 编码助手使用，或者独立使用！

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🔍 **analyze** | 自动分析代码/错误 → 提方案 → Yes/No 选择 → 执行 |
| 🎯 **pick** | 辅助模式：手动输入方案，只用交互式选择器 |
| 👁️ **review** | 审查 git diff → 交互式选择修复方案 |
| ⚙ **init** | 交互式配置初始化 |

## 🖥 交互界面

```
🔧 方案 (1/3)
┌──────────────────────────────────────┐
│  方案A: 加联合索引                    │
│                                      │
│  在 orders 表加 (user_id, order_id)   │
│  联合索引，消除全表扫描                │
│                                      │
## 🖥 交互界面

```
📋 可选修复方案
┌────┬────────┬──────┬──────┬──────────────┐
│ #  │ 方案名  │ 风险  │ 改动  │ 说明         │
├────┼────────┼──────┼──────┼──────────────┤
│ 🔧 │ 加索引  │ 🟢低 │ 📏小 │ 加联合索引   │
│ 💡 │ 异步    │ 🟡中 │ 📐中 │ 异步并发     │
│ ⭐ │ 缓存    │ 🟢低 │ 🏗️大 │ Redis 缓存   │
└────┴────────┴──────┴──────┴──────────────┘

🔧 请选择你想要的方案： (↑↓ 方向键，回车确认)
  → 🔧 方案1：加索引  🟢 低  📏 小
    💡 方案2：异步    🟡 中  📐 中
    ⭐ 方案3：缓存    🟢 低  🏗️ 大
    ──────────────────────────────────────
    ✏️ 我来说一个方案（自定义输入）
    🚫 都不选，算了
```

选 **✏️ 我来说一个方案** 后弹出输入框，填写方案名称 → 描述 → 风险 → 改动 → 步骤。

---

## 📦 安装

### 方式一：pip 安装

```bash
pip install fix-choose
```

### 方式二：uv 安装（推荐）

```bash
uv tool install fix-choose
# 或直接运行不安装
uvx fix-choose
```

### 方式三：源码运行

```bash
git clone <repo>
cd fix-choose
pip install -e .
```

---

## 🔧 配置

使用前需配置 AI API：

### 方式一：交互式配置

```bash
fix-choose init
```

### 方式二：环境变量

```bash
export FIX_CHOOSE_API_KEY=your_api_key
export FIX_CHOOSE_API_URL=https://openrouter.ai/api/v1/chat/completions
export FIX_CHOOSE_MODEL=google/gemini-2.0-flash-001
```

### 方式三：配置文件

创建 `~/.fix-choose/config.yaml`：

```yaml
api_key: your_api_key
api_url: https://openrouter.ai/api/v1/chat/completions
model: google/gemini-2.0-flash-001
```

### 支持的 API

| API | 地址 | 推荐模型 |
|-----|------|---------|
| OpenRouter | https://openrouter.ai/api/v1/chat/completions | google/gemini-2.0-flash-001 |
| DeepSeek | https://api.deepseek.com/v1/chat/completions | deepseek-chat |
| OpenAI | https://api.openai.com/v1/chat/completions | gpt-4o-mini |
| 自定义 | 任意 OpenAI 兼容接口 | — |

---

## 🚀 使用示例

### 分析代码问题

```bash
# 分析文件
fix-choose analyze app.py

# 分析错误信息
fix-choose analyze "IndexError: list index out of range at line 45"

# 分析 git diff（当前变更）
fix-choose analyze --diff
```

### 配合 Claude Code 使用（pick 模式）

在 Claude Code 中分析完问题后，它会给你几个方案。这时运行：

```bash
fix-choose pick \
  -a "加索引: 在 orders 表加 (user_id, order_id) 联合索引, 风险低, 改动小" \
  -b "异步查询: 用 asyncio + aiosqlite 并发执行所有查询, 风险中, 改动中" \
  -c "缓存层: 用 Redis 缓存热点查询结果, 风险低, 改动大"
```

然后用方向键选择方案，回车确认。

### 审查代码变更

```bash
fix-choose review          # 审查当前 git diff
```

---

## 🔄 与 Claude Code 配合的最佳实践

1. **在 CLAUDE.md 中加规则**（已存在于你的配置中）

```markdown
## ── Interactive Debug: Yes/No 方案选择循环 ──
- 分析完成后，建议用户用 fix-choose 做方案选择
- 每个方案标注风险等级和改动范围
```

2. **工作流**

```
你：Claude，帮我分析这个 Bug
Claude：根因是 XXX，建议方案：
       方案A：加索引（低风险，小改动）
       方案B：异步查询（中风险，中改动）
       方案C：加缓存（低风险，大改动）

你：fix-choose pick -a "加索引: ..." -b "异步: ..." -c "缓存: ..."
    → 交互式选择方案B

你：Claude，按方案B执行（异步查询）
```

---

## 🗺 项目结构

```
fix-choose/
├── pyproject.toml           # 项目配置
├── README.md                # 使用文档
├── src/
│   └── fix_choose/
│       ├── __init__.py      # 版本信息
│       ├── __main__.py      # python -m 入口
│       ├── cli.py           # CLI 命令定义
│       ├── chooser.py       # 交互式选择器核心
│       ├── analyzer.py      # AI 分析模块
│       ├── config.py        # 配置管理
│       └── executor.py      # 方案执行
```

---

## 📝 许可证

MIT
