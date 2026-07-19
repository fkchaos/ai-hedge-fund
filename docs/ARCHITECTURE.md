# AI Hedge Fund 架构设计文档

## 概述

本文档描述AI Hedge Fund项目的整体架构，包括：
- 原工程架构（virattt/ai-hedge-fund）
- 新增功能模块（A股支持、四大佬辩论、S&P500估值分析）
- 代码结构和依赖关系

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Hedge Fund 架构图                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   命令行入口   │    │   Web界面    │    │  Python API  │  │
│  │  (CLI)       │    │  (Streamlit) │    │  (库调用)    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│                    ┌────────▼────────┐                     │
│                    │   核心调度模块    │                     │
│                    │  (src/main.py)  │                     │
│                    └────────┬────────┘                     │
│                             │                              │
│         ┌───────────────────┼───────────────────┐          │
│         │                   │                   │          │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐  │
│  │  原工程代理   │    │  新增辩论模块  │    │  估值分析模块  │  │
│  │ (18个大佬)   │    │  (4个大佬)    │    │  (S&P500)    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│                    ┌────────▼────────┐                     │
│                    │    数据层        │                     │
│                    │ (yfinance/akshare│                    │
│                    │  /本地数据库)    │                     │
│                    └─────────────────┘                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
ai-hedge-fund/
├── src/                          # 原工程核心代码
│   ├── main.py                   # 原工程主入口
│   ├── agents/                   # 原工程18个代理
│   │   ├── warren_buffett.py
│   │   ├── charlie_munger.py
│   │   ├── michael_burry.py
│   │   ├── peter_lynch.py
│   │   └── ... (共19个代理文件)
│   ├── tools/                    # 数据工具
│   │   ├── api.py                # 核心API（已修改，支持A股）
│   │   ├── a_share_api.py        # [新增] A股数据API
│   │   └── a_share_financials.py # [新增] A股财务数据
│   ├── debate/                   # [新增] 辩论模块
│   │   ├── sp500_timing.py       # S&P500出手时机标准接口
│   │   ├── market_data.py        # 市场数据获取
│   │   ├── agents.py             # 四大佬角色定义
│   │   ├── debater.py            # 辩论引擎
│   │   └── llm.py                # LLM调用封装
│   ├── data/                     # 数据模型
│   └── backtester.py             # 回测模块
│
├── [新增] 根目录脚本
│   ├── check_valuation.py        # S&P500估值查询器
│   ├── check_valuation_with_debate.py  # 估值+辩论集成
│   ├── run_debate.py             # 辩论入口脚本
│   ├── run_a_share.py            # A股分析脚本
│   └── run_holdings.py           # 持仓分析脚本
│
├── docs/                         # [新增] 文档目录
│   ├── DEPLOY.md                 # 部署文档
│   ├── SP500_TIMING_GUIDE.md     # 操作手册
│   └── ARCHITECTURE.md           # 架构设计（本文档）
│
├── .env.example                  # 环境变量模板
├── pyproject.toml                # Poetry配置（已修改）
└── poetry.lock                   # 依赖锁文件（已修改）
```

## 模块详解

### 1. 原工程模块（src/）

#### 1.1 核心调度（src/main.py）
- **功能**：原工程主入口，协调18个代理进行投资决策
- **输入**：股票代码列表、日期范围
- **输出**：买入/卖出/持有决策

#### 1.2 代理模块（src/agents/）
**18个AI投资大佬代理：**

| 代理 | 投资风格 | 关注点 |
|------|---------|--------|
| Warren Buffett | 价值投资 | 护城河、管理层、估值 |
| Charlie Munger | 质量投资 | 逆向思维、安全边际 |
| Michael Burry | 逆向投资 | 拥挤交易、风险定价 |
| Peter Lynch | GARP投资 | 成长性、PEG |
| Ben Graham | 价值投资 | 安全边际、隐藏宝石 |
| Cathie Wood | 成长投资 | 创新、颠覆性技术 |
| Bill Ackman | 激进投资 | 主动参与、大胆持仓 |
| ... | ... | ... |

#### 1.3 数据工具（src/tools/）
- **api.py**（已修改）：核心数据获取，支持A股数据库
- **a_share_api.py**（新增）：A股数据API封装
- **a_share_financials.py**（新增）：A股财务数据获取

### 2. 新增辩论模块（src/debate/）

#### 2.1 标准接口（sp500_timing.py）
```python
# 核心函数
def check_sp500_timing(
    debate_rounds: int = 2,
    stock_tickers: list[str] | None = None,
    topic: str = "当前市场环境下，是否应该投资S&P500?",
    force_debate: bool = False,
) -> TimingResult:
    """
    四大佬辩论判断S&P500出手时机
    
    Returns:
        TimingResult: 包含估值信号、辩论结论、行动建议
    """
