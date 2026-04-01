import matplotlib.pyplot as plt
from datetime import datetime
import subprocess
import os

def format_num(num):
    """数字格式化，大于1000显示为k，大于10000显示为w，保留1位小数"""
    if num >= 10000:
        return f"{round(num/10000, 1)}w"
    elif num >= 1000:
        return f"{round(num/1000, 1)}k"
    else:
        return str(num)

# 要生成的三个时间周期
periods = [('24h', '近24小时'), ('7d', '近7天'), ('30d', '近30天')]
output_files = []

for period, period_name in periods:
    print(f"正在生成{period_name}统计...")
    # 获取统计数据
    result = subprocess.check_output(['python3', '/root/.openclaw/workspace/skills/openclaw-usage-stats/scripts/get_usage_stats.py', period]).decode('utf-8')
    lines = result.split('\n')
    
    # 解析基础数据
    time_range = lines[0].replace('📊 统计时间范围：', '')
    total_msg = int(lines[1].split('：')[1].replace(' 次', ''))
    user_msg = int(lines[2].split('：')[1].replace(' 次', ''))
    assistant_msg = int(lines[3].split('：')[1].replace(' 次', ''))
    tool_call_msg = int(lines[4].split('：')[1].replace(' 次', ''))
    tool_response_msg = int(lines[5].split('：')[1].replace(' 次', ''))
    
    # 查找token_usage行
    token_usage = ""
    for line in lines:
        if line.startswith('🧠 Token消耗情况：'):
            token_usage = line.replace('🧠 Token消耗情况：', '')
            break
    
    # 解析工具调用统计
    tool_list = []
    tool_counts = []
    in_tool_section = False
    for line in lines:
        if line.startswith('🛠️ 工具调用统计'):
            in_tool_section = True
            continue
        if in_tool_section:
            # 遇到下一个大标题就停止
            if line.startswith('💬 ') or line.startswith('⏰ ') or line.startswith('🧠 '):
                break
            line_stripped = line.strip()
            if line_stripped and '：' in line_stripped and not line_stripped.startswith('无工具调用记录'):
                parts = line_stripped.split('：')
                tool_name = parts[0]
                count = int(parts[1].replace(' 次', '').strip())
                tool_list.append(tool_name)
                tool_counts.append(count)
    
    # 解析时间维度统计数据
    time_labels = []
    time_total = []
    time_user = []
    time_assistant = []
    time_tool = []
    in_time_section = False
    time_unit = '天'
    for line in lines:
        if line.startswith('⏰ '):
            in_time_section = True
            if '按小时' in line:
                time_unit = '小时'
            continue
        if in_time_section and line.strip().startswith('20'):
            parts = line.strip().split('：')
            time_key = parts[0]
            stats_part = parts[1].split('|')
            total = int(stats_part[0].replace('总', '').replace('次', '').strip())
            user = int(stats_part[1].replace('用户', '').replace('次', '').strip())
            assistant = int(stats_part[2].replace('助手', '').replace('次', '').strip())
            tool = int(stats_part[3].replace('工具', '').replace('次', '').strip())
            time_labels.append(time_key)
            time_total.append(total)
            time_user.append(user)
            time_assistant.append(assistant)
            time_tool.append(tool)
    
    # 设置图片样式
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']
    plt.rcParams['axes.unicode_minus'] = False
    fig = plt.figure(figsize=(16, 14))
    
    # 使用网格布局避免重叠：3行2列，趋势图占满第3行
    # 子图1：消息类型占比饼图（左上）
    ax1 = plt.subplot2grid((3, 2), (0, 0))
    labels = [
        f'用户输入\n({format_num(user_msg)}次)', 
        f'助手回复\n({format_num(assistant_msg)}次)',
        f'工具返回\n({format_num(tool_response_msg)}次)'
    ]
    sizes = [user_msg, assistant_msg, tool_response_msg]
    colors = ['#FF9800', '#2196F3', '#FFC107']
    explode = (0.05, 0, 0)
    ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')
    ax1.set_title('消息类型占比分布', fontsize=14, pad=20)
    
    # 子图2：工具调用统计（右上）
    ax2 = plt.subplot2grid((3, 2), (0, 1))
    if len(tool_list) > 0:
        bars = ax2.bar(tool_list, tool_counts, color='#4CAF50', width=0.6)
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    format_num(height),
                    ha='center', va='bottom')
        ax2.set_title('工具调用次数统计（Top5）', fontsize=14, pad=20)
        ax2.set_ylabel('调用次数', fontsize=12)
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        plt.setp(ax2.get_xticklabels(), rotation=30, ha='right')
    else:
        ax2.text(0.5, 0.5, '当前时间范围内无工具调用记录', ha='center', va='center', fontsize=14, color='#666666')
        ax2.set_title('工具调用次数统计', fontsize=14, pad=20)
        ax2.axis('off')
    
    # 子图3：消息数量统计柱状图（左下，堆叠式展示助手回复中工具调用占比）
    ax3 = plt.subplot2grid((3, 2), (1, 0))
    metrics = ['总消息数', '用户输入', '助手回复', '工具返回']
    # 计算普通助手回复（不含工具调用）
    assistant_plain = assistant_msg - tool_call_msg
    # 画堆叠柱状图
    ax3.bar(metrics[0], total_msg, color='#607D8B', width=0.6)
    ax3.bar(metrics[1], user_msg, color='#FF9800', width=0.6)
    # 助手回复堆叠：普通回复+工具调用
    ax3.bar(metrics[2], assistant_plain, color='#2196F3', width=0.6, label='普通回复')
    ax3.bar(metrics[2], tool_call_msg, bottom=assistant_plain, color='#4CAF50', width=0.6, label='工具调用')
    ax3.bar(metrics[3], tool_response_msg, color='#FFC107', width=0.6)
    # 显示各柱子数值
    ax3.text(0, total_msg + 0.5, format_num(total_msg), ha='center')
    ax3.text(1, user_msg + 0.5, format_num(user_msg), ha='center')
    # 助手回复堆叠显示各部分数值和总数值
    ax3.text(2, assistant_plain/2, format_num(assistant_plain), ha='center', va='center', color='white', fontweight='bold')
    ax3.text(2, assistant_plain + tool_call_msg/2, format_num(tool_call_msg), ha='center', va='center', color='white', fontweight='bold')
    ax3.text(2, assistant_msg + 0.5, format_num(assistant_msg), ha='center', va='bottom')
    ax3.text(3, tool_response_msg + 0.5, format_num(tool_response_msg), ha='center')
    ax3.set_title('各类型消息数量统计', fontsize=14, pad=20)
    ax3.set_ylabel('次数', fontsize=12)
    ax3.legend()
    ax3.grid(axis='y', linestyle='--', alpha=0.7)
    plt.setp(ax3.get_xticklabels(), rotation=30, ha='right')
    
    # 子图4：工具调用占比饼图（右下）
    ax4 = plt.subplot2grid((3, 2), (1, 1))
    if len(tool_list) > 0:
        ax4.pie(tool_counts, labels=tool_list, autopct='%1.1f%%',
                colors=['#4CAF50', '#2196F3', '#FF9800', '#FFC107', '#9C27B0'],
                shadow=True, startangle=90)
        ax4.axis('equal')
        ax4.set_title('工具调用占比（Top5）', fontsize=14, pad=20)
    else:
        ax4.text(0.5, 0.5, '当前时间范围内无工具调用记录', ha='center', va='center', fontsize=14, color='#666666')
        ax4.set_title('工具调用占比', fontsize=14, pad=20)
        ax4.axis('off')
    
    # 子图5：时间维度使用趋势图（占满第3行）
    ax5 = plt.subplot2grid((3, 2), (2, 0), colspan=2)
    if len(time_labels) > 0:
        ax5.plot(time_labels, time_total, marker='o', label='总消息数', color='#607D8B', linewidth=2)
        ax5.plot(time_labels, time_user, marker='s', label='用户输入', color='#FF9800', linewidth=2)
        ax5.plot(time_labels, time_assistant, marker='^', label='助手回复', color='#2196F3', linewidth=2)
        ax5.plot(time_labels, time_tool, marker='*', label='工具消息', color='#4CAF50', linewidth=2)
        # 添加数据标签
        for x, y in enumerate(time_total):
            ax5.text(x, y + 0.5, format_num(y), ha='center')
        ax5.set_title(f'按{time_unit}使用趋势统计', fontsize=14, pad=20)
        ax5.set_xlabel(f'时间（{time_unit}）', fontsize=12, labelpad=15)
        ax5.set_ylabel('消息次数', fontsize=12)
        ax5.legend()
        ax5.grid(axis='y', linestyle='--', alpha=0.7)
        # 时间标签优化：小时级只显示时间部分，避免太长
        if time_unit == '小时':
            short_labels = [label.split(' ')[1] for label in time_labels]
            ax5.set_xticks(range(len(time_labels)))
            ax5.set_xticklabels(short_labels)
        plt.setp(ax5.get_xticklabels(), rotation=45, ha='right')
    else:
        ax5.text(0.5, 0.5, '当前时间范围内无统计数据', ha='center', va='center', fontsize=16, color='#666666')
        ax5.axis('off')
    
    # 添加整体标题和说明
    plt.suptitle(f'OpenClaw {period_name}使用统计\n统计时间范围：{time_range}', fontsize=16, y=0.98)
    plt.figtext(0.5, 0.01, f'注：{token_usage}\n工具调用已包含在助手回复计数中，工具返回为工具执行后返回的消息', ha='center', fontsize=10, color='#666666')
    
    # 调整布局，增加行间距避免重叠
    plt.tight_layout(pad=3.0, h_pad=4.0, w_pad=1.5)
    # 保存图片
    output_file = f'/root/.openclaw/workspace/usage_stats_{period}.png'
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    output_files.append((period_name, output_file, result))
    plt.close()
    print(f"✅ {period_name}统计图像已生成：{output_file}")

# 输出所有统计结果
print("\n" + "="*50 + "\n")
for period_name, _, result in output_files:
    print(f"🌟 {period_name}统计结果：")
    print(result)
    print("-"*50 + "\n")
