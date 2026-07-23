# AI Hedge Fund 架构设计文档

## 概述

本文档描述 AI Hedge Fund 项目的整体架构，核心为 **七大佬辩论系统** —— 七位不同风格的AI投资大佬（Buffett、Graham、Munger、Lynch、Burry、Druckenmiller、Taleb）通过三阶段辩论机制，对 S&P500 等投资标的给出多角度分析和综合建议。

系统特点：
- **7位投资大佬**，覆盖价值/深度价值/质量/GARP/逆向/宏观/反脆弱七大风格
- **三阶段聚焦辩论**：快速投票 → 分歧代表深入辩论 → 最终投票
- **量化预计算**：Python精确计算技术指标（RSI/MACD/MA/BB/ADX等），喂给LLM解释
- **历史记忆系统**：加载最近N次辩论供大佬参考，追踪各大佬预测准确率
- **超时保护**：单次LLM调用超时自动降级，不会因单个大佬卡住整个流程
- **自动估值触发**：根据估值信号自动决定是否辩论及辩论强度

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Hedge Fund 架构图                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   命令行入口   │    │   Web界面    │    │  Python API  │          │
│  │  (CLI)       │    │  (Streamlit) │    │  (库调用)    │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             │                                       │
│                    ┌────────▼────────┐                              │
│                    │   标准接口层     │                              │
│                    │ sp500_timing.py │                              │
│                    └────────┬────────┘                              │
│                             │                                       │
│              ┌──────────────┼──────────────┐                        │
│              │              │              │                         │
│     ┌────────▼───────┐ ┌───▼────┐ ┌───────▼────────┐              │
│     │ 市场数据模块     │ │ 量化   │ │ 历史记忆模块   │              │
│     │ market_data.py │ │ signals│ │ history.py     │              │
│     │ (yfinance+     │ │quant_  │ │ (辩论存档/     │              │
│     │  宏观数据)      │ │signals │ │  准确率追踪)   │              │
│     └────────┬───────┘ └───┬────┘ └───────┬────────┘              │
│              │              │              │                         │
│              └──────────────┼──────────────┘                        │
│                             │                                       │
│                    ┌────────▼────────┐                              │
│                    │  三阶段辩论引擎  │                              │
│                    │  debater.py     │                              │
│                    └────────┬────────┘                              │
│                             │                                       │
│   ┌──────┬──────┬──────┬───┴───┬──────┬──────┬──────┐             │
│   ▼      ▼      ▼      ▼      ▼      ▼      ▼                       │
│ Buffett Graham Munger Lynch Burry Druck-  Taleb                     │
│                          enmiller                                   │
│  价值   深度   质量   GARP  逆向   宏观    反脆弱                    │
│        价值                                                      │
│                    ┌────────▼────────┐                              │
│                    │  LLM 调用层     │                              │
│                    │  llm.py         │                              │
│                    │  (MiMo/OpenAI   │                              │
│                    │   compatible)   │                              │
│                    └─────────────────┘                              │
│                                                                     │
│                    ┌─────────────────┐                              │
│                    │    数据层        │                              │
│                    │ yfinance (美股)  │                              │
│                    │ akshare (A股)   │                              │
│                    └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
ai-hedge-fund/
├── src/
│   ├── main.py                   # 原工程主入口
│   ├── agents/                   # 原工程18个代理（独立模块）
│   │   ├── warren_buffett.py
│   │   ├── charlie_munger.py
│   │   ├── michael_burry.py
│   │   ├── peter_lynch.py
│   │   └── ... (共19个代理文件)
│   ├── tools/                    # 数据工具
│   │   ├── api.py                # 核心API（支持A股）
│   │   ├── a_share_api.py        # A股数据API
│   │   └── a_share_financials.py # A股财务数据
│   ├── debate/                   # ★ 七大佬辩论模块（核心）
│   │   ├── __init__.py           # 模块导出
│   │   ├── agents.py             # 7位大佬角色定义 + 提示词模板
│   │   ├── debater.py            # 三阶段辩论引擎（Phase 1/2/3）
│   │   ├── llm.py                # LLM调用封装（超时支持）
│   │   ├── market_data.py        # 市场数据获取（美股+宏观+量化）
│   │   ├── quant_signals.py      # ★ 量化预计算（技术指标+指数估值）
│   │   ├── history.py            # ★ 辩论历史+记忆+准确率追踪
│   │   └── sp500_timing.py       # S&P500出手时机标准接口
│   ├── data/                     # 数据模型
│   └── backtester.py             # 回测模块
│
├── run_debate.py                 # 辩论入口脚本
├── check_valuation.py            # S&P500估值查询器
├── check_valuation_with_debate.py # 估值+辩论集成
│
├── data/
│   └── debate_history/           # 辩论历史记录存储
│
├── docs/
│   ├── DEPLOY.md                 # 部署文档
│   ├── SP500_TIMING_GUIDE.md     # 操作手册
│   └── ARCHITECTURE.md           # 架构设计（本文档）
│
├── .env.example                  # 环境变量模板
├── pyproject.toml                # Poetry配置
└── poetry.lock                   # 依赖锁文件
```

## 模块详解

### 1. 七大佬投资代理（agents.py — 770行）

定义了七位投资大佬的角色、投资哲学和输出格式。每位大佬拥有完整的思维模型和Few-Shot示例。

| 大佬 | 角色标签 | 投资风格 | 核心关注点 |
|------|---------|---------|-----------|
| **Warren Buffett** | `value` | 价值投资之王 | 护城河、管理层、安全边际、长期持有 |
| **Benjamin Graham** | `deep-value` | 价值投资之父 | Graham Number、安全边际>30%、10年持续盈利 |
| **Charlie Munger** | `skeptic` | 质量投资大师 | 多元思维模型、逆向思考、心理学偏误、太难堆 |
| **Peter Lynch** | `growth` | GARP投资之王 | 公司分类、PEG估值、增长故事、十倍股 |
| **Michael Burry** | `contrarian` | 逆向投资大师 | 市场共识错误、FCF yield、不对称性、尾部风险 |
| **Stanley Druckenmiller** | `macro-momentum` | 宏观对冲大师 | 流动性、央行政策、动量、3:1不对称性 |
| **Nassim Taleb** | `tail-risk` | 反脆弱大师 | 黑天鹅、凸性/凹性、尾部对冲、从波动中获益 |

**提示词模板（4个）：**
- `VOTE_PROMPT_TEMPLATE` — Phase 1 快速投票，含历史记忆 + 目标仓位(0-100%)
- `CHALLENGE_PROMPT_TEMPLATE` — Phase 2 挑战辩论，引用其他大佬观点
- `FINAL_VOTE_PROMPT_TEMPLATE` — Phase 3 最终投票，可改票 + 目标仓位
- `SYNTHESIS_PROMPT` — 主持人综合结论

所有模板都包含 `{current_date}` 防幻觉注入，确保大佬只基于已知信息分析。

```python
# 全部代理列表
ALL_AGENTS = [BUFFETT, GRAHAM, MUNGER, LYNCH, BURRY, DRUCKENMILLER, TALEB]
```

### 2. 三阶段辩论引擎（debater.py — 516行）

核心辩论引擎，实现聚焦的三阶段辩论机制：

```
Phase 1 — Vote:        7位大佬快速投票（7次LLM调用）
                         ↓ 统计 bullish/bearish/neutral 分布
