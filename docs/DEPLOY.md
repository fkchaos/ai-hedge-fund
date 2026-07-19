# AI Hedge Fund 部署文档

## 概述

本文档说明如何在服务器上部署和运行AI Hedge Fund项目，包括：
- 原工程功能（18个AI投资大佬代理）
- 新增功能（四大佬辩论、A股支持、S&P500估值分析）

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

### 5. 验证安装

```bash
# 检查Python环境
poetry run python --version

# 检查依赖
poetry run pip list | grep -E "(yfinance|akshare|langchain)"

# 测试导入
poetry run python -c "from src.debate.sp500_timing import check_sp500_timing; print('✅ 导入成功')"
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

**1. 四大佬辩论模块（S&P500出手时机判断）**

```bash
# 快速估值查询
poetry run python -m src.debate.sp500_timing --brief

# 估值+辩论
poetry run python -m src.debate.sp500_timing

# 指定个股分析
poetry run python -m src.debate.sp500_timing --stocks AAPL,MSFT
```

**2. A股支持**

```bash
# A股分析
poetry run python run_a_share.py

# 持仓分析
poetry run python run_holdings.py
```

**3. 估值查询器**

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

### A股数据（akshare + 本地数据库）
- 需要配置 `A_SHARE_DB_PATH` 环境变量
- 数据库路径：`/root/a-share-quant-sim/data/quant_stocks.db`
- 支持：A股指数、个股行情、财务数据

### 财务数据API（financialdatasets.ai）
- 需要配置 `FINANCIAL_DATASETS_API_KEY`
- 用于获取美股详细财务数据
- 可选，不配置也能运行（使用yfinance基础数据）

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

# 测试API连接（以OpenAI为例）
poetry run python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('✅ OpenAI API连接成功')
"
```

### Q5: 辩论模块运行缓慢

辩论需要调用LLM，通常需要30-60秒。如果只需要快速估值：

```bash
# 使用 --brief 只看估值结论
poetry run python -m src.debate.sp500_timing --brief
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
# 每天9:30和15:00检查S&P500估值
30 9 * * 1-5 cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --brief >> /var/log/sp500_valuation.log 2>&1
0 15 * * 1-5 cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --brief >> /var/log/sp500_valuation.log 2>&1
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

## 监控和日志

### 查看运行日志

```bash
# 查看最近的日志
tail -f /var/log/sp500_valuation.log

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
print(f'   SPY: ${bundle.us_indices[0].price if bundle.us_indices else \"N/A\"}')
"
```

## 安全注意事项

1. **API密钥安全**：`.env`文件不要提交到git仓库
2. **网络访问**：确保服务器可以访问yfinance和LLM API
3. **数据库权限**：A股数据库文件权限设置为600
4. **日志脱敏**：日志中不要记录API密钥

## 相关文档

- [操作手册](SP500_TIMING_GUIDE.md) — 详细使用说明
- [架构设计](ARCHITECTURE.md) — 系统架构和代码结构
