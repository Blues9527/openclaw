#!/usr/bin/env python3
import urllib.request
import ssl
import json
import re
from datetime import datetime

# 创建不验证证书的上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_daily_kline(symbol, days=10):
    """获取日线数据
    新浪K线接口: https://quotes.sina.cn/cn/api/jsonp_v2.php/.../CN_MarketDataService.getKLineData
    scale=240 表示日线 (240分钟)
    """
    url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{symbol}=/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}"
    
    try:
        req = urllib.request.Request(url, headers={
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        text = resp.read().decode('utf-8')
        
        # 解析JSONP: var _xxx=([...])
        match = re.search(r"\(\[(.*)\]\)", text, re.DOTALL)
        if not match:
            return []
        
        data = json.loads("[" + match.group(1) + "]")
        result = []
        for item in data:
            result.append({
                "date": item["day"][:10] if "day" in item else item.get("d", "")[:10],  # YYYY-MM-DD
                "open": float(item.get("open", 0)),
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "close": float(item.get("close", 0)),
                "volume": int(item.get("volume", 0)),
                "amount": float(item.get("amount", 0)) if "amount" in item else 0
            })
        return result
    except Exception as e:
        print(f"获取K线数据错误: {e}")
        return []

def calculate_ma(data, period):
    """计算均线"""
    if len(data) < period:
        return None
    closes = [d['close'] for d in data[-period:]]
    return sum(closes) / period

def calculate_rsi(data, period=6):
    """计算RSI (默认6日)"""
    if len(data) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, period + 1):
        change = data[-i]['close'] - data[-(i+1)]['close']
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_stock(code, name):
    """分析股票"""
    symbol = f"sz{code}" if code.startswith(("0", "3")) else f"sh{code}"
    
    print("=" * 70)
    print(f"📊 {name} ({code}) - 近5日走势分析")
    print("=" * 70)
    print()
    
    # 获取10日数据（用于计算均线，但只展示最近5日）
    data = fetch_daily_kline(symbol, 10)
    
    if len(data) < 5:
        print(f"❌ 数据不足，仅获取到 {len(data)} 天")
        return
    
    # 取最近5日
    recent_5 = data[-5:]
    
    print("【近5日行情数据】")
    print("-" * 70)
    print(f"{'日期':<12} {'开盘':<8} {'最高':<8} {'最低':<8} {'收盘':<8} {'涨跌':<8} {'成交量':<12}")
    print("-" * 70)
    
    total_change = 0
    total_volume = 0
    avg_volume_5 = 0
    
    for i, day in enumerate(recent_5):
        if i == 0:
            change_pct = 0
        else:
            change_pct = (day['close'] - recent_5[i-1]['close']) / recent_5[i-1]['close'] * 100
        
        change_symbol = "+" if change_pct >= 0 else ""
        total_change += change_pct
        total_volume += day['volume']
        
        print(f"{day['date']:<12} {day['open']:<8.2f} {day['high']:<8.2f} "
              f"{day['low']:<8.2f} {day['close']:<8.2f} "
              f"{change_symbol}{change_pct:<7.2f}% {day['volume']/10000:<11.1f}万")
    
    avg_volume_5 = total_volume / 5
    latest = recent_5[-1]
    first = recent_5[0]
    total_return = (latest['close'] - first['close']) / first['close'] * 100
    
    print("-" * 70)
    print(f"5日累计涨跌: {'+' if total_return >= 0 else ''}{total_return:.2f}%")
    print(f"5日均量: {avg_volume_5/10000:.1f}万手")
    print()
    
    # 技术指标分析
    print("【技术指标分析】")
    print("-" * 70)
    
    # 计算均线
    ma5 = calculate_ma(data, 5)
    ma10 = calculate_ma(data, 10) if len(data) >= 10 else None
    ma20 = calculate_ma(data, 20) if len(data) >= 20 else None
    
    print(f"📈 均线系统:")
    print(f"   MA5:  {ma5:.2f}")
    if ma10:
        print(f"   MA10: {ma10:.2f}")
    if ma20:
        print(f"   MA20: {ma20:.2f}")
    
    # 均线排列
    if ma10 and ma20:
        if latest['close'] > ma5 > ma10 > ma20:
            print(f"   ✅ 多头排列 (MA5>MA10>MA20)，趋势强劲")
        elif latest['close'] < ma5 < ma10 < ma20:
            print(f"   ⚠️ 空头排列 (MA5<MA10<MA20)，趋势弱势")
        else:
            print(f"   📊 均线交织，趋势震荡")
    
    print()
    
    # RSI分析
    rsi6 = calculate_rsi(data, 6)
    if rsi6:
        print(f"🌡️ RSI(6): {rsi6:.1f}", end=" ")
        if rsi6 > 70:
            print("(超买区 ⚠️)")
        elif rsi6 < 30:
            print("(超卖区 💡)")
        else:
            print("(正常区 ✅)")
    
    print()
    
    # 成交量分析
    print("📊 成交量分析:")
    latest_volume = latest['volume']
    vol_ratio = latest_volume / avg_volume_5
    print(f"   最新成交量: {latest_volume/10000:.1f}万手")
    print(f"   量比(与5日均量): {vol_ratio:.2f}x", end=" ")
    if vol_ratio > 2:
        print("(🔥 显著放量)")
    elif vol_ratio > 1.5:
        print("(📈 温和放量)")
    elif vol_ratio < 0.5:
        print("(📉 明显缩量)")
    else:
        print("(➡️ 正常)")
    
    print()
    
    # 关键价位
    print("【关键价位】")
    print("-" * 70)
    high_5 = max(d['high'] for d in recent_5)
    low_5 = min(d['low'] for d in recent_5)
    print(f"   5日最高价: {high_5:.2f}")
    print(f"   5日最低价: {low_5:.2f}")
    print(f"   当前价位区间: {(latest['close']-low_5)/(high_5-low_5)*100:.1f}% (从最低到最高)")
    
    # 支撑/压力位估算
    support = min(d['low'] for d in recent_5[-3:])  # 近3日最低
    resistance = max(d['high'] for d in recent_5[-3:])  # 近3日最高
    print(f"   支撑位: {support:.2f}")
    print(f"   压力位: {resistance:.2f}")
    print()
    
    # 走势特征分析
    print("【走势特征】")
    print("-" * 70)
    
    up_days = sum(1 for i in range(1, 5) if recent_5[i]['close'] > recent_5[i-1]['close'])
    down_days = 4 - up_days
    
    print(f"   上涨天数: {up_days}天")
    print(f"   下跌天数: {down_days}天")
    
    # 趋势判断
    if total_return > 5:
        trend = "📈 强势上涨"
    elif total_return > 0:
        trend = "📊 温和上涨"
    elif total_return > -5:
        trend = "📉 温和调整"
    else:
        trend = "📉 明显下跌"
    print(f"   趋势判断: {trend}")
    
    # 波动性
    daily_changes = []
    for i in range(1, 5):
        change = abs((recent_5[i]['close'] - recent_5[i-1]['close']) / recent_5[i-1]['close'] * 100)
        daily_changes.append(change)
    avg_change = sum(daily_changes) / len(daily_changes)
    print(f"   平均日振幅: {avg_change:.2f}%")
    
    print()
    
    # 交易策略建议
    print("=" * 70)
    print("💡 下个交易日交易策略建议")
    print("=" * 70)
    print()
    
    # 综合评分
    score = 50  # 基础分
    reasons = []
    
    # 趋势加分
    if total_return > 3:
        score += 10
        reasons.append("近期上涨趋势")
    elif total_return < -3:
        score -= 10
        reasons.append("近期下跌趋势")
    
    # 均线加分
    if ma5 and latest['close'] > ma5:
        score += 10
        reasons.append("站在MA5之上")
    elif ma5:
        score -= 5
        reasons.append("跌破MA5支撑")
    
    if ma10 and latest['close'] > ma10:
        score += 5
    
    # RSI调整
    if rsi6:
        if rsi6 > 75:
            score -= 15
            reasons.append("RSI超买，短期或有回调")
        elif rsi6 > 65:
            score -= 5
            reasons.append("RSI偏高")
        elif rsi6 < 25:
            score += 15
            reasons.append("RSI超卖，或有反弹")
        elif rsi6 < 35:
            score += 5
            reasons.append("RSI偏低")
    
    # 成交量
    if vol_ratio > 2:
        if total_return > 0:
            score += 10
            reasons.append("放量上涨，资金活跃")
        else:
            score -= 10
            reasons.append("放量下跌，注意风险")
    elif vol_ratio < 0.5:
        score -= 5
        reasons.append("成交量萎缩，观望情绪浓")
    
    # 位置判断
    position_ratio = (latest['close']-low_5)/(high_5-low_5) if high_5 > low_5 else 0.5
    if position_ratio > 0.8:
        score -= 10
        reasons.append("接近5日高点，注意回调风险")
    elif position_ratio < 0.2:
        score += 10
        reasons.append("接近5日低点，或有支撑")
    
    # 输出建议
    if score >= 70:
        recommendation = "🚀 积极看多"
        action = "可考虑逢低买入或持有"
    elif score >= 55:
        recommendation = "📈 谨慎看多"
        action = "可小仓位参与或继续持有"
    elif score >= 45:
        recommendation = "➡️ 中性观望"
        action = "保持观望，等待方向明确"
    elif score >= 30:
        recommendation = "📉 谨慎看空"
        action = "考虑减仓或止盈"
    else:
        recommendation = "⚠️ 规避风险"
        action = "建议离场观望"
    
    print(f"综合评分: {score}/100")
    print(f"策略建议: {recommendation}")
    print(f"操作建议: {action}")
    print()
    
    if reasons:
        print("📋 关键因素:")
        for r in reasons:
            print(f"   • {r}")
    print()
    
    # 具体交易计划
    print("【具体交易计划】")
    print("-" * 70)
    
    # 买入计划
    if score >= 55:
        buy_price = max(support * 0.99, latest['close'] * 0.98)
        print(f"📥 买入参考价: {buy_price:.2f} (支撑位附近)")
        print(f"   止损位: {support * 0.97:.2f} (-{ (1-support*0.97/latest['close'])*100:.1f}%)")
        print(f"   目标位: {resistance * 1.02:.2f} (+{ (resistance*1.02/latest['close']-1)*100:.1f}%)")
    
    # 卖出计划
    if score < 55:
        sell_price = min(resistance * 0.99, latest['close'] * 1.01)
        print(f"📤 卖出参考价: {sell_price:.2f} (压力位附近)")
        print(f"   若跌破: {support * 0.98:.2f} 应果断止损")
    
    # 持仓者建议
    print()
    print("📌 持仓者建议:")
    if score >= 70:
        print(f"   ✅ 继续持有，趋势向好")
        print(f"   📍 止盈位: {latest['close'] * 1.08:.2f} (+8%)")
        print(f"   🛑 止损位: {ma5 * 0.98:.2f} (跌破MA5)")
    elif score >= 55:
        print(f"   ⏸️  继续持有，但设置止盈")
        print(f"   📍 止盈位: {latest['close'] * 1.05:.2f} (+5%)")
        print(f"   🛑 止损位: {latest['close'] * 0.95:.2f} (-5%)")
    elif score >= 45:
        print(f"   👀 观察为主，灵活应对")
        print(f"   📍 若跌破 {support:.2f} 考虑减仓")
        print(f"   📍 若突破 {resistance:.2f} 可加仓")
    else:
        print(f"   ⚠️ 建议减仓或离场")
        print(f"   📍 减仓位: {latest['close'] * 0.98:.2f}")
        print(f"   🛑 止损位: {latest['close'] * 0.95:.2f}")
    
    print()
    print("=" * 70)
    print("⚠️ 免责声明: 以上分析仅供参考，不构成投资建议。")
    print("   股市有风险，投资需谨慎。")
    print("=" * 70)

# 执行分析
if __name__ == "__main__":
    analyze_stock("000981", "山子高科")
