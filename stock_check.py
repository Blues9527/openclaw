#!/usr/bin/env python3
import urllib.request
import ssl
import re

# 创建不验证证书的上下文
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://hq.sinajs.cn/list=sz002195'
req = urllib.request.Request(url, headers={
    'Referer': 'https://finance.sina.com.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

try:
    resp = urllib.request.urlopen(req, context=ctx, timeout=10)
    text = resp.read().decode('gbk')
    
    # 解析数据
    match = re.match(r'var hq_str_(\w+)="([^"]*)"', text)
    if match:
        data_str = match.group(2)
        fields = data_str.split(',')
        if len(fields) >= 10:
            name = fields[0]
            open_price = float(fields[1]) if fields[1] else 0
            pre_close = float(fields[2]) if fields[2] else 0
            price = float(fields[3]) if fields[3] else 0
            high = float(fields[4]) if fields[4] else 0
            low = float(fields[5]) if fields[5] else 0
            volume = int(float(fields[8])) // 100 if fields[8] else 0  # 手
            amount = float(fields[9]) / 100000000 if fields[9] else 0  # 亿
            change_pct = (price - pre_close) / pre_close * 100 if pre_close else 0
            
            print('=' * 60)
            print(f'股票: {name} (002195)')
            print('=' * 60)
            print()
            print('【实时行情】')
            change_symbol = '+' if change_pct >= 0 else ''
            print(f'  现价: {price:.2f}  涨跌: {change_symbol}{change_pct:.2f}%')
            print(f'  今开: {open_price:.2f}  最高: {high:.2f}  最低: {low:.2f}')
            print(f'  昨收: {pre_close:.2f}')
            print(f'  成交量: {volume/10000:.1f}万手  成交额: {amount:.2f}亿')
            
            # 获取分时数据
            print()
            print('【分时量能分析】获取中...')
            
            minute_url = 'https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_sz002195=/CN_MarketDataService.getKLineData?symbol=sz002195&scale=1&ma=no&datalen=250'
            req2 = urllib.request.Request(minute_url, headers={
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            resp2 = urllib.request.urlopen(req2, context=ctx, timeout=10)
            text2 = resp2.read().decode('utf-8')
            
            # 解析JSONP
            import json
            match2 = re.search(r"\(\[(.*)\]\)", text2, re.DOTALL)
            if match2:
                data = json.loads("[" + match2.group(1) + "]")
                
                # 过滤交易时段
                trading_data = [d for d in data if int(d.get('volume', 0)) > 0 and "09:25" <= d['day'][-8:-3] <= "15:00"]
                
                if trading_data:
                    total_vol = sum(int(d['volume']) for d in trading_data)
                    
                    def period_vol(start, end):
                        return sum(int(d['volume']) for d in trading_data if start <= d['day'][-8:-3] < end)
                    
                    open_30 = period_vol("09:30", "10:00")
                    mid_am = period_vol("10:00", "11:30")
                    mid_pm = period_vol("13:00", "14:30")
                    close_30 = period_vol("14:30", "15:01")
                    
                    print(f'  全天成交: {total_vol//100}手')
                    print()
                    print('  成交分布:')
                    print(f'    早盘30分(9:30-10:00): {open_30//100}手 ({open_30/total_vol*100:.1f}%)')
                    print(f'    上午中段(10:00-11:30): {mid_am//100}手 ({mid_am/total_vol*100:.1f}%)')
                    print(f'    下午中段(13:00-14:30): {mid_pm//100}手 ({mid_pm/total_vol*100:.1f}%)')
                    print(f'    尾盘30分(14:30-15:00): {close_30//100}手 ({close_30/total_vol*100:.1f}%)')
                    print()
                    
                    # 主力信号
                    signals = []
                    if close_30 / total_vol > 0.25:
                        signals.append("尾盘大幅放量，可能有主力抢筹或出货")
                    elif close_30 / total_vol > 0.15:
                        signals.append("尾盘有一定放量")
                    if open_30 / total_vol > 0.30:
                        signals.append("早盘主力抢筹明显")
                    if open_30 / total_vol > 0.40:
                        signals.append("早盘放量异常，主力强势介入")
                    
                    if signals:
                        print('  【主力动向判断】')
                        for s in signals:
                            print(f'    🔥 {s}')
                    
                    # 放量 TOP 5
                    sorted_data = sorted(trading_data, key=lambda x: x['volume'], reverse=True)[:5]
                    print()
                    print('  放量时段 TOP 5:')
                    for d in sorted_data:
                        print(f"    {d['day'][-8:]} 价格:{float(d['close']):.2f} 成交:{int(d['volume'])//100}手")
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
