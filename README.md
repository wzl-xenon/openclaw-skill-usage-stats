# OpenClaw Usage Statistics Skill | OpenClaw 用量统计技能

---

**English**
Full-featured usage statistics skill for OpenClaw, which can count all usage data during OpenClaw operation and support visual report generation. Suitable for personal usage analysis, cost accounting, and exception monitoring.

**中文**
OpenClaw 全功能用量统计技能，可统计OpenClaw运行期间的所有使用数据，支持可视化报表生成，适用于个人使用分析、成本核算、异常监控场景。

---

## ✨ Core Features | 核心功能

| Feature | 功能说明 |
|---------|---------|
| Multi-dimensional statistics | 多维度统计：总消息量、用户输入/助手回复/工具返回分类统计、工具调用明细（次数/成功率/平均耗时）、会话统计、按小时/天时间趋势 |
| Visual reports | 可视化报表：自动生成饼图/柱状图/折线图组合统计图表，支持固定周期/自定义时间范围 |
| Practical tools | 实用功能：CSV明细导出、5分钟查询缓存、异常用量告警、使用行为分析报告 |
| Flexible time range | 灵活时间范围：支持24h/7d/30d固定周期查询，也支持任意起止时间自定义查询 |

---

## 📦 Installation | 安装
1. Download this skill to OpenClaw `skills/` directory
2. Install dependencies:
```bash
pip3 install matplotlib
apt install -y fonts-noto-cjk # Fix Chinese display issue / 解决中文显示乱码问题
```
3. Restart OpenClaw service to load the skill

---

## 🚀 Usage | 使用方法

### 1. Natural Language Trigger (Recommended for normal users) | 自然语言触发（普通用户推荐）
After installing the skill, you can directly trigger it by chatting, no need to run commands:
安装技能后，直接在对话中通过自然语言触发即可，无需运行命令：
```
// English examples | 英文示例
- "Show me the usage statistics for the last 24 hours"
- "Generate a 7-day usage chart"
- "Export CSV of usage data for the last month"
- "Query usage from 9 AM to 6 PM today"
- "Generate a behavior analysis report"

// Chinese examples | 中文示例
- "查询近24小时使用统计"
- "生成近7天的用量图表"
- "导出最近一个月的用量明细CSV"
- "查询今天9点到18点的使用情况"
- "生成使用行为分析报告"
```

### 2. Slash Command | 斜杠命令
```
/stat 24h    # Query last 24 hours data / 查询近24小时数据
/stat 7d     # Query last 7 days data / 查询近7天数据
/stat 30d    # Query last 30 days data / 查询近30天数据
/stat export # Export CSV data / 导出CSV明细
```

### 3. Manual Script Execution (For developers/debugging) | 手动运行脚本（开发者/调试使用）
```bash
# Query last 24 hours data / 查询近24小时数据
python3 scripts/get_usage_stats.py 24h
# Query last 7 days data / 查询近7天数据
python3 scripts/get_usage_stats.py 7d
# Query last 30 days data / 查询近30天数据
python3 scripts/get_usage_stats.py 30d
# Query custom time range / 查询自定义时间范围
python3 scripts/get_usage_stats.py "2026-04-01 09:00" "2026-04-01 18:00"
# Export to CSV file / 导出CSV明细数据
python3 scripts/get_usage_stats.py 7d --export
# Force refresh latest data / 强制刷新最新数据（跳过缓存）
python3 scripts/get_usage_stats.py 24h --force

# Generate charts for 24h/7d/30d at once / 同时生成24h/7d/30d三个固定周期的统计图表
python3 scripts/generate_all_period_charts.py
# Generate chart for custom time range / 生成自定义时间范围统计图表
python3 scripts/generate_custom_usage_chart.py "2026-04-01 09:00" "2026-04-01 18:00"

# Generate behavior analysis report / 生成使用行为分析报告
python3 scripts/generate_behavior_analysis.py
```

---

## 📊 Output Example | 输出示例
```
📊 统计时间范围：2026-03-31 14:00 至 2026-04-01 14:00
🔢 总消息次数：486 次
  ├─ 用户输入：51 次
  ├─ 助手回复：243 次
  │  └─ 包含工具调用：193 次
  └─ 工具返回结果：192 次
✅ 分类校验：用户+助手+工具返回 = 486 次，与总消息数一致
⚠️ 【异常告警】今日用量异常！当前总消息数486次，超过近7天日均6.0次的3倍

🛠️ 工具调用统计（Top5）：
  exec：74 次 | 成功率 98.6% | 平均耗时 1.81s
  edit：73 次 | 成功率 100.0% | 平均耗时 0.04s
  process：17 次 | 成功率 100.0% | 平均耗时 24.62s
```

---

## 📄 License | 许可证
MIT License