Phase 2 — Challenge:   分歧最大的代表深入辩论（最多4人 × N轮）
                         ↓ 选策略：
                         │ 全票一致 → 跳过Phase 2
                         │ 单一异见 → 异见者 + 最强多数派代表
                         │ 两方对峙(4:3) → 各方最高置信度代表
                         │ 三方分裂 → 各组最高代表
Phase 3 — Final Vote:  所有人看到辩论结果后重新表态（7次LLM调用）
                         ↓ 可改票，给出目标仓位
Synthesis:             主持人综合出最终结论（1次LLM调用）
```

**关键特性：**
- **超时保护**：单次LLM调用默认30秒超时，失败自动重试1次，连续2次失败则禁用该大佬
- **优雅降级**：任何大佬出错不影响整体流程
- **检查点保存**：每个Phase结束自动保存中间状态到磁盘
- **历史记忆**：Phase 1 前加载最近N次辩论记录作为大佬参考
- **表现追踪**：每次新辩论开始时自动更新上一次辩论后SPY涨跌
- **JSON解析容错**：5层容错解析（直接/Markdown/嵌套/截断/情感分析）

**数据结构：**
```python
class DebateRound:      # 单个大佬单次发言
    agent_name, role, signal, confidence, reasoning, phase, target_position

class AgentStatus:      # 大佬健康状态跟踪
    name, successes, failures, last_error, is_disabled

