#!/usr/bin/env python3
"""简单A股实时监控脚本。

支持：
- 多标的批量查询
- 按涨跌幅阈值 + 量比阈值触发
- 输出当前是否命中，以及盘口摘要

示例：
  python3 tools/stock_monitor.py 002195 000981 --move-pct 2 --volume-ratio 1.5
  python3 tools/stock_monitor.py 601619 --move-pct 2 --volume-ratio 1.5 --json
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any


def get_sina_symbol(code: str) -> str:
    code = code.upper().replace("SH", "").replace("SZ", "").replace(".", "")
    if code.startswith("6"):
        return "sh" + code
    if code.startswith(("0", "3")):
        return "sz" + code
    if code.startswith(("8", "4")):
        return "bj" + code
    return "sh" + code


def fetch_quotes(codes: list[str]) -> dict[str, dict[str, Any]]:
    symbols = [get_sina_symbol(code) for code in codes]
    url = f"https://hq.sinajs.cn/list={','.join(symbols)}"
    req = urllib.request.Request(
        url,
        headers={
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        },
    )
    text = urllib.request.urlopen(req, timeout=10).read().decode("gbk")

    result: dict[str, dict[str, Any]] = {}
    for line in text.strip().splitlines():
        m = re.match(r'var hq_str_(\w+)="([^"]*)"', line.strip())
        if not m:
            continue
        symbol, payload = m.groups()
        fields = payload.split(",")
        if len(fields) < 32 or not fields[0]:
            continue

        pre_close = float(fields[2]) if fields[2] else 0.0
        price = float(fields[3]) if fields[3] else 0.0
        volume_shares = int(float(fields[8])) if fields[8] else 0
        amount = float(fields[9]) if fields[9] else 0.0
        bid1 = float(fields[6]) if fields[6] else 0.0
        ask1 = float(fields[7]) if fields[7] else 0.0
        bid1_vol = int(float(fields[10])) if fields[10] else 0
        ask1_vol = int(float(fields[20])) if fields[20] else 0
        date_str = fields[30] if len(fields) > 30 else ""
        time_str = fields[31] if len(fields) > 31 else ""

        change_pct = ((price - pre_close) / pre_close * 100) if pre_close else 0.0

        result[symbol[2:]] = {
            "code": symbol[2:],
            "symbol": symbol,
            "name": fields[0],
            "open": float(fields[1]) if fields[1] else 0.0,
            "pre_close": pre_close,
            "price": price,
            "high": float(fields[4]) if fields[4] else 0.0,
            "low": float(fields[5]) if fields[5] else 0.0,
            "bid1": bid1,
            "ask1": ask1,
            "bid1_vol_lots": bid1_vol,
            "ask1_vol_lots": ask1_vol,
            "volume_lots": volume_shares // 100,
            "amount": amount,
            "change_pct": round(change_pct, 2),
            "updated_at": f"{date_str} {time_str}".strip(),
        }
    return result


def estimate_volume_ratio(quote: dict[str, Any]) -> float:
    """粗略估算量比。

    说明：新浪这个轻量接口不直接给量比，这里按“当前分钟成交节奏 vs 全日均匀节奏”做盘中近似，
    用来做快速预警，不适合作为精确复盘指标。
    """
    updated_at = quote.get("updated_at", "")
    try:
        if len(updated_at) < 16:
            return 0.0
        dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
        minutes = trading_minutes_elapsed(dt.hour, dt.minute)
        if minutes <= 0:
            return 0.0
        avg_per_minute = quote["volume_lots"] / minutes
        full_day_avg = quote["volume_lots"] / 240 if quote["volume_lots"] else 0.0
        if full_day_avg <= 0:
            return 0.0
        return round(avg_per_minute / full_day_avg, 2)
    except Exception:
        return 0.0


def trading_minutes_elapsed(hour: int, minute: int) -> int:
    total = 0
    current = hour * 60 + minute
    morning_start = 9 * 60 + 30
    morning_end = 11 * 60 + 30
    afternoon_start = 13 * 60
    afternoon_end = 15 * 60

    if current > morning_start:
        total += max(0, min(current, morning_end) - morning_start)
    if current > afternoon_start:
        total += max(0, min(current, afternoon_end) - afternoon_start)
    return min(total, 240)


def evaluate(quote: dict[str, Any], move_pct: float, volume_ratio: float) -> dict[str, Any]:
    est_ratio = estimate_volume_ratio(quote)
    hit_move = abs(quote["change_pct"]) >= move_pct
    hit_ratio = est_ratio >= volume_ratio
    return {
        **quote,
        "estimated_volume_ratio": est_ratio,
        "hit_move": hit_move,
        "hit_volume_ratio": hit_ratio,
        "triggered": hit_move and hit_ratio,
    }


def analyze_reseal(quote: dict[str, Any]) -> dict[str, Any]:
    price = quote.get("price", 0.0)
    pre_close = quote.get("pre_close", 0.0)
    high = quote.get("high", 0.0)
    low = quote.get("low", 0.0)
    bid1_vol = quote.get("bid1_vol_lots", 0)
    ask1_vol = quote.get("ask1_vol_lots", 0)
    change_pct = quote.get("change_pct", 0.0)

    limit_up = round(pre_close * 1.10, 2) if pre_close else 0.0
    distance_to_limit = round(limit_up - price, 2) if limit_up else 0.0
    pullback_from_high_pct = round(((high - price) / high * 100), 2) if high else 0.0
    intraday_amplitude_pct = round(((high - low) / pre_close * 100), 2) if pre_close else 0.0
    bid_ask_ratio = round((bid1_vol / ask1_vol), 2) if ask1_vol else 99.0

    score = 0
    reasons = []

    if change_pct >= 8:
        score += 2
        reasons.append("涨幅仍在强势区")
    elif change_pct >= 5:
        score += 1
        reasons.append("涨幅仍有强势基础")
    else:
        reasons.append("涨幅优势一般")

    if distance_to_limit <= 0.03:
        score += 2
        reasons.append("已非常接近涨停价")
    elif distance_to_limit <= 0.08:
        score += 1
        reasons.append("距离涨停价不远")
    else:
        reasons.append("离涨停价还有距离")

    if pullback_from_high_pct <= 1.0:
        score += 2
        reasons.append("开板后回撤较浅")
    elif pullback_from_high_pct <= 2.0:
        score += 1
        reasons.append("开板后回撤可控")
    else:
        reasons.append("开板后回撤偏深")

    if bid_ask_ratio >= 1.5:
        score += 2
        reasons.append("买一承接明显强于卖一抛压")
    elif bid_ask_ratio >= 0.8:
        score += 1
        reasons.append("买卖盘相对均衡")
    else:
        reasons.append("卖一压单偏重")

    if intraday_amplitude_pct >= 8:
        reasons.append("日内振幅较大，分歧不小")
        score -= 1

    if score >= 7:
        verdict = "回封概率高"
    elif score >= 5:
        verdict = "有回封预期"
    elif score >= 3:
        verdict = "回封偏弱"
    else:
        verdict = "回封难"

    return {
        "limit_up": limit_up,
        "distance_to_limit": distance_to_limit,
        "pullback_from_high_pct": pullback_from_high_pct,
        "intraday_amplitude_pct": intraday_amplitude_pct,
        "bid_ask_ratio": bid_ask_ratio,
        "score": score,
        "verdict": verdict,
        "reasons": reasons,
    }


def format_line(item: dict[str, Any]) -> str:
    flag = "✅触发" if item["triggered"] else "⏳未触发"
    return (
        f"{flag} {item['name']}({item['code']}) 现价:{item['price']:.2f} "
        f"涨跌幅:{item['change_pct']:+.2f}% 估算量比:{item['estimated_volume_ratio']:.2f} "
        f"买一/卖一:{item['bid1']:.2f}/{item['ask1']:.2f} "
        f"买一量/卖一量:{item['bid1_vol_lots']}/{item['ask1_vol_lots']}手 "
        f"更新时间:{item['updated_at']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="A股实时监控")
    parser.add_argument("codes", nargs="+", help="股票代码")
    parser.add_argument("--move-pct", type=float, default=2.0, help="涨跌幅阈值，默认2")
    parser.add_argument("--volume-ratio", type=float, default=1.5, help="量比阈值，默认1.5")
    parser.add_argument("--reseal", action="store_true", help="输出回封判断")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    args = parser.parse_args()

    quotes = fetch_quotes(args.codes)
    items = [evaluate(quotes[code], args.move_pct, args.volume_ratio) for code in args.codes if code in quotes]

    if args.reseal:
        items = [{**item, "reseal": analyze_reseal(item)} for item in items]

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        for item in items:
            print(format_line(item))
            if args.reseal and "reseal" in item:
                reseal = item["reseal"]
                print(f"  回封判断:{reseal['verdict']} | 距涨停:{reseal['distance_to_limit']:.2f} | 回撤:{reseal['pullback_from_high_pct']:.2f}% | 买卖比:{reseal['bid_ask_ratio']:.2f}")
                print(f"  依据: {'；'.join(reseal['reasons'])}")

    missing = [code for code in args.codes if code not in quotes]
    if missing:
        print(f"未获取到行情: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
