# S&P500 四大佬辩论出手时机判断器 — 操作手册

## 快速开始

### 1. 命令行查询（最简单）

```bash
cd /root/ai-hedge-fund

# 仅估值查询（不辩论）
poetry run python -m src.debate.sp500_timing --brief

# 估值查询 + 自动辩论
poetry run python -m src.debate.sp500_timing

# 完整输出（含大佬观点）
poetry run python -m src.debate.sp500_timing --json
```

### 2. Python代码调用

```python
import sys
sys.path.insert(0, '/root/ai-hedge-fund')

from src.debate.sp500_timing import check_sp500_timing

# 基础用法
result = check_sp500_timing()
print(result.summary)

# 指定辩论轮数
result = check_sp500_timing(debate_rounds=3)

# 强制辩论（即使估值中性）
result = check_sp500_timing(force_debate=True)

# 自定义主题
result = check_sp500_timing(topic="当前是否应该加仓摩根标普500?")
```

---

## 返回结构说明

`TimingResult` 对象包含以下字段：

### 估值指标
| 字段 | 类型 | 说明 |
|------|------|------|
| `spy_price` | float | SPY当前价格 |
| `pe` | float | S&P500市盈率 |
| `vix` | float | VIX恐慌指数 |
| `pos_52w` | float | 52周位置百分比（0-100） |
| `tnx_10y` | float | 10年期美国国债收益率 |

### 估值信号
| 字段 | 类型 | 说明 |
|------|------|------|
| `valuation_signal` | str | "🟢" / "🟡" / "🟠" / "🔴" |
| `valuation_desc` | str | "强烈买入" / "可以分批买" / "偏贵" / "不买" |

### 辩论结论（如果启用辩论）
| 字段 | 类型 | 说明 |
|------|------|------|
| `debate_enabled` | bool | 是否启用了辩论 |
| `debate_consensus` | str | "bullish" / "bearish" / "neutral" |
| `debate_confidence` | int | 平均置信度 0-100 |
| `debate_agreement` | list | 大佬一致同意的观点 |
| `debate_risks` | list | 识别出的风险 |
| `action_items` | list | 行动建议 |

### 综合判断
| 字段 | 类型 | 说明 |
|------|------|------|
| `final_signal` | str | 最终信号 "🟢" / "🟡" / "🔴" |
| `final_advice` | str | 最终建议文字 |
| `summary` | str | 完整的可读报告 |

---

## 估值判断逻辑

### 单项指标区间
| 指标 | 🟢 便宜 | 🟡 合理 | 🟠 偏贵 | 🔴 极贵 |
|------|---------|---------|---------|---------|
| S&P500 PE | ≤18 | 18-22 | 22-27 | ≥27 |
| VIX | ≥30（恐慌买入） | 25-30 | 20-25 | ≤20（贪婪） |
| 52周位置 | ≤30% | 30-50% | 50-80% | ≥80% |
| 10Y国债 | ≤2.5% | 2.5-3.5% | 3.5-4.5% | ≥4.5% |

### 综合信号
- **强烈买入** 🟢：3个以上指标显示"便宜"
- **可以分批买** 🟢：2个指标显示"便宜"
- **偏贵** 🟠：2个以上指标显示"偏贵"
- **不买** 🔴：3个以上指标显示"极贵"
- **中性** 🟡：其余情况

---

## 辩论触发逻辑

系统会根据估值信号自动决定是否辩论：

| 估值信号 | 自动辩论 | 辩论轮数 | 说明 |
|---------|----------|----------|------|
| 强烈买入 🟢 | ✅ 是 | 2轮 | 快速确认买入机会 |
| 可以分批买 🟢 | ✅ 是 | 2轮 | 标准辩论 |
| 偏贵 🟠 | ✅ 是 | 1轮 | 轻量辩论确认风险 |
| 不买 🔴 | ✅ 是 | 2轮 | 确认高风险 |
| 中性 🟡 | ❌ 否 | - | 无需辩论 |

使用 `force_debate=True` 可强制辩论。

---

## 四大佬角色

### 优化说明（2026-07-19更新）
本次优化深度还原了每位大佬的投资哲学和思维模型：
- 添加了详细的决策框架（6步分析流程）
- 添加了Few-Shot示例（教LLM如何应用框架）
- 添加了个性化特征（语言风格、常用短语）
- 输出更有深度和实战价值