class DebateResult:     # 完整辩论输出
    topic, rounds, consensus, market_data,
    agent_statuses, total_llm_calls, total_time,
    skipped_agents, phase_times, debate_record_id,
    avg_target_position
```

**LLM调用开销：**
- Phase 1: 7次调用（全部大佬）
- Phase 2: 最多 4人 × 2轮 = 8次调用
- Phase 3: 7次调用（全部大佬）
- Synthesis: 1次调用
- **最大总调用数：23次**（最少：全票一致时仅15次）

### 3. 量化预计算模块（quant_signals.py — 425行）

**核心理念：不让LLM猜技术指标，而是用pandas精确计算后作为结构化数据喂给它。**

用 yfinance 拉取 SPY 1年历史数据，计算以下指标：

**均线系统：**
- MA5 / MA20 / MA50 / MA200
- 均线排列判断（多头排列 / 空头排列 / 缠绕）
- 价格相对MA200位置

**动量指标：**
- RSI(14) — 超买(≥70)/超卖(≤30)/中性
- MACD(12,26,9) — 金叉/死叉/零轴位置

**波动率：**
- 布林带(20,2) — 上轨/中轨/下轨位置
- ATR(14) — 波动幅度百分比

**成交量：**
- 20日均量、量比
- 放量/缩量判断

**趋势强度：**
- ADX(14) — 强趋势(≥40)/中等(25-40)/弱趋势(<25)

**指数估值：**
- S&P500 PE(TTM) + 盈利收益率(EY)
- 股权风险溢价(ERP) = EY - 10年期国债收益率
- PE相对历史均值偏离

**综合技术评分：** 基于均线/RSI/MACD/布林带/量价的多空评分

```python
# 入口函数
def format_quant_summary(spy_price: float = 0.0) -> str:
    """获取完整量化摘要（技术指标+指数估值），返回格式化文本"""
```

### 4. 历史记忆系统（history.py — 293行）

辩论历史记录与大佬记忆系统，四个核心功能：

**1. 辩论存档** — 每次辩论自动保存完整记录到JSON文件
```
data/debate_history/
  ├── 2026-07-23_a1b2c3d4.json
  ├── 2026-07-22_e5f6g7h8.json
  └── ...
```

**2. 历史加载** — 读取最近N次辩论，供大佬参考

**3. 记忆注入** — Phase 1投票前把历史上下文注入prompt，包含：
- 历史市场环境（SPY价格/PE/VIX）
- 历史投票分布和结论
- 后续SPY表现（涨跌幅）
- 各大佬历史准确率

**4. 表现追踪** — 辩论后记录SPY涨跌，评估各大佬预测准确率
- 每次新辩论开始时自动更新上一次辩论的 `spy_price_after`
- 根据 `spy_change_pct` 判断各大佬方向是否正确
- 汇总最近20次的准确率统计

```python
class DebateRecord:
    """单次辩论完整记录"""
    id, timestamp, topic,
    spy_price, pe, vix, pos_52w, tnx_10y, valuation_signal,
    votes, vote_distribution,           # Phase 1
    challenge_participants, challenges,  # Phase 2
    final_votes,                        # Phase 3
    consensus, confidence_avg, agreement_points, risks, action_items,
    spy_price_at_debate, spy_price_after, spy_change_pct,
    agent_accuracy, total_time, total_llm_calls

class DebateHistory:
    def save(record) -> Path
    def load_recent(n=3) -> list[DebateRecord]
    def get_agent_stats() -> dict[str, dict]
    def update_performance(current_spy_price)
    def format_memory_context(n=3) -> str
```

### 5. 市场数据模块（market_data.py — 433行）

综合 yfinance（美股）+ akshare（A股）获取市场数据，为辩论提供完整上下文。

**数据获取范围：**

| 类别 | 数据源 | 内容 |
|------|--------|------|
| 美股指数 | yfinance | SPY/QQQ/DIA/IWM 价格、PE、PB、52周区间、均线 |
| 宏观指标 | yfinance | VIX、10Y国债、13W国债(联储利率代理)、5Y国债、30Y国债、DXY、黄金 |
| 收益率曲线 | 计算 | 10Y-3M利差、30Y-10Y期限利差、曲线解读 |
| 个股详情 | yfinance | PE/PB/PEG/ROE/ROA/利润率/D/E/增长/FCF/分析师评级 |
| 近期走势 | yfinance | SPY近10个交易日逐日收盘+成交量 |
| 量化指标 | quant_signals | 技术指标 + 指数估值（自动集成） |

**关键数据结构：**
```python
class IndexSnapshot:     # 指数/ETF快照
    name, price, change_pct, pe, pb, dividend_yield,
    high_52w, low_52w, ma50, ma200, extra

