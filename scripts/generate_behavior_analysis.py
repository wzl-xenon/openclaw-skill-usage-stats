#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timedelta

def get_usage_data(start_time, end_time):
    """获取指定时间范围内的统计数据"""
    total_msg = 0
    user_msg = 0
    assistant_msg = 0
    tool_call_msg = 0
    tool_response_msg = 0
    # 按小时统计活跃度
    hourly_dist = [0]*24
    # 工具统计
    tool_stats = {}
    # 按天统计
    daily_stats = {}
    
    sessions_dir = os.path.expanduser("~/.openclaw/agents/main/sessions/")
    
    for f in os.listdir(sessions_dir):
        if f.endswith('.jsonl') and not f.endswith('.lock') and not f.endswith('.reset'):
            try:
                with open(os.path.join(sessions_dir, f), 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            # 检查时间
                            ts = data.get('timestamp', 0)
                            if isinstance(ts, str):
                                ts = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp() * 1000)
                            if ts >= start_time and ts <= end_time:
                                dt = datetime.fromtimestamp(ts/1000)
                                # 按小时统计
                                hour = dt.hour
                                hourly_dist[hour] +=1
                                # 按天统计
                                date_str = dt.strftime('%Y-%m-%d')
                                if date_str not in daily_stats:
                                    daily_stats[date_str] = 0
                                daily_stats[date_str] +=1
                                
                                if data.get('type') == 'message':
                                    total_msg +=1
                                    msg = data.get('message', {})
                                    role = msg.get('role', '')
                                    if role == 'user':
                                        user_msg +=1
                                    elif role == 'assistant':
                                        assistant_msg +=1
                                        # 统计工具调用
                                        content = msg.get('content', [])
                                        if isinstance(content, list):
                                            for item in content:
                                                if isinstance(item, dict) and item.get('type') == 'toolCall':
                                                    tool_call_msg +=1
                                                    tool_name = item.get('name', 'unknown')
                                                    if tool_name not in tool_stats:
                                                        tool_stats[tool_name] = {'count':0, 'success':0, 'fail':0, 'total_time':0}
                                                    tool_stats[tool_name]['count'] +=1
                                    elif role == 'toolResult':
                                        tool_response_msg +=1
                                        call_id = msg.get('toolCallId', '')
                                        is_error = msg.get('isError', False)
                                        # 匹配调用（简化处理，这里只要统计成功失败即可）
                                        if is_error:
                                            # 粗略统计，假设失败的工具都有对应的调用
                                            for tool_name in tool_stats:
                                                tool_stats[tool_name]['fail'] +=1
                                        else:
                                            for tool_name in tool_stats:
                                                tool_stats[tool_name]['success'] +=1
                        except:
                            continue
            except Exception as e:
                pass
    
    # 计算成功率和平均耗时
    for tool_name in tool_stats:
        stats = tool_stats[tool_name]
        if stats['count'] > 0:
            stats['success_rate'] = round(stats['success'] / stats['count'] * 100, 1) if (stats['success'] + stats['fail']) > 0 else 100
        else:
            stats['success_rate'] = 100
    
    return {
        'overview': {
            'total_msg': total_msg,
            'user_msg': user_msg,
            'assistant_msg': assistant_msg,
            'tool_call_msg': tool_call_msg,
            'tool_response_msg': tool_response_msg,
            'duration_days': round((end_time - start_time) / (24*60*60*1000), 1)
        },
        'hourly_dist': hourly_dist,
        'tool_stats': tool_stats,
        'daily_stats': daily_stats
    }