```

**返回结构（TimingResult）：**
- 估值指标（PE/VIX/52周位置/10Y国债）
- 估值信号（🟢便宜/🟡合理/🟠偏贵/🔴极贵）
- 辩论结论（共识/置信度/风险/建议）
- 综合判断（最终信号+行动建议）

#### 2.2 市场数据（market_data.py）
**数据源：**
- yfinance：美股（SPY/QQQ/VIX/^TNX）
- akshare：A股（上证/沪深300/创业板）

**输出结构（MarketDataBundle）：**
- us_indices：美股指数/ETF数据
- cn_indices：A股指数数据
- macro：宏观指标（VIX/国债/黄金/美元）
- stocks：个股详细数据

#### 2.3 辩论引擎（debater.py）
**辩论流程：**
1. 初始轮：每位大佬独立给出观点
2. 挑战轮：大佬们互相挑战和回应
3. 综合结论：主持人总结共识和分歧

**四大佬角色（agents.py）：**
- Warren Buffett：价值投资者，关注护城河
- Peter Lynch：GARP投资者，关注PEG
- Charlie Munger：质量投资者，逆向思维
- Michael Burry：逆向投资者，泡沫探测器

#### 2.4 LLM调用（llm.py）
**支持的LLM提供商：**
- OpenAI（GPT-4o等）
- Anthropic（Claude等）
- DeepSeek
- Groq
- 本地Ollama

### 3. 根目录脚本

#### 3.1 估值查询器（check_valuation.py）
- **功能**：S&P500估值指标查询和判断
- **接口**：命令行参数（--brief/--json）
- **输出**：估值区间判断和综合信号

#### 3.2 集成脚本（check_valuation_with_debate.py）
- **功能**：估值查询 + 自动触发辩论
- **逻辑**：根据估值信号决定是否辩论
- **输出**：估值报告 + 辩论结论 + 行动建议

#### 3.3 辩论入口（run_debate.py）
- **功能**：独立的辩论脚本
- **参数**：--topic/--stocks/--agents/--rounds
- **输出**：辩论过程和结论

## 数据流

### 估值分析数据流

```
┌─────────────┐
│  用户请求    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  获取市场数据 │
│ (yfinance/  │
│  akshare)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  估值指标计算 │
│ PE/VIX/52周  │
│  /10Y国债    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  估值信号判断 │
│ (便宜/合理/  │
│  偏贵/极贵)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  决定是否辩论 │
│ (自动触发)   │
└──────┬──────┘
       │
       ├──── 不需要辩论 ────┐
       │                    │
       │                    ▼
       │              ┌─────────────┐
       │              │  输出估值报告 │
       │              └─────────────┘
       │
       └──── 需要辩论 ─────┐
                           │
                           ▼
                    ┌─────────────┐
                    │  四大佬辩论  │
                    │ (LLM调用)   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  综合结论    │
                    │ (估值+辩论) │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  输出报告    │
                    └─────────────┘