class StockSnapshot:     # 个股详细数据
    ticker, name, price, pe_trailing, pe_forward, pb, peg,
    roe, roa, profit_margin, gross_margin, operating_margin,
    debt_to_equity, current_ratio, revenue_growth, earnings_growth,
    dividend_yield, market_cap, free_cashflow, high_52w, low_52w,
    ma50, ma200, analyst_rating, target_price, num_analysts

class MarketDataBundle:  # 完整市场数据包
    us_indices, cn_indices, macro, stocks,
    recent_trend, timestamp, quant_signals
```

### 6. S&P500出手时机标准接口（sp500_timing.py — 450行）

面向用户的顶层接口，整合估值分析 + 辩论系统。

**估值区间定义：**
```python
VALUATION_BANDS = {
    "pe":       {"cheap": 18, "fair": 22, "expensive": 27},
    "vix_fear": {"cheap": 30, "fair": 25, "expensive": 15},  # 反向
    "pos_52w":  {"cheap": 30, "fair": 50, "expensive": 80},
    "tnx":      {"cheap": 2.5, "fair": 3.5, "expensive": 4.5},
}
```

**自动辩论触发规则：**
- 🟢 强烈买入（≥3项便宜）→ 标准辩论（2轮）
- 🟢 可分批买（≥2项便宜）→ 标准辩论（2轮）
- 🔴 不建议买入（≥3项贵）→ 标准辩论（2轮）
- 🟠 偏贵观望（≥2项贵）→ 轻量辩论（1轮）
- 🟡 中性 → 不辩论

**最终信号计算：** 估值信号分数(0-2) + 辩论分数(0-2) = 综合判断

**输出：** `TimingResult` 包含估值指标、辩论结论、平均目标仓位、行动建议、完整报告

### 7. LLM调用层（llm.py — 58行）

OpenAI-compatible API 封装，支持所有兼容 OpenAI 接口的模型。

```python
class MiMoLLM:
    """LLM客户端，默认使用MiMo-v2.5模型"""
    def __init__(self, model=None, base_url=None, api_key=None,
                 temperature=0.7, max_tokens=4096, timeout=30.0):
    def complete(self, system: str, user: str) -> str:
        """调用LLM，支持超时和连接错误处理"""
```

**配置项：**
- `OPENAI_API_KEY` — API密钥
- `OPENAI_API_BASE` — API基础URL（支持自定义端点）
- `OPENAI_API_MODEL` — 模型名称（默认 mimo-v2.5）
- `timeout` — 单次调用超时秒数（默认30）

## 数据流

### 完整流程（Phase 1/2/3）

```
┌─────────────────┐
│   用户请求       │  check_sp500_timing() / CLI / API
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  获取市场数据     │  market_data.py
│  ├─ yfinance    │  SPY/QQQ/DIA/IWM + VIX/国债/DXY/黄金
│  ├─ 宏观指标    │  13W/5Y/10Y/30Y国债, 收益率曲线
│  └─ 量化指标    │  quant_signals.py: RSI/MACD/MA/BB/ADX + ERP
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  估值信号判断     │  sp500_timing.py
│  PE/VIX/52周位置  │  4项指标 → 🟢便宜 🟡合理 🟠偏贵 🔴极贵
│  /10Y国债        │
└────────┬────────┘
         │
         ├──── 🟡中性 → 不辩论 → 直接输出估值结论
         │
         └──── 非中性 → 触发辩论 ─────────────────┐
                                                   │
         ┌─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  加载历史记忆     │  history.py: 最近N次辩论 + 各大佬准确率
└────────┬────────┘
         │
         ▼
