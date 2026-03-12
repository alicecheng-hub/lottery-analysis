#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣樂透資料抓取腳本
方法一：api.taiwanlottery.com 官方 API（逐月）
方法二：財政部國庫署開放資料 API
方法三：台灣彩券官網 HTML 歷史頁
"""

import json, os, sys, re
from datetime import datetime, timedelta
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.taiwanlottery.com/",
    "Origin": "https://www.taiwanlottery.com",
}

BASE_URL = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery"

def fetch_official(game, months_back=14):
    draws = []
    today = datetime.today()
    seen = set()
    endpoint = "Lotto649Result"   if game == "lotto649" else "Daily539Result"
    res_key  = "lotto649Res"      if game == "lotto649" else "daily539Res"

    for i in range(months_back):
        d  = today - timedelta(days=i * 30)
        ym = f"{d.year}-{d.month:02d}"
        url = f"{BASE_URL}/{endpoint}?period&month={ym}&pageSize=31"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            rows = data.get("content", {}).get(res_key, [])
            for row in rows:
                period = str(row.get("period", "")).strip()
                if not period or period in seen:
                    continue
                seen.add(period)
                nums = [int(x) for x in row.get("drawNumberSize", [])]
                if game == "lotto649" and len(nums) >= 6:
                    draws.append({"period": period, "date": row.get("lotteryDate",""),
                                  "numbers": sorted(nums[:6]),
                                  "special": int(nums[6]) if len(nums)>6 else None})
                elif game == "daily539" and len(nums) >= 5:
                    draws.append({"period": period, "date": row.get("lotteryDate",""),
                                  "numbers": sorted(nums[:5]), "special": None})
        except Exception as e:
            print(f"  [{game}] {ym} 官方API失敗：{e}")

    draws.sort(key=lambda x: x["period"], reverse=True)
    return draws

def fetch_nta(game, total=250):
    draws = []
    game_no = "02" if game == "lotto649" else "11"
    seen = set()
    for page in range(1, 20):
        url = f"https://gaze.nta.gov.tw/ntaOpenApi/api/lottery/lotteryNumInfo?gameNo={game_no}&pageNum={page}&pageSize=30"
        try:
            r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"], "Accept": "application/json"}, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            rows = data.get("body", data.get("data", data.get("content", [])))
            if not rows:
                break
            for row in rows:
                period = str(row.get("期別", row.get("period",""))).strip()
                if not period or period in seen:
                    continue
                seen.add(period)
                num_str = row.get("獎號", row.get("drawNumbers", row.get("numbers","")))
                if isinstance(num_str, str):
                    nums = [int(x) for x in re.findall(r'\d+', num_str)]
                elif isinstance(num_str, list):
                    nums = [int(x) for x in num_str]
                else:
                    continue
                date = row.get("開獎日期", row.get("lotteryDate",""))
                if game == "lotto649" and len(nums) >= 6:
                    draws.append({"period": period, "date": date,
                                  "numbers": sorted(nums[:6]),
                                  "special": int(nums[6]) if len(nums)>6 else None})
                elif game == "daily539" and len(nums) >= 5:
                    draws.append({"period": period, "date": date,
                                  "numbers": sorted(nums[:5]), "special": None})
            if len(draws) >= total:
                break
        except Exception as e:
            print(f"  [{game}] NTA page {page} 失敗：{e}")
            break

    draws.sort(key=lambda x: x["period"], reverse=True)
    return draws

def fetch_html(game, pages=10):
    draws = []
    seen = set()
    if game == "lotto649":
        base = "https://www.taiwanlottery.com/lotto/lotto649/history"
    else:
        base = "https://www.taiwanlottery.com/lotto/dailyCash/history"

    for page in range(1, pages + 1):
        url = f"{base}?p={page}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            html = r.text
            if game == "lotto649":
                rows = re.findall(
                    r'(\d{3,4}000\d{3})[^\d]*?(\d{4}/\d{2}/\d{2})[^\d]+'
                    r'(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{1,2})[^\d]+'
                    r'(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{1,2})',
                    html)
                for row in rows:
                    period = row[0]
                    if period in seen: continue
                    seen.add(period)
                    draws.append({"period": period, "date": row[1],
                                  "numbers": sorted([int(row[2+i]) for i in range(6)]),
                                  "special": int(row[8])})
            else:
                rows = re.findall(
                    r'(\d{3,4}000\d{3})[^\d]*?(\d{4}/\d{2}/\d{2})[^\d]+'
                    r'(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{1,2})',
                    html)
                for row in rows:
                    period = row[0]
                    if period in seen: continue
                    seen.add(period)
                    draws.append({"period": period, "date": row[1],
                                  "numbers": sorted([int(row[2+i]) for i in range(5)]),
                                  "special": None})
        except Exception as e:
            print(f"  [{game}] HTML p{page} 失敗：{e}")

    draws.sort(key=lambda x: x["period"], reverse=True)
    return draws

def fetch_game(game):
    name = "大樂透" if game == "lotto649" else "今彩539"
    print(f"[{name}] 方法一：官方API...")
    draws = fetch_official(game, months_back=14)
    if len(draws) >= 30:
        print(f"[{name}] ✅ 官方API，取得 {len(draws)} 期")
        return draws

    print(f"[{name}] 方法二：財政部API...")
    draws = fetch_nta(game, total=250)
    if len(draws) >= 30:
        print(f"[{name}] ✅ 財政部API，取得 {len(draws)} 期")
        return draws

    print(f"[{name}] 方法三：HTML抓取...")
    draws = fetch_html(game, pages=10)
    print(f"[{name}] HTML取得 {len(draws)} 期")
    return draws

def compute_stats(draws, n, zones, has_special=False):
    subset = draws[:n]
    if not subset:
        return None
    last = subset[0]
    freq = {}
    miss_counter = {}
    sp_freq = {}
    sp_last_seen = {}
    max_num = zones[2]

    for i, draw in enumerate(subset):
        nums = draw["numbers"]
        for num in nums:
            freq[num] = freq.get(num, 0) + 1
        for num in range(1, max_num + 1):
            if num not in nums:
                miss_counter[num] = miss_counter.get(num, 0) + 1
        if has_special and draw.get("special"):
            sp = draw["special"]
            sp_freq[sp] = sp_freq.get(sp, 0) + 1
            if sp not in sp_last_seen:
                sp_last_seen[sp] = i

    sp_miss = {}
    if has_special:
        for num in range(1, max_num + 1):
            sp_miss[num] = sp_last_seen.get(num, n)

    for num in range(1, max_num + 1):
        if num not in freq:
            freq[num] = 0
        if num not in miss_counter:
            miss_counter[num] = n

    zone_def = [(1, zones[0]), (zones[0]+1, zones[1]), (zones[1]+1, max_num)]
    zone_combo_counts = {}
    zone_trend = []
    recent_draws = []

    for draw in subset[:15]:
        nums = draw["numbers"]
        zc = [sum(1 for x in nums if lo <= x <= hi) for lo, hi in zone_def]
        zone_trend.append(zc)
        key = "-".join(map(str, zc))
        zone_combo_counts[key] = zone_combo_counts.get(key, 0) + 1

    for draw in subset[:10]:
        nums = draw["numbers"]
        zc = [sum(1 for x in nums if lo <= x <= hi) for lo, hi in zone_def]
        recent_draws.append({
            "period":  draw.get("period",""),
            "date":    draw.get("date",""),
            "numbers": nums,
            "special": draw.get("special"),
            "zones":   zc,
        })

    zone_freq = []
    for lo, hi in zone_def:
        total = sum(freq.get(num, 0) for num in range(lo, hi+1))
        zone_freq.append({"avg": round(total / n, 2)})

    top_hot  = sorted(freq.keys(), key=lambda x: -freq[x])[:10]
    top_cold = sorted(miss_counter.keys(), key=lambda x: -miss_counter[x])[:10]

    result = {
        "lastDraw":    {**last, "zones": recent_draws[0]["zones"] if recent_draws else []},
        "frequency":   {str(k): v for k, v in freq.items()},
        "missing":     {str(k): v for k, v in miss_counter.items()},
        "topHot":      [int(x) for x in top_hot],
        "topCold":     [int(x) for x in top_cold],
        "topMissing":  [int(x) for x in top_cold],
        "zoneCombos":  zone_combo_counts,
        "zoneTrend":   zone_trend,
        "zoneFreq":    zone_freq,
        "recentDraws": recent_draws,
    }

    if has_special:
        sp_scored = sorted(sp_freq.keys(), key=lambda x: -(sp_freq.get(x,0)*2 + sp_miss.get(x,0)))
        result["specialFrequency"]  = {str(k): v for k, v in sp_freq.items()}
        result["specialMissing"]    = {str(k): v for k, v in sp_miss.items()}
        result["specialTopHot"]     = [int(x) for x in sp_scored[:10]]
        result["specialTopMissing"] = [int(x) for x in sorted(sp_miss.keys(), key=lambda x: -sp_miss.get(x,0))[:10]]

    return result

def build_game(draws, zones, has_special=False):
    result = {}
    for n in [30, 50, 100, 200]:
        stats = compute_stats(draws, n, zones, has_special=has_special)
        if stats:
            result[str(n)] = stats
    return result

def main():
    draws_649 = fetch_game("lotto649")
    draws_539 = fetch_game("daily539")

    if not draws_649 and not draws_539:
        print("❌ 兩個彩種都抓取失敗，中止")
        sys.exit(1)

    output = {
        "updatedAt":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lotto649":   build_game(draws_649, [16, 33, 49], has_special=True)  if draws_649 else {},
        "lottery539": build_game(draws_539, [13, 26, 39], has_special=False) if draws_539 else {},
    }

    os.makedirs("data", exist_ok=True)
    with open("data/lottery.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"✅ 完成！大樂透 {len(draws_649)} 期，今彩539 {len(draws_539)} 期")

if __name__ == "__main__":
    main()
