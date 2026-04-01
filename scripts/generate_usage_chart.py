import matplotlib.pyplot as plt
from datetime import datetime
import sys
import subprocess

# 从统计脚本获取数据
period = sys.argv[1] if len(sys.argv) > 1 else '7d'
result = subprocess.check_output(['python3', '/root/.openclaw/workspace/skills/openclaw-usage-stats/scripts/get_usage_stats.py', period]).decode('utf-8')
lines = result.split('\n')

# 解析基础数据
time_range = lines[0].replace('📊 统计时间范围：', '')
total_msg = int(lines[1].split('：')[1].replace(' 次', ''))
user_msg = int(lines[2].split('：')[1].replace(' 次', ''))
assistant_msg = int(lines[3].split('：')[1].replace(' 次', ''))
tool_call_msg = int(lines[4].split('：')[1].replace(' 次', ''))
tool_response_msg = int(lines[5].split('：')[1].replace(' 次', ''))
system_msg = int(lines[6].split('：')[1].replace(' 次', ''))
token_usage = lines[7].replace('🧠 Token消耗情况：', '')

# 解析按天统计数据
daily_dates = []
daily_total = []
daily_user = []
daily_assistant = []
daily_tool = []
in_daily_section = False
for line in lines:
    if line.startswith('📅 按天统计明细：'):
        in_daily_section = True
        continue
    if in_daily_section and line.strip().startswith('202'):
        parts = line.strip().split('：')
        date = parts[0]
        stats_part = parts[1].split('|')
        total = int(stats_part[0].replace('总', '').replace('次', '').strip())
        user = int(stats_part[1].replace('用户', '').replace('次', '').strip())
        assistant = int(stats_part[2].replace('助手', '').replace('次', '').strip())
        tool = int(stats_part[3].replace('工具', '').replace('次', '').strip())
        daily_dates.append(date)
        daily_total.append(total)
        daily_user.append(user)
        daily_assistant.append(assistant)
        daily_tool.append(tool)

# 设置图片样式
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False
fig = plt.figure(figsize=(16, 10))

# 子图1：消息类型占比饼图
ax1 = fig.add_subplot(2, 2, 1)
labels = [
    f'用户输入\n({user_msg}次)', 
    f'助手回复\n({assistant_msg - tool_call_msg}次)', 
    f'工具调用\n({tool_call_msg}次)',
    f'工具返回\n({tool_response_msg}次)',
    f'系统消息\n({system_msg}次)'
]
sizes = [user_msg, assistant_msg - tool_call_msg, tool_call_msg, tool_response_msg, system_msg]
colors = ['#FF9800', '#2196F3', '#4CAF50', '#FFC107', '#9C27B0']
explode = (0.05, 0, 0, 0, 0)
ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.axis('equal')
ax1.set_title('消息类型占比分布', fontsize=14, pad=20)

# 子图2：消息数量统计柱状图
ax2 = fig.add_subplot(2, 2, 2)
metrics = ['总消息数', '用户输入', '助手回复', '工具调用', '工具返回', '系统消息']
values = [total_msg, user_msg, assistant_msg, tool_call_msg, tool_response_msg, system_msg]
bars = ax2.bar(metrics, values, color=['#607D8B', '#FF9800', '#2196F3', '#4CAF50', '#FFC107', '#9C27B0'], width=0.6)
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom')
ax2.set_title('各类型消息数量统计', fontsize=14, pad=20)
ax2.set_ylabel('次数', fontsize=12)
ax2.grid(axis='y', linestyle='--', alpha=0.7)
plt.setp(ax2.get_xticklabels(), rotation=30, ha='right')

# 子图3：按天使用趋势图
ax3 = fig.add_subplot(2, 1, 2)
ax3.plot(daily_dates, daily_total, marker='o', label='总消息数', color='#607D8B', linewidth=2)
ax3.plot(daily_dates, daily_user, marker='s', label='用户输入', color='#FF9800', linewidth=2)
ax3.plot(daily_dates, daily_assistant, marker='^', label='助手回复', color='#2196F3', linewidth=2)
ax3.plot(daily_dates, daily_tool, marker='*', label='工具消息', color='#4CAF50', linewidth=2)
# 添加数据标签
for x, y in enumerate(daily_total):
    ax3.text(x, y + 0.5, str(y), ha='center')
ax3.set_title('按天使用趋势统计', fontsize=14, pad=20)
ax3.set_xlabel('日期', fontsize=12)
ax3.set_ylabel('消息次数', fontsize=12)
ax3.legend()
ax3.grid(axis='y', linestyle='--', alpha=0.7)
plt.setp(ax3.get_xticklabels(), rotation=30, ha='right')

# 添加整体标题和说明
plt.suptitle(f'OpenClaw 近{period}使用统计\n统计时间范围：{time_range}', fontsize=16, y=0.98)
plt.figtext(0.5, 0.01, f'注：{token_usage}\n工具调用已包含在助手回复计数中，工具返回为工具执行后返回的消息', ha='center', fontsize=10, color='#666666')

plt.tight_layout()
# 保存图片
plt.savefig('/root/.openclaw/workspace/usage_stats_full.png', dpi=100, bbox_inches='tight')
print("✅ 全量统计图像已生成：usage_stats_full.png")
print("\n" + result)
