# AI Hedge Fund 部署文档

## 概述

本文档说明如何在服务器上部署和运行AI Hedge Fund项目，包括：
- 原工程功能（18个AI投资大佬代理）
- 新增功能（七大佬辩论、A股支持、S&P500估值分析）
- 量化预计算指标（技术指标+指数估值）
- 辩论历史记忆系统

**当前版本：7-agent 辩论系统**
- 7位投资大佬：Warren Buffett、Benjamin Graham、Charlie Munger、Peter Lynch、Michael Burry、Stanley Druckenmiller、Nassim Taleb
- 3阶段辩论流程：投票 → 挑战 → 最终投票 → 综合
- 完整辩论约4分钟（17次LLM调用）
- 自动保存辩论历史，支持表现追踪和准确率统计

## 环境要求

### 系统要求
- Python 3.11+
- Poetry（依赖管理）
- Git

### 硬件要求
- 内存：建议4GB+
- 磁盘：建议10GB+（含依赖和数据）
- 网络：需要访问外网（获取市场数据、调用LLM API）

## 安装步骤

### 1. 克隆仓库

```bash
# 克隆主公的fork
git clone git@github.com:fkchaos/ai-hedge-fund.git
cd ai-hedge-fund

# 配置远程仓库（可选，用于同步原工程）
git remote add upstream https://github.com/virattt/ai-hedge-fund.git
```

### 2. 安装Poetry（如果未安装）

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. 安装依赖

```bash
poetry install
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入API密钥
nano .env
```

**必需的环境变量：**

```bash
# LLM API密钥（至少配置一个）
OPENAI_API_KEY=your-openai-key
# 或
ANTHROPIC_API_KEY=your-anthropic-key
# 或
DEEPSEEK_API_KEY=your-deepseek-key

# MiMo LLM配置（推荐使用MiMo推理模型）
OPENAI_API_KEY=your-mimo-api-key
OPENAI_API_BASE=https://api.example.com/v1
OPENAI_API_MODEL=mimo-v2.5

# 财务数据API（可选，美股数据）
FINANCIAL_DATASETS_API_KEY=your-financial-datasets-key

# A股数据库路径（新增功能需要）
USE_A_SHARE_DB=true
A_SHARE_DB_PATH=/root/a-share-quant-sim/data/quant_stocks.db
```

**其他可选的LLM API密钥：**

```bash
GROQ_API_KEY=your-groq-key
GOOGLE_API_KEY=your-google-key
XAI_API_KEY=your-xai-key
OPENROUTER_API_KEY=your-openrouter-key
MOONSHOT_API_KEY=your-moonshot-key
```

### 5. 创建辩论历史目录

```bash
# 辩论记录默认存储在 data/debate_history/
mkdir -p data/debate_history
```

### 6. 验证安装

```bash
# 检查Python环境
poetry run python --version

# 检查依赖
poetry run pip list | grep -E "(yfinance|akshare|langchain)"

# 测试导入（7-agent系统核心模块）
poetry run python -c "from src.debate.agents import ALL_AGENTS; print(f'✅ {len(ALL_AGENTS)}位大佬就绪')"

# 测试量化信号模块
poetry run python -c "from src.debate.quant_signals import format_quant_summary; print('✅ 量化预计算模块就绪')"

# 测试历史记忆模块
poetry run python -c "from src.debate.history import DebateHistory; print('✅ 历史记忆系统就绪')"

# 测试市场数据获取
poetry run python -c "from src.debate.market_data import get_market_data; print('✅ 市场数据模块就绪')"
```

## 功能模块

### 原工程功能

**18个AI投资大佬代理：**
- Warren Buffett — 价值投资
- Charlie Munger — 质量投资
- Michael Burry — 逆向投资
- Peter Lynch — GARP投资
- 等等...

**命令行使用：**
```bash
# 运行AI对冲基金分析
poetry run python src/main.py --ticker AAPL,MSFT,NVDA

# 运行回测
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA
```

### 新增功能

**1. 七大佬辩论模块（S&P500出手时机判断）**

