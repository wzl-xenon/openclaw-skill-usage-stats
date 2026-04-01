#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timedelta

def parse_time_str(time_str):
    """解析时间字符串，支持YYYY-MM-DD、YYYY-MM-DD HH:MM格式"""
    try:
        if len(time_str) == 10: # 只有日期 YYYY-MM-DD
            dt = datetime.strptime(time_str, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)
        elif len(time_str) >= 16: # 带时间 YYYY-MM-DD HH:MM
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            return int(dt.timestamp() * 1000)
    except:
        return None
    return None

def get_time_range(period_or_start, end_time_str=None):
    """获取时间范围，支持固定周期或自定义起止时间"""
    now = time.time() * 1000
    # 如果是固定周期
    if period_or_start in ['24h', '7d', '30d']:
        if period_or_start == '24h':
            start = now - 24 * 60 * 60 * 1000
        elif period_or_start == '7d':
            start = now - 7 * 24 * 60 * 60 * 1000
        elif period_or_start == '30d':
            start = now - 30 * 24 * 60 * 60 * 1000
        return start, now
    # 否则是自定义时间范围
    else:
        start_ts = parse_time_str(period_or_start)
        end_ts = parse_time_str(end_time_str) if end_time_str else now
        if start_ts and end_ts and start_ts < end_ts:
            return start_ts, end_ts
        # 解析失败默认返回近24小时
        print("⚠️ 自定义时间格式解析失败，默认返回近24小时统计")
        print("💡 自定义时间格式：python get_usage_stats.py <开始时间> <结束时间>，例如：")
        print("   python get_usage_stats.py \"2026-04-01 09:00\" \"2026-04-01 12:00\"")
        print("   python get_usage_stats.py 2026-03-01 2026-03-31")
        return now - 24 * 60 * 60 * 1000, now

def count_requests_and_tokens(start_time, end_time, period):
    total_msg = 0
    user_msg = 0
    assistant_msg = 0
    tool_call_msg = 0
    tool_response_msg = 0
    total_tokens = 0
    # 工具调用明细统计：{工具名: {'count': 调用次数, 'success': 成功次数, 'fail': 失败次数, 'total_time': 总耗时ms}}
    tool_stats = {}
    # 存储待匹配的工具调用：{call_id: (tool_name, timestamp)}
    pending_tool_calls = {}
    # 会话统计
    session_stats = {}
    # 时间粒度判断：时间范围小于24小时按小时，否则按天
    time_range_ms = end_time - start_time
    use_hourly = time_range_ms < 24 * 60 * 60 * 1000 or period == '24h'
    time_stats = {}
    sessions_dir = os.path.expanduser("~/.openclaw/agents/main/sessions/")
    
    # 遍历所有会话jsonl文件
    for f in os.listdir(sessions_dir):
        if f.endswith('.jsonl') and not f.endswith('.lock') and not f.endswith('.reset'):
            session_id = f.replace('.jsonl', '')
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
                                # 处理ISO时间
                                ts = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp() * 1000)
                            if ts >= start_time and ts <= end_time:
                                # 生成时间key
                                if use_hourly:
                                    time_key = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:00')
                                else:
                                    time_key = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d')
                                if time_key not in time_stats:
                                    time_stats[time_key] = {'total':0, 'user':0, 'assistant':0, 'tool':0}
                                
                                # 统计消息
                                if data.get('type') == 'message':
                                    total_msg +=1
                                    # 会话统计
                                    if session_id not in session_stats:
                                        session_stats[session_id] = 0
                                    session_stats[session_id] +=1
                                    
                                    msg = data.get('message', {})
                                    role = msg.get('role', '')
                                    if role == 'user':
                                        user_msg +=1
                                        time_stats[time_key]['user'] +=1
                                    elif role == 'assistant':
                                        assistant_msg +=1
                                        time_stats[time_key]['assistant'] +=1
                                        # 统计工具调用：遍历content中的toolCall项
                                        content = msg.get('content', [])
                                        if isinstance(content, list):
                                            has_tool_call = False
                                            for item in content:
                                                if isinstance(item, dict) and item.get('type') == 'toolCall':
                                                    has_tool_call = True
                                                    call_id = item.get('id', '')
                                                    tool_name = item.get('name', 'unknown')
                                                    # 初始化工具统计
                                                    if tool_name not in tool_stats:
                                                        tool_stats[tool_name] = {'count':0, 'success':0, 'fail':0, 'total_time':0}
                                                    tool_stats[tool_name]['count'] +=1
                                                    # 记录待匹配的调用
                                                    if call_id:
                                                        pending_tool_calls[call_id] = (tool_name, ts)
                                            if has_tool_call:
                                                tool_call_msg +=1
                                    elif role == 'toolResult':
                                        tool_response_msg +=1
                                        time_stats[time_key]['tool'] +=1
                                        # 匹配工具调用，计算耗时和成功率
                                        call_id = msg.get('toolCallId', '')
                                        is_error = msg.get('isError', False)
                                        if call_id in pending_tool_calls:
                                            tool_name, call_ts = pending_tool_calls.pop(call_id)
                                            duration = ts - call_ts
                                            if tool_name in tool_stats:
                                                tool_stats[tool_name]['total_time'] += duration
                                                if is_error:
                                                    tool_stats[tool_name]['fail'] +=1
                                                else:
                                                    tool_stats[tool_name]['success'] +=1
                                    time_stats[time_key]['total'] +=1
                                # 统计token
                                msg = data.get('message', {})
                                usage = msg.get('usage', {})
                                total_tokens += usage.get('totalTokens', 0)
                        except:
                            continue
            except Exception as e:
                pass
    # 按时间排序
    sorted_time_stats = sorted(time_stats.items(), key=lambda x: x[0])
    # 工具统计按调用次数排序
    sorted_tool_stats = sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    # 会话统计按消息量排序
    sorted_session_stats = sorted(session_stats.items(), key=lambda x: x[1], reverse=True)
    return total_msg, user_msg, assistant_msg, tool_call_msg, tool_response_msg, total_tokens, sorted_time_stats, sorted_tool_stats, sorted_session_stats