```

## 依赖关系

### 外部依赖

```
yfinance          # 美股数据获取
akshare           # A股数据获取
langchain         # LLM编排框架
openai            # OpenAI API
anthropic         # Anthropic API
pandas            # 数据处理
python-dotenv     # 环境变量管理
```

### 内部依赖

```
src/main.py
    ├── src/agents/* (原工程代理)
    └── src/tools/api.py
            └── src/tools/a_share_api.py (新增)

src/debate/sp500_timing.py
    ├── src/debate/market_data.py
    │       ├── yfinance (美股)
    │       └── akshare (A股)
    ├── src/debate/debater.py
    │       └── src/debate/llm.py
    └── src/debate/agents.py (四大佬)
```

## 配置管理

### 环境变量

| 变量名 | 必需 | 说明 |
|--------|------|------|
| OPENAI_API_KEY | 是* | OpenAI API密钥 |
| ANTHROPIC_API_KEY | 是* | Anthropic API密钥 |
| DEEPSEEK_API_KEY | 是* | DeepSeek API密钥 |
| FINANCIAL_DATASETS_API_KEY | 否 | 美股财务数据API |
| USE_A_SHARE_DB | 否 | 启用A股数据库（默认true） |
| A_SHARE_DB_PATH | 否 | A股数据库路径 |

*至少配置一个LLM API密钥

### 配置文件

- `.env`：环境变量（不提交到git）
- `pyproject.toml`：Poetry依赖配置
- `poetry.lock`：依赖版本锁定

## 扩展性设计

### 添加新的投资大佬

1. 在 `src/debate/agents.py` 中定义新的Agent：

```python
NEW_AGENT = Agent(
    name="New Investor",
    role="value",
    system_prompt="""You are a value investor..."""
)

# 添加到ALL_AGENTS列表
ALL_AGENTS = [BUFFETT, LYNCH, MUNGER, BURRY, NEW_AGENT]
```

2. 在 `run_debate.py` 中添加映射：

```python
AGENT_MAP["new_investor"] = NEW_AGENT
```

### 添加新的估值指标

1. 在 `src/debate/sp500_timing.py` 中添加指标：

```python
VALUATION_BANDS["new_metric"] = {"cheap": 0, "fair": 50, "expensive": 100}

def classify_new_metric(val):
    # 实现分类逻辑
    pass
```

2. 在 `get_overall_signal()` 中添加指标权重

### 支持新的数据源

1. 在 `src/debate/market_data.py` 中添加获取函数：

```python
def fetch_new_data_source() -> list[IndexSnapshot]:
    """获取新数据源"""
    # 实现数据获取逻辑
    pass
```

2. 在 `get_market_data()` 中调用新函数

## 性能优化

### 缓存策略

```python
# 市场数据缓存（避免重复请求）
from functools import lru_cache

@lru_cache(maxsize=128)
def get_market_data():
    # 数据获取逻辑
    pass
```

### 异步处理

```python
# 并发获取多个数据源
import asyncio
import aiohttp

async def fetch_all_data():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_yfinance_data(session),
            fetch_akshare_data(session),
        ]
        results = await asyncio.gather(*tasks)
        return results
```

## 安全考虑

### API密钥管理
- 使用 `.env` 文件存储敏感信息
- `.gitignore` 排除 `.env` 文件
- 环境变量优先于硬编码

### 数据安全
- A股数据库文件权限设置为600
- 日志中不记录API密钥
- 定期清理敏感数据

### 网络安全
- 使用HTTPS访问外部API
- 设置合理的请求超时
- 实现重试和降级策略

## 测试策略

### 单元测试

```python
# 测试估值判断逻辑
def test_classify():
    assert classify(15, VALUATION_BANDS["pe"]) == ("🟢", "便宜")
    assert classify(25, VALUATION_BANDS["pe"]) == ("🟠", "偏贵")

# 测试数据获取
def test_get_market_data():
    bundle = get_market_data()
    assert bundle.us_indices is not None
    assert bundle.macro is not None
```

### 集成测试

```python
# 测试完整流程
def test_sp500_timing():
    result = check_sp500_timing()
    assert result.valuation_signal in ["🟢", "🟡", "🟠", "🔴"]
    assert result.summary != ""
```

### 端到端测试

```bash
# 命令行测试
poetry run python -m src.debate.sp500_timing --brief

# Python API测试
poetry run python -c "
from src.debate.sp500_timing import check_sp500_timing
result = check_sp500_timing()
print(result.summary)
"
```

## 监控和日志

### 日志级别

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 监控指标

- 市场数据获取成功率
- LLM API调用延迟
- 辩论模块执行时间
- 错误率和异常统计

## 后续规划

### 短期（1-2周）
- [ ] 完善单元测试
- [ ] 优化辩论模块性能
- [ ] 添加更多估值指标

### 中期（1-2月）
- [ ] 支持更多LLM提供商
- [ ] 实现数据缓存机制
- [ ] 添加Web界面

### 长期（3-6月）
- [ ] 实现实时交易信号
- [ ] 集成更多投资大佬
- [ ] 支持多语言（中文/英文）

## 相关文档

- [部署文档](DEPLOY.md) — 安装和部署说明
- [操作手册](SP500_TIMING_GUIDE.md) — 详细使用说明
- [原工程README](../README.md) — 原工程文档