┌═══════════════════════════════════════════════════┐
║  Phase 1 — VOTE（快速投票）                        ║
║  7位大佬独立投票 → bullish/bearish/neutral + 仓位   ║
║  7次LLM调用                                       ║
╚════════════════════╤══════════════════════════════╝
                     │
                     ▼
         ┌────────────────────┐
         │  统计投票分布        │
         │  全票一致？         │
         └────┬───────────┬───┘
              │           │
              │ 一致      │ 有分歧
              │           │
              ▼           ▼
         跳过Phase 2  ┌══════════════════════════════════════┐
                      ║  Phase 2 — CHALLENGE（聚焦辩论）      ║
                      ║  选代表：少数派最高置信 + 多数派最强防守  ║
                      ║  最多4人 × N轮深入辩论                  ║
                      ║  最多8次LLM调用                        ║
                      ╚═════════════════╤════════════════════╝
                                        │
         ┌──────────────────────────────┘
         │
         ▼
┌═══════════════════════════════════════════════════┐
║  Phase 3 — FINAL VOTE（最终投票）                  ║
║  所有人看到辩论结果后重新表态（可改票）              ║
║  7次LLM调用                                       ║
╚══════════════════╤══════════════════════════════╝
                   │
                   ▼
┌═══════════════════════════════════════════════════┐
║  SYNTHESIS（综合结论）                             ║
║  主持人综合共识/分歧/风险/行动建议                   ║
║  1次LLM调用                                       ║
╚══════════════════╤══════════════════════════════╝
                   │
                   ▼