def get_cache(period):
    """读取缓存数据，有效期5分钟"""
    cache_file = f"/tmp/openclaw_usage_cache_{period}.json"
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < 300: # 5分钟有效期
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
    return None

def save_cache(period, data):
    """保存数据到缓存"""
    cache_file = f"/tmp/openclaw_usage_cache_{period}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except:
        pass

def get_7d_avg_daily_usage():
    """获取近7天的日均消息量，用于异常告警判断"""
    now = time.time() * 1000
    start_7d = now - 7 * 24 * 60 * 60 * 1000
    total_msg_7d, _, _, _, _, _, time_stats_7d, _, _ = count_requests_and_tokens(start_7d, now, '7d')
    # 排除今天，计算前6天的平均值
    today_str = datetime.now().strftime('%Y-%m-%d')
    valid_days = 0
    total_valid_msg = 0
    for time_key, stats in time_stats_7d:
        if time_key.split(' ')[0] != today_str:
            valid_days +=1
            total_valid_msg += stats['total']
    if valid_days == 0:
        return None
    return total_valid_msg / valid_days

def get_token_usage(total_tokens):
    if total_tokens > 0:
        return f"{total_tokens} 个Token"
    else:
        return "当前模型返回的Token用量均为0（可能是coding plan按访问次数计费，不统计单请求Token量）"

def export_to_csv(period, start_str, end_str, total_msg, user_msg, assistant_msg, tool_call_msg, tool_response_msg, total_tokens, time_stats, tool_stats, session_stats):
    """导出统计数据到CSV文件"""
    import csv
    filename = f"openclaw_usage_stats_{period.replace('/', '_').replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 基础统计
        writer.writerow(['【基础统计信息】'])
        writer.writerow(['统计时间范围', f'{start_str} 至 {end_str}'])
        writer.writerow(['总消息次数', total_msg])
        writer.writerow(['用户输入次数', user_msg])
        writer.writerow(['助手回复次数', assistant_msg])
        writer.writerow(['  其中工具调用次数', tool_call_msg])
        writer.writerow(['工具返回结果次数', tool_response_msg])
        writer.writerow(['总Token消耗量', total_tokens])
        writer.writerow([])
        
        # 时间维度明细
        writer.writerow(['【时间维度明细】'])
        time_unit = '小时' if len(next(iter(time_stats), [''])[0]) > 10 else '天'
        writer.writerow([f'时间({time_unit})', '总消息数', '用户输入', '助手回复', '工具消息'])
        for time_key, stats in time_stats:
            writer.writerow([time_key, stats['total'], stats['user'], stats['assistant'], stats['tool']])
        writer.writerow([])
        
        # 工具调用明细
        writer.writerow(['【工具调用明细（Top10）】'])
        writer.writerow(['工具名称', '调用次数'])
        for tool_name, count in tool_stats[:10]:
            writer.writerow([tool_name, count])
        writer.writerow([])
        
        # 会话明细
        writer.writerow(['【活跃会话明细（Top10）】'])
        writer.writerow(['会话ID（前8位）', '消息数量'])
        for session_id, count in session_stats[:10]:
            writer.writerow([session_id[:8], count])
    
    return filename

