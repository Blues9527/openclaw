#!/usr/bin/env python3
"""
山子高科(000981) 历史涨幅超过7%日期统计
分析次日平均涨幅
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

print("=" * 60)
print("山子高科(000981) 历史涨幅>7% 统计分析")
print("=" * 60)

# 获取历史数据 (2020年至今)
print("\n📥 正在获取历史数据...")
try:
    df = ak.stock_zh_a_hist(symbol="000981", start_date="20200101", end_date="20260317")
    print(f"✅ 获取成功，共 {len(df)} 条日K线数据")
except Exception as e:
    print(f"❌ 获取数据失败: {e}")
    exit(1)

# 数据处理
df.columns = ['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
df['日期'] = pd.to_datetime(df['日期'])
df['涨跌幅'] = pd.to_numeric(df['涨跌幅'])
df = df.sort_values('日期').reset_index(drop=True)

# 筛选涨幅>7%的日期
df_up7 = df[df['涨跌幅'] > 7].copy()
print(f"\n📊 涨幅超过7%的交易日: {len(df_up7)} 天")

if len(df_up7) == 0:
    print("没有找到涨幅超过7%的日期")
    exit(0)

print("\n" + "=" * 60)
print("涨幅 >7% 日期明细")
print("=" * 60)

results = []
for idx, row in df_up7.iterrows():
    date = row['日期'].strftime('%Y-%m-%d')
    pct = row['涨跌幅']
    close = row['收盘']
    
    # 找次日
    current_idx = df[df['日期'] == row['日期']].index[0]
    if current_idx + 1 < len(df):
        next_row = df.iloc[current_idx + 1]
        next_date = next_row['日期'].strftime('%Y-%m-%d')
        next_pct = next_row['涨跌幅']
        next_close = next_row['收盘']
    else:
        next_date = "无数据"
        next_pct = None
        next_close = None
    
    results.append({
        'date': date,
        'pct': pct,
        'close': close,
        'next_date': next_date,
        'next_pct': next_pct,
        'next_close': next_close
    })
    
    status = "🔴" if next_pct and next_pct > 0 else "🟢" if next_pct and next_pct < 0 else "⚪"
    next_info = f"{next_pct:+.2f}%" if next_pct else "N/A"
    print(f"{date} | 涨幅: {pct:+.2f}% | 收盘: {close:.2f} | 次日: {next_info} {status}")

# 统计次日涨幅
valid_next = [r for r in results if r['next_pct'] is not None]
if valid_next:
    avg_next = sum(r['next_pct'] for r in valid_next) / len(valid_next)
    up_count = sum(1 for r in valid_next if r['next_pct'] > 0)
    down_count = sum(1 for r in valid_next if r['next_pct'] < 0)
    flat_count = sum(1 for r in valid_next if r['next_pct'] == 0)
    
    print("\n" + "=" * 60)
    print("📈 次日走势统计")
    print("=" * 60)
    print(f"样本数: {len(valid_next)} 次")
    print(f"次日平均涨幅: {avg_next:+.2f}%")
    print(f"上涨次数: {up_count} ({up_count/len(valid_next)*100:.1f}%)")
    print(f"下跌次数: {down_count} ({down_count/len(valid_next)*100:.1f}%)")
    print(f"平盘次数: {flat_count} ({flat_count/len(valid_next)*100:.1f}%)")
    
    # 最大涨跌幅
    max_up = max(r['next_pct'] for r in valid_next)
    max_down = min(r['next_pct'] for r in valid_next)
    print(f"\n次日最大涨幅: {max_up:+.2f}%")
    print(f"次日最大跌幅: {max_down:+.2f}%")
    
    # 近期表现 (2024-2025)
    recent = [r for r in valid_next if r['date'] >= '2024-01-01']
    if recent:
        avg_recent = sum(r['next_pct'] for r in recent) / len(recent)
        print(f"\n📅 2024年以来:")
        print(f"  样本数: {len(recent)} 次")
        print(f"  次日平均涨幅: {avg_recent:+.2f}%")

print("\n" + "=" * 60)
print("数据来源: akshare (东方财富)")
print("=" * 60)