┌─────────────────┐
│  保存辩论历史    │  history.py → data/debate_history/*.json
│  更新表现追踪    │  计算上一次辩论后SPY涨跌
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  综合估值+辩论   │  估值分数 + 辩论分数 = 最终信号
│  生成报告       │  包含目标仓位/行动建议/基金操作指南
└─────────────────┘
```

## 依赖关系

### 内部模块依赖

```
sp500_timing.py（标准接口）
    ├── market_data.py（市场数据）
    │       ├── yfinance（美股数据）
    │       ├── akshare（A股数据）
    │       └── quant_signals.py（量化预计算）
    │               ├── yfinance（历史数据）
    │               └── pandas/numpy（技术指标计算）
    ├── debater.py（辩论引擎）
    │       ├── agents.py（7位大佬 + 提示词模板）
    │       ├── llm.py（LLM调用）
    │       └── history.py（历史记忆）
    └── agents.py（ALL_AGENTS 列表）

market_data.py
    └── quant_signals.py（自动调用format_quant_summary）

debater.py
    ├── agents.py（VOTE/CHALLENGE/FINAL_VOTE/SYNTHESIS模板）
    ├── llm.py（MiMoLLM）
    └── history.py（DebateHistory, record_from_debate_result）
```

### 外部依赖

| 依赖包 | 用途 | 使用模块 |
|--------|------|---------|
| yfinance | 美股数据获取 | market_data, quant_signals |
| akshare | A股数据获取 | market_data |
| openai | LLM API调用 | llm.py |
| pandas | 数据处理 + 技术指标 | quant_signals |
| numpy | 数值计算 | quant_signals |
| python-dotenv | 环境变量管理 | sp500_timing |

## 配置管理

### 环境变量

| 变量名 | 必需 | 说明 | 默认值 |
|--------|------|------|--------|
| OPENAI_API_KEY | 是 | LLM API密钥 | — |
| OPENAI_API_BASE | 否 | API基础URL | — |
| OPENAI_API_MODEL | 否 | 模型名称 | mimo-v2.5 |
| FINANCIAL_DATASETS_API_KEY | 否 | 美股财务数据API | — |
| USE_A_SHARE_DB | 否 | 启用A股数据库 | true |
| A_SHARE_DB_PATH | 否 | A股数据库路径 | — |

### 配置文件

- `.env`：环境变量（不提交到git）
- `pyproject.toml`：Poetry依赖配置
- `poetry.lock`：依赖版本锁定

### 运行时参数

```python
# check_sp500_timing() 参数
debate_rounds: int = 2          # 辩论轮数（Phase 2的挑战轮数）
stock_tickers: list[str] | None  # 个股代码（可选）
topic: str                       # 辩论主题
force_debate: bool = False       # 强制辩论（即使估值中性）
call_timeout: float = 30.0       # LLM单次调用超时秒数
```

## 扩展指南

### 添加新的投资大佬

**Step 1：在 `src/debate/agents.py` 中定义新的 Agent**

```python
NEW_AGENT = Agent(
    name="投资人姓名",
    role="role_label",  # 如 "momentum", "quant", "macro" 等
    system_prompt="""你是XXX，...

═══ 核心投资哲学 ═══
1. ...
2. ...

═══ 思维模型 ═══
【Step 1: ...】
...

═══ 信号判断规则 ═══
- Bullish: ...
- Bearish: ...
- Neutral: ...

═══ 语言风格 ═══
- ...

═══ Few-Shot示例 ═══
...

═══ 输出格式 ═══
{
  "signal": "bullish" | "bearish" | "neutral",
  "confidence": 0-100,
  "reasoning": "用XXX的风格..."
}"""
)
```

**Step 2：添加到 `ALL_AGENTS` 列表**

```python
ALL_AGENTS = [BUFFETT, GRAHAM, MUNGER, LYNCH, BURRY, DRUCKENMILLER, TALEB, NEW_AGENT]
```

**Step 3（可选）：在 `run_debate.py` 中添加映射**

```python
AGENT_MAP["new_investor"] = NEW_AGENT
```

**注意事项：**
- 添加大佬会增加 Phase 1 和 Phase 3 的LLM调用次数（各+1次）
- Phase 2 的参与人数上限为4人，不受大佬总数影响
- 建议不超过10位大佬，避免辩论时间过长

### 添加新的量化指标

在 `src/debate/quant_signals.py` 中：

```python
@dataclass
class TechSignals:
    # ... 现有字段 ...
    new_metric: float = 0.0
    new_metric_signal: str = ""

def calculate_tech_signals(spy_price: float = 0.0) -> TechSignals:
    # ... 现有计算 ...
    # 添加新指标计算
    signals.new_metric = ...
    signals.new_metric_signal = ...
    return signals

def to_text(self) -> str:
    # ... 现有输出 ...
    lines.append(f"  新指标: {self.new_metric:.2f} → {self.new_metric_signal}")
```

### 添加新的数据源

在 `src/debate/market_data.py` 中：

```python
def fetch_new_data_source() -> list[IndexSnapshot]:
    """获取新数据源"""
    # 实现数据获取逻辑
    pass

def get_market_data(...) -> MarketDataBundle:
    # ... 现有获取 ...
    new_indices = fetch_new_data_source()
    bundle.us_indices.extend(new_indices)
    return bundle
```

### 添加新的估值指标

在 `src/debate/sp500_timing.py` 中：

```python
VALUATION_BANDS["new_metric"] = {"cheap": 0, "fair": 50, "expensive": 100}

def get_overall_signal(pe, vix, pos, tnx, new_metric=None):
    # ... 现有逻辑 ...
    if new_metric is not None:
        signals.append("cheap" if new_metric <= 50 else "expensive" if new_metric >= 100 else "fair")
```

## 性能特征

### LLM调用统计

| 场景 | Phase 1 | Phase 2 | Phase 3 | Synthesis | 总计 |
|------|---------|---------|---------|-----------|------|
| 全票一致 | 7 | 0 (跳过) | 7 | 1 | **15** |
| 标准辩论(2轮) | 7 | 8 | 7 | 1 | **23** |
| 轻量辩论(1轮) | 7 | 4 | 7 | 1 | **19** |

### 超时与容错

- 单次LLM调用超时：默认30秒（可通过 `call_timeout` 参数调整）
- 自动重试：1次
- 禁用阈值：连续2次失败后禁用该大佬
- 最坏情况（7个大佬全部超时）：23 × 30秒 = 11.5分钟
- 正常情况：约2-5分钟完成全部辩论

### 历史记忆

- 默认加载最近3次辩论记录（可通过 `memory_rounds` 调整）
- 准确率统计基于最近20次有后续数据的辩论
- 历史存储路径：`data/debate_history/`（JSON格式）

## 后续规划

### 已完成
- [x] 七位投资大佬（Buffett/Graham/Munger/Lynch/Burry/Druckenmiller/Taleb）
- [x] 三阶段聚焦辩论机制（Vote → Challenge → Final Vote）
- [x] 量化预计算模块（技术指标 + 指数估值）
- [x] 历史记忆系统（辩论存档 + 准确率追踪 + 记忆注入）
- [x] 超时保护 + 优雅降级
- [x] 检查点保存
- [x] 防幻觉（current_date注入）
- [x] 目标仓位输出（0-100%）
- [x] 收益率曲线分析（10Y-3M利差 / 30Y-10Y期限利差）
- [x] 完善项目文档