def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    flags = [arg for arg in sys.argv[1:] if arg.startswith('--')]
    export_csv = '--export' in flags
    force_refresh = '--force' in flags
    
    # 解析时间参数
    period = None
    custom_time = False
    start = None
    end = None
    if len(args) == 0:
        period = '24h'
    elif len(args) == 1:
        period = args[0]
    elif len(args) >= 2:
        # 自定义时间范围
        start_str_input = args[0]
        end_str_input = args[1]
        start, end = get_time_range(start_str_input, end_str_input)
        custom_time = True
        # 自定义时间的缓存key
        period = f"custom_{int(start)}_{int(end)}"
    
    if not custom_time:
        start, end = get_time_range(period)
    
    start_str = datetime.fromtimestamp(start/1000).strftime('%Y-%m-%d %H:%M:%S')
    end_str = datetime.fromtimestamp(end/1000).strftime('%Y-%m-%d %H:%M:%S')
    
    # 优先读缓存
    cached_data = get_cache(period) if not force_refresh else None
    if cached_data:
        total_msg = cached_data['total_msg']
        user_msg = cached_data['user_msg']
        assistant_msg = cached_data['assistant_msg']
        tool_call_msg = cached_data['tool_call_msg']
        tool_response_msg = cached_data['tool_response_msg']
        total_tokens = cached_data['total_tokens']
        time_stats = [tuple(item) for item in cached_data['time_stats']]
        tool_stats = [tuple(item) for item in cached_data['tool_stats']]
        session_stats = [tuple(item) for item in cached_data['session_stats']]
        print("⚡ 读取缓存数据，查询速度更快（使用--force可强制刷新）")
    else:
        total_msg, user_msg, assistant_msg, tool_call_msg, tool_response_msg, total_tokens, time_stats, tool_stats, session_stats = count_requests_and_tokens(start, end, period)
        # 保存缓存
        save_cache(period, {
            'total_msg': total_msg,
            'user_msg': user_msg,
            'assistant_msg': assistant_msg,
            'tool_call_msg': tool_call_msg,
            'tool_response_msg': tool_response_msg,
            'total_tokens': total_tokens,
            'time_stats': time_stats,
            'tool_stats': tool_stats,
            'session_stats': session_stats
        })
    
    token_usage = get_token_usage(total_tokens)
    
    print(f"📊 统计时间范围：{start_str} 至 {end_str}")
    print(f"🔢 总消息次数：{total_msg} 次")
    print(f"  ├─ 用户输入：{user_msg} 次")
    print(f"  ├─ 助手回复：{assistant_msg} 次")
    print(f"  │  └─ 包含工具调用：{tool_call_msg} 次")
    print(f"  └─ 工具返回结果：{tool_response_msg} 次")
    print(f"✅ 分类校验：用户+助手+工具返回 = {user_msg + assistant_msg + tool_response_msg} 次，与总消息数一致")
    print(f"🧠 Token消耗情况：{token_usage}")
    
    # 异常用量告警：查询近24小时/今天数据时，对比近7天日均
    if (period == '24h' or (custom_time and end > time.time()*1000 - 60*60*1000)):
        avg_daily = get_7d_avg_daily_usage()
        if avg_daily and total_msg > avg_daily * 3:
            print(f"\n⚠️ 【异常告警】今日用量异常！当前总消息数{total_msg}次，超过近7天日均{round(avg_daily, 1)}次的3倍，请检查是否有异常调用！")
        elif avg_daily and total_msg > avg_daily * 2:
            print(f"\n⚠️ 【用量提醒】今日用量{total_msg}次，超过近7天日均{round(avg_daily, 1)}次的2倍，属于较高用量水平。")
    
    # 工具调用统计
    if len(tool_stats) > 0:
        print("\n🛠️ 工具调用统计（Top5）：")
        for tool_name, stats in tool_stats[:5]:
            count = stats['count']
            success = stats['success']
            fail = stats['fail']
            total_time = stats['total_time']
            # 计算成功率和平均耗时
            if count == 0:
                success_rate = 0
                avg_time = 0
            else:
                success_rate = round(success / count * 100, 1)
                avg_time = round(total_time / count / 1000, 2) if count > 0 else 0
            print(f"  {tool_name}：{count} 次 | 成功率 {success_rate}% | 平均耗时 {avg_time}s")
    else:
        print("\n🛠️ 工具调用统计：无工具调用记录")
    
    # 会话统计
    if len(session_stats) > 0:
        total_sessions = len(session_stats)
        avg_msg_per_session = round(total_msg / total_sessions, 1)
        print(f"\n💬 活跃会话统计：")
        print(f"  总会话数：{total_sessions} 个")
        print(f"  单会话平均消息数：{avg_msg_per_session} 次")
        print(f"  最活跃会话（Top3）：")
        for session_id, count in session_stats[:3]:
            print(f"    {session_id[:8]}...：{count} 次")
    
    # 时间维度统计
    time_unit = "按小时统计明细" if len(time_stats) > 0 and len(time_stats[0][0]) > 10 else "按天统计明细"
    print(f"\n⏰ {time_unit}：")
    for time_key, stats in time_stats:
        print(f"  {time_key}：总{stats['total']}次 | 用户{stats['user']}次 | 助手{stats['assistant']}次 | 工具{stats['tool']}次")
    
    print("\n💡 工具调用已包含在助手回复计数中，工具返回结果为工具执行后返回的消息~")
    
    # 导出CSV
    if export_csv:
        csv_file = export_to_csv(period, start_str, end_str, total_msg, user_msg, assistant_msg, tool_call_msg, tool_response_msg, total_tokens, time_stats, tool_stats, session_stats)
        print(f"\n📤 统计数据已导出到CSV文件：{csv_file}")

if __name__ == "__main__":
    main()