```bash
# 快速估值查询（不运行辩论）
poetry run python -m src.debate.sp500_timing --brief

# 估值 + 完整7-agent辩论（约4分钟）
poetry run python -m src.debate.sp500_timing

# 指定个股分析（含辩论）
poetry run python -m src.debate.sp500_timing --stocks AAPL,MSFT

# 自定义辩论主题
python run_debate.py --topic "当前市场环境下，是否应该投资S&P500?"

# 指定参与大佬
python run_debate.py --topic "科技股估值" --stocks AAPL,MSFT,GOOGL --agents buffett,lynch,munger

# 指定辩论轮数（默认2轮）
python run_debate.py --topic "市场方向判断" --rounds 3

# 输出JSON格式
python run_debate.py --topic "S&P500估值" --json

# 保存结果到文件
python run_debate.py --topic "投资时机判断" --output /tmp/debate_result.txt
```

**2. 七大佬辩论流程详解**

辩论分为4个阶段：

| 阶段 | 说明 | LLM调用次数 |
|------|------|------------|
| Phase 1: 投票 | 7位大佬独立快速投票，统计看多/看空/中性分布 | 7次 |
| Phase 2: 挑战 | 找出分歧最大的代表深入辩论（最多4人参与） | 最多8次 |
| Phase 3: 最终投票 | 所有人看到辩论结果后重新表态（可改票） | 7次 |
| 综合 | 主持人综合出最终结论 | 1次 |

**7位大佬角色：**

| 大佬 | 角色 | 投资风格 |
|------|------|---------|
| Warren Buffett | value | 价值投资之王，护城河+安全边际 |
| Benjamin Graham | deep-value | 价值投资之父，Graham Number |
| Charlie Munger | skeptic | 质量投资大师，逆向思维+多元模型 |
| Peter Lynch | growth | GARP投资之王，PEG估值 |
| Michael Burry | contrarian | 逆向投资大师，泡沫探测器 |
| Stanley Druckenmiller | macro-momentum | 宏观对冲大师，流动性+动量 |
| Nassim Taleb | tail-risk | 反脆弱大师，尾部风险专家 |

**3. 量化预计算模块（quant_signals.py）**

系统自动用Python精确计算技术指标，喂给LLM解释（不让LLM猜数字）：

- 均线系统：MA5/20/50/200，均线排列，价格相对位置
- 动量指标：RSI(14)，MACD(12,26,9)
- 波动率：布林带(20,2)，ATR(14)
- 成交量：OBV趋势，量价关系
- 趋势强度：ADX(14)
- 指数估值：CAPE(席勒PE)、ERP(股权风险溢价)

```python
# 单独查看量化指标
from src.debate.quant_signals import format_quant_summary
summary = format_quant_summary()
print(summary)
```

**4. 辩论历史记忆系统（history.py）**

每次辩论自动保存完整记录，支持：
- 辩论存档：自动保存到 `data/debate_history/` 目录
- 历史加载：读取最近N次辩论，供大佬参考
- 记忆注入：Phase 1投票前把历史上下文注入prompt
- 表现追踪：辩论后记录SPY涨跌，评估各大佬预测准确率

```python
from src.debate.history import DebateHistory

# 加载最近3次辩论记录
history = DebateHistory()
records = history.load_recent(3)

# 格式化历史上下文供大佬参考
context = history.format_memory_context(n=3)

# 统计各大佬历史准确率
stats = history.get_agent_stats()
```

**5. A股支持**

```bash
# A股分析
poetry run python run_a_share.py

# 持仓分析
poetry run python run_holdings.py
```

**6. 估值查询器**

```bash
# S&P500估值查询
poetry run python check_valuation.py

# 估值+辩论集成
poetry run python check_valuation_with_debate.py
```

## 数据源配置

### 美股数据（yfinance）
- 自动获取，无需额外配置
- 支持：SPY、QQQ、VIX、国债收益率等
- **宏观数据**：13周国债收益率（联邦基金利率代理）、5年期/10年期/30年期国债、收益率曲线(10Y-3M利差)、美元指数、黄金

### A股数据（akshare + 本地数据库）
- 需要配置 `A_SHARE_DB_PATH` 环境变量
- 数据库路径：`/root/a-share-quant-sim/data/quant_stocks.db`
- 支持：A股指数、个股行情、财务数据