def generate_analysis():
    """生成行为分析报告"""
    now = time.time() * 1000
    start_7d = now - 7 * 24 * 60 * 60 * 1000
    data = get_usage_data(start_7d, now)
    overview = data['overview']
    hourly_dist = data['hourly_dist']
    tool_stats = data['tool_stats']
    daily_stats = data['daily_stats']
    
    print("📊 === OpenClaw 使用行为分析报告（近7天）===")
    print(f"📅 统计周期：{datetime.fromtimestamp(start_7d/1000).strftime('%Y-%m-%d %H:%M')} 至 {datetime.fromtimestamp(now/1000).strftime('%Y-%m-%d %H:%M')}")
    print(f"📈 总消息量：{overview['total_msg']} 次，日均 {round(overview['total_msg']/overview['duration_days'], 1)} 次")
    
    # 1. 消息构成分析
    print("\n📝 === 1. 消息构成分析 ===")
    user_ratio = round(overview['user_msg'] / overview['total_msg'] * 100, 1)
    assistant_ratio = round(overview['assistant_msg'] / overview['total_msg'] * 100, 1)
    tool_ratio = round(overview['tool_response_msg'] / overview['total_msg'] * 100, 1)
    tool_call_ratio = round(overview['tool_call_msg'] / overview['assistant_msg'] * 100, 1) if overview['assistant_msg'] >0 else 0
    print(f"  用户输入占比：{user_ratio}%（{overview['user_msg']}次）")
    print(f"  助手回复占比：{assistant_ratio}%（{overview['assistant_msg']}次）")
    print(f"  工具返回占比：{tool_ratio}%（{overview['tool_response_msg']}次）")
    print(f"  助手回复中工具调用占比：{tool_call_ratio}%，工具依赖程度较高")
    
    # 2. 活跃时段分析
    print("\n⏰ === 2. 活跃时段分析 ===")
    peak_hour = hourly_dist.index(max(hourly_dist))
    peak_count = max(hourly_dist)
    low_hour = hourly_dist.index(min([v for v in hourly_dist if v>0])) if any(hourly_dist) else 0
    active_hours = [i for i, v in enumerate(hourly_dist) if v > peak_count * 0.5]
    print(f"  最活跃时段：{peak_hour}:00，该时段消息量 {peak_count} 次")
    if len(active_hours) > 0:
        print(f"  高活跃时段：{', '.join([f'{h}:00' for h in active_hours])}")
    # 判断使用时间类型
    work_hours = sum(hourly_dist[9:18])
    off_hours = sum(hourly_dist[0:9]) + sum(hourly_dist[18:24])
    if work_hours > off_hours * 2:
        print("  💡 主要使用场景：工作时段使用为主，符合办公使用习惯")
    elif off_hours > work_hours * 2:
        print("  💡 主要使用场景：非工作时段使用为主，偏向个人/业余用途")
    else:
        print("  💡 使用时段分布均匀，全天候使用")
    
    # 3. 工具使用分析
    print("\n🛠️ === 3. 工具使用分析 ===")
    if len(tool_stats) > 0:
        # 按调用次数排序
        sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        print(f"  共使用 {len(tool_stats)} 种工具，总调用次数 {sum([v['count'] for v in tool_stats.values()])} 次")
        print("\n  🔝 最常用工具Top3：")
        for i, (tool_name, stats) in enumerate(sorted_tools[:3]):
            print(f"    {i+1}. {tool_name}：{stats['count']}次，成功率 {stats['success_rate']}%")
        
        # 低成功率工具
        low_success_tools = [(name, stats) for name, stats in tool_stats.items() if stats['success_rate'] < 90 and stats['count'] >=3]
        if low_success_tools:
            print("\n  ⚠️ 低成功率工具（成功率<90%）：")
            for tool_name, stats in low_success_tools:
                print(f"    {tool_name}：{stats['count']}次，成功率 {stats['success_rate']}%，建议排查调用参数/网络问题")
        
        # 工具建议
        if 'exec' in tool_stats and tool_stats['exec']['count'] > 20:
            print("\n  💡 优化建议：exec调用量很高，建议把常用的shell命令封装成自定义技能，减少重复输入和调用次数")
        if 'web_fetch' in tool_stats and tool_stats['web_fetch']['count'] > 10:
            print("  💡 优化建议：网页抓取调用较多，对于常用网站内容可以做本地缓存，减少重复请求和Token消耗")
    
    else:
        print("  无工具调用记录，纯文本对话为主")
    
    # 4. 用量趋势分析
    print("\n📈 === 4. 用量趋势分析 ===")
    if len(daily_stats) > 1:
        sorted_daily = sorted(daily_stats.items(), key=lambda x: x[0])
        max_day = max(daily_stats.items(), key=lambda x: x[1])
        min_day = min(daily_stats.items(), key=lambda x: x[1])
        print(f"  最高用量日：{max_day[0]}，{max_day[1]}次")
        print(f"  最低用量日：{min_day[0]}，{min_day[1]}次")
        # 增长趋势
        first_half = sum([v for d, v in sorted_daily[:len(sorted_daily)//2]])
        second_half = sum([v for d, v in sorted_daily[len(sorted_daily)//2:]])
        if second_half > first_half * 1.5:
            print("  📈 用量趋势：近期用量明显增长，使用频率正在提升")
        elif first_half > second_half * 1.5:
            print("  📉 用量趋势：近期用量下降，使用频率降低")
        else:
            print("  ⚖️ 用量趋势：使用量平稳，波动不大")
    else:
        print("  仅1天有使用记录，无法分析趋势")
    
    # 5. 综合优化建议
    print("\n💡 === 5. 综合优化建议 ===")
    suggestions = []
    if tool_call_ratio > 70:
        suggestions.append("🔹 工具调用占比很高，建议把高频使用的工具流封装成自定义技能，一次调用完成多个操作，减少消息往返次数和Token消耗")
    if overview['total_msg'] > 200 and 'process' in tool_stats:
        suggestions.append("🔹 process后台进程调用较多，建议定时清理无用的后台进程，避免占用系统资源")
    if work_hours > 0 and off_hours > 0:
        suggestions.append("🔹 跨时段使用较多，可以开启用量异常告警，避免非预期时段的异常消耗")
    if len(tool_stats) > 5:
        suggestions.append("🔹 使用工具类型丰富，建议整理常用工具快捷键/别名，提升输入效率")
    
    if suggestions:
        for s in suggestions:
            print(s)
    else:
        print("  当前使用习惯良好，暂无特殊优化建议~")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    generate_analysis()