### Warren Buffett（价值投资者）
**核心投资哲学：**
1. 以合理价格买入优秀公司，而不是以便宜价格买入平庸公司
2. 别人贪婪时我恐惧，别人恐惧时我贪婪
3. 长期持有，理想是永远
4. 不懂不做，只投能力圈内的公司
5. 护城河是最重要的——找有持久竞争优势的企业

**思维模型（6步决策）：**
1. 能力圈检验 → 2. 护城河分析 → 3. 管理层评估 → 4. 财务健康 → 5. 估值判断 → 6. 长期持有检验

**信号判断规则：**
- Bullish: 优秀公司 + 合理价格 + 安全边际>25% + 愿意持有10年
- Bearish: 平庸公司 OR 高估 OR 超出能力圈
- Neutral: 好公司但价格不合理，或信息不足

### Peter Lynch（GARP投资者）
**核心投资哲学：**
1. 知道你拥有什么，知道你为什么拥有它
2. 买入你了解的公司
3. 用PEG估值：PE/增长率 < 1 是便宜
4. 寻找"十倍股"（ten-bagger）
5. 股价最终反映盈利增长

**思维模型（5步分析）：**
1. 公司分类 → 2. PEG检验 → 3. 故事检验 → 4. 资产负债表 → 5. 增长驱动

**信号判断规则：**
- Bullish: 合理分类 + PEG<1 + 增长故事成立 + 资产负债表健康
- Bearish: 增长放缓 OR PEG>2 OR 资产负债表恶化
- Neutral: 增长不确定或估值合理

### Charlie Munger（质量投资者）
**核心投资哲学：**
1. 反过来想，总是反过来想
2. 多元思维模型——用多学科知识分析问题
3. 太难了就说不
4. 避免愚蠢比追求聪明更重要
5. 宁可错过十个好机会，也不接受一个坏机会

**思维模型（多元模型）：**
数学 + 心理学（25种偏误）+ 经济学 + 生物学

**决策框架：**
1. 识别愚蠢 → 2. 逆向思考 → 3. 机会成本 → 4. 太难堆 → 5. 安全边际

### Michael Burry（逆向投资者）
**核心投资哲学：**
1. 市场先生是躁郁症患者——利用他的情绪
2. 找市场共识的错误——大众通常是错的
3. 风险第一，收益第二
4. 不对称性：小亏大赚
5. 数据驱动，不用直觉

**思维模型（6步逆向分析）：**
1. 识别市场共识 → 2. 找出共识的错误 → 3. 深度价值分析 → 4. 催化剂识别 → 5. 不对称性评估 → 6. 尾部风险分析

**信号判断规则：**
- Bullish: 市场共识错误 + 深度价值 + 催化剂 + 不对称性
- Bearish: 拥挤交易 OR 估值泡沫 OR 无催化剂
- Neutral: 无法量化优势

---

## 使用场景示例

### 场景1：日常估值检查（快速）

```bash
cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --brief
```

输出示例：
```
🟠 S&P500出手时机: 偏贵，观望
  SPY: $743.29 | PE: 26.7 | VIX: 18.77 | 52周: 88%
```

### 场景2：投资决策前（带辩论）

```bash
cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing
```

输出示例：
```
══════════════════════════════════════════════════════════════
  S&P500 出手时机判断报告
══════════════════════════════════════════════════════════════
  时间: 2026-07-19 18:00
  
  📊 估值指标
  ──────────────────────────────────────────────────────────
  SPY价格: $743.29
  🟠 PE: 26.74 → 偏贵
  🟠 VIX: 18.77 → 中性
  🔴 52周位置: 87.87% → 极贵
  🔴 10Y国债: 4.541% → 极贵
  
  📈 综合信号: 🟠 偏贵，观望

══════════════════════════════════════════════════════════════
  四大佬辩论结论
══════════════════════════════════════════════════════════════
  共识: 🔴 BEARISH | 平均置信度: 65%
  
  ✅ 一致同意:
    • 估值处于历史高位
    • 不建议此时入场
  
  🚨 风险提示:
    • 52周位置过高，回调风险大
    • 国债收益率偏高，压制估值
  
  📋 行动建议:
    • 等待回调至52周位置60%以下
    • 或VIX升至25以上再考虑

══════════════════════════════════════════════════════════════
  最终建议: 🔴 不建议买入（信号偏负面）
══════════════════════════════════════════════════════════════
```