### 财务数据API（financialdatasets.ai）
- 需要配置 `FINANCIAL_DATASETS_API_KEY`
- 用于获取美股详细财务数据
- 可选，不配置也能运行（使用yfinance基础数据）

### 宏观利率数据
系统自动获取以下利率数据用于估值分析：
- **13周国债收益率（^IRX）**：联邦基金利率代理，判断紧缩/宽松周期
- **5年期国债收益率（^FVX）**：中期利率参考
- **10年期国债收益率（^TNX）**：长期利率基准，用于ERP计算
- **30年期国债收益率（^TYX）**：期限利差(30Y-10Y)
- **收益率曲线(10Y-3M利差)**：倒挂=衰退信号，平坦=放缓，陡峭=扩张

## 辩论输出说明

### 目标仓位
每次辩论的最终投票阶段，每位大佬会输出目标仓位（0-100%）：
- `target_position`: 0=全现金，100=满仓SPY
- 系统自动计算7位大佬的平均目标仓位
- 可作为资产配置参考

### 辩论记录字段
```json
{
  "id": "a1b2c3d4",
  "timestamp": "2025-07-23T10:30:00",
  "topic": "当前市场环境下，是否应该投资S&P500?",
  "spy_price_at_debate": 580.25,
  "pe": 24.5,
  "vix": 18.3,
  "pos_52w": 72.5,
  "tnx_10y": 4.25,
  "valuation_signal": "🟡",
  "votes": [...],
  "challenges": [...],
  "final_votes": [...],
  "consensus": "bullish",
  "confidence_avg": 72,
  "avg_target_position": 65,
  "spy_price_after": 585.0,
  "spy_change_pct": 0.82
}
```

## 常见问题

### Q1: 依赖安装失败

```bash
# 清理缓存重试
poetry cache clear --all .
poetry install
```

### Q2: yfinance获取数据失败

```bash
# 测试yfinance连接
poetry run python -c "
import yfinance as yf
spy = yf.Ticker('SPY')
print(f'SPY价格: {spy.info.get(\"regularMarketPrice\")}')
"
```

### Q3: A股数据库连接失败

```bash
# 检查数据库文件是否存在
ls -la /root/a-share-quant-sim/data/quant_stocks.db

# 检查环境变量
echo $A_SHARE_DB_PATH
```

### Q4: LLM API调用失败

```bash
# 检查API密钥配置
grep -E "(OPENAI|ANTHROPIC|DEEPSEEK)_API_KEY" .env

# 测试MiMo API连接
poetry run python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_API_BASE'))
resp = client.chat.completions.create(
    model=os.getenv('OPENAI_API_MODEL', 'mimo-v2.5'),
    messages=[{'role': 'user', 'content': 'Hello'}],
    max_tokens=10
)
print(f'✅ MiMo API连接成功: {resp.choices[0].message.content}')
"
```

### Q5: 辩论运行缓慢

7-agent完整辩论约需4分钟（17次LLM调用），这是正常的。优化建议：

```bash
# 如果只需要快速估值结论（不运行辩论）
poetry run python -m src.debate.sp500_timing --brief

# 减少参与大佬数量（加速）
python run_debate.py --topic "S&P500估值" --agents buffett,lynch,munger

# 减少辩论轮数（加速）
python run_debate.py --topic "S&P500估值" --rounds 1
```

### Q6: 某个大佬超时或被禁用

系统内置容错机制：
- 单个大佬超时30秒会跳过，不影响整体辩论
- 连续2次失败的大佬会被禁用（本次辩论）
- 其余大佬继续辩论，综合时排除禁用大佬

查看被禁用的大佬：
```bash
# 检查checkpoint日志
ls -la data/checkpoints/
cat data/checkpoints/debate_*_phase3_final_vote.json | python -m json.tool | grep "disabled"
```

### Q7: 辩论历史记录查看

```bash
# 查看最近的辩论记录
ls -lt data/debate_history/ | head -5

# 查看某次辩论详情
cat data/debate_history/2025-07-23_a1b2c3d4.json | python -m json.tool
```

## 服务部署（可选）

如果需要作为服务运行，可以使用systemd或supervisor：

### systemd服务示例

```ini
# /etc/systemd/system/ai-hedge-fund.service
[Unit]
Description=AI Hedge Fund Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ai-hedge-fund
ExecStart=/root/.local/bin/poetry run python -m src.debate.sp500_timing --brief
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable ai-hedge-fund
sudo systemctl start ai-hedge-fund

# 查看状态
sudo systemctl status ai-hedge-fund
```

### Cron定时任务示例

```bash
# 每天9:30和15:00检查S&P500估值（快速模式）
30 9 * * 1-5 cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --brief >> /var/log/sp500_valuation.log 2>&1
0 15 * * 1-5 cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --brief >> /var/log/sp500_valuation.log 2>&1

# 每天10:00运行完整7-agent辩论（约4分钟）
0 10 * * 1-5 cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing >> /var/log/sp500_debate.log 2>&1
```

## 更新维护

### 同步原工程更新

```bash
# 拉取原工程更新
git fetch upstream

# 查看差异
git log --oneline upstream/main..HEAD

# 合并更新（可能需要解决冲突）
git merge upstream/main

# 推送到主公的fork
git push origin main
```

### 更新依赖

```bash
# 更新所有依赖
poetry update

# 更新特定依赖
poetry update yfinance
```

### 清理辩论历史

```bash
# 清理30天前的辩论记录
find data/debate_history/ -name "*.json" -mtime +30 -delete

# 查看历史记录大小
du -sh data/debate_history/
```

## 监控和日志

### 查看运行日志

```bash
# 查看最近的日志
tail -f /var/log/sp500_valuation.log

# 查看辩论日志
tail -f /var/log/sp500_debate.log

# 查看错误日志
grep -i error /var/log/sp500_valuation.log
```

### 健康检查

```bash
# 快速健康检查
cd /root/ai-hedge-fund && poetry run python -c "
from src.debate.market_data import get_market_data
bundle = get_market_data()
print(f'✅ 市场数据获取成功: {bundle.timestamp}')
print(f'   SPY: \${bundle.us_indices[0].price if bundle.us_indices else \"N/A\"}')
print(f'   宏观指标数: {len(bundle.macro)}')
"

# 检查7-agent辩论系统
cd /root/ai-hedge-fund && poetry run python -c "
from src.debate.agents import ALL_AGENTS
from src.debate.debater import MarketDebater
print(f'✅ 7-agent系统就绪: {len(ALL_AGENTS)}位大佬')
for a in ALL_AGENTS:
    print(f'   {a.name} ({a.role})')
"

# 检查辩论历史
cd /root/ai-hedge-fund && poetry run python -c "
from src.debate.history import DebateHistory
h = DebateHistory()
records = h.load_recent(5)
print(f'✅ 历史记录: {len(records)}条')
stats = h.get_agent_stats()
if stats:
    print('   各大佬准确率:')
    for name, s in sorted(stats.items(), key=lambda x: x[1].get('accuracy', 0), reverse=True):
        print(f'     {name}: {s.get(\"accuracy\", 0)}%')
"
```

### 性能监控

```bash
# 查看最近辩论的耗时和LLM调用次数
ls -lt data/debate_history/ | head -1 | awk '{print $NF}' | xargs cat | python -c "
import json, sys
data = json.load(sys.stdin)
print(f'辩论时间: {data[\"total_time\"]:.1f}秒')
print(f'LLM调用: {data[\"total_llm_calls\"]}次')
print(f'平均目标仓位: {data.get(\"avg_target_position\", \"N/A\")}%')
"
```

## 安全注意事项

1. **API密钥安全**：`.env`文件不要提交到git仓库
2. **网络访问**：确保服务器可以访问yfinance和LLM API
3. **数据库权限**：A股数据库文件权限设置为600
4. **日志脱敏**：日志中不要记录API密钥
5. **辩论记录**：`data/debate_history/`包含投资观点，注意访问权限

## 相关文档

- [操作手册](SP500_TIMING_GUIDE.md) — 详细使用说明
- [架构设计](ARCHITECTURE.md) — 系统架构和代码结构