### 场景3：JSON输出（程序化处理）

```bash
cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --json
```

```json
{
  "timestamp": "2026-07-19T18:00:00",
  "valuation": {
    "spy_price": 743.29,
    "pe": 26.74,
    "vix": 18.77,
    "pos_52w": 87.87,
    "tnx_10y": 4.541,
    "signal": "🟠",
    "description": "偏贵，观望"
  },
  "debate": {
    "enabled": true,
    "consensus": "bearish",
    "confidence": 65,
    "agreement": ["估值处于历史高位", "不建议此时入场"],
    "risks": ["52周位置过高", "国债收益率偏高"],
    "action_items": ["等待回调", "VIX升至25以上"]
  },
  "final": {
    "signal": "🔴",
    "advice": "不建议买入"
  }
}
```

### 场景4：Python代码集成

```python
#!/usr/bin/env python3
"""我的投资决策脚本"""
import sys
sys.path.insert(0, '/root/ai-hedge-fund')

from src.debate.sp500_timing import check_sp500_timing

def make_investment_decision():
    """根据估值和辩论结果做出决策"""
    result = check_sp500_timing()
    
    if result.final_signal == "🟢":
        print("✅ 可以买入")
        print(f"   建议: {result.final_advice}")
        # 执行买入逻辑...
        
    elif result.final_signal == "🔴":
        print("❌ 不建议买入")
        print(f"   原因: {result.final_advice}")
        # 继续观望...
        
    else:
        print("⏳ 观望中")
        print(f"   信号: {result.final_advice}")
    
    # 保存结果
    with open("investment_decision.txt", "w") as f:
        f.write(result.summary)

if __name__ == "__main__":
    make_investment_decision()
```

---

## 常见问题

### Q1: 辩论太慢怎么办？

辩论需要调用LLM，通常需要30-60秒。如果只需要快速估值：

```bash
# 使用 --brief 只看估值结论
poetry run python -m src.debate.sp500_timing --brief
```

### Q2: 如何只看某个大佬的观点？

目前辩论会调用所有4位大佬。如需单独调用，可直接使用 `run_debate.py`：

```bash
poetry run python run_debate.py --topic "S&P500估值" --agents buffett,munger --rounds 1
```

### Q3: 数据获取失败怎么办？

如果 yfinance 获取失败，可能是网络问题。检查：

```python
import yfinance as yf
spy = yf.Ticker("SPY")
print(spy.info)
```

### Q4: 如何保存结果？

```bash
# 命令行保存到文件
poetry run python -m src.debate.sp500_timing > report.txt

# JSON格式保存
poetry run python -m src.debate.sp500_timing --json > report.json
```

### Q5: 如何在cron任务中使用？

```bash
# cron job prompt 示例
cd /root/ai-hedge-fund && poetry run python -m src.debate.sp500_timing --brief
```

---

## 文件结构

```
ai-hedge-fund/
├── src/debate/
│   ├── sp500_timing.py      # 标准接口模块（本工具）
│   ├── market_data.py       # 市场数据获取
│   ├── debater.py           # 辩论引擎
│   ├── agents.py            # 四大佬角色定义
│   └── llm.py               # LLM调用
├── check_valuation.py       # 估值查询（独立脚本）
├── check_valuation_with_debate.py  # 估值+辩论（独立脚本）
└── run_debate.py            # 辩论入口（独立脚本）
```

---

## 适用基金/ETF

本工具**完全聚焦美股/标普500**，通过SPY获取S&P500数据，适用于所有跟踪S&P500的投资标的：

- **161125** — 易方达标普500ETF联接A
- **019305** — 摩根标普500ETF联接A
- 其他S&P500指数基金/ETF

估值指标（PE、VIX、52周位置、国债收益率）直接适用，无需转换。

**注意：** 四大佬（Buffett、Lynch、Munger、Burry）擅长美股分析，不擅长A股。本工具已移除A股数据获取，专注于美股/标普500分析。
---

## 更新日志

- **2026-07-19** — 初始版本，集成估值查询+四大佬辩论
- **2026-07-19** — 优化四大佬投资代理
  - 深度还原每位大佬的投资哲学和思维模型
  - 添加Few-Shot示例（教LLM如何应用框架）
  - 添加针对摩根标普基金的行动建议
  - 输出更有深度和实战价值
