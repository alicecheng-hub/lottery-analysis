import requests
import json
import os
from datetime import datetime

# ====================================================
# 台灣彩券官網 API
# 大樂透 lotto649，今彩539 dailyCash
# ====================================================

BASE_URL = "https://www.taiwanlottery.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Referer": "https://www.taiwanlottery.com/",
    "Accept": "application/json, text/plain, */*",
}

# 抓取期數
FETCH_COUNTS = {
    "lotto649": 250,   # 大樂透（每週三次）
    "lottery539": 250, # 今彩539（每天一次）
}


def fetch_lotto649(count=250):
    """抓大樂透歷史開獎資料"""
    print(f"[大樂透] 開始抓取最近 {count} 期...")
    results = []

    try:
        # 官方 API endpoint
        url = f"{BASE_URL}/api/v1/game/lotto649/history"
        params = {"count": count}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("content", []):
            numbers = [
                item.get("no1", 0), item.get("no2", 0), item.get("no3", 0),
                item.get("no4", 0), item.get("no5", 0), item.get("no6", 0),
            ]
            numbers = sorted([n for n in numbers if n > 0])
            special = item.get("special", 0)
            period = str(item.get("period", ""))
            date = str(item.get("openDate", ""))

            if len(numbers) == 6:
                results.append({
                    "period": period,
                    "date": date,
                    "numbers": numbers,
                    "special": special
                })

        print(f"[大樂透] 成功取得 {len(results)} 期")

    except Exception as e:
        print(f"[大樂透] API 失敗，嘗試備用方式: {e}")
        results = fetch_lotto649_fallback(count)

    return results


def fetch_lotto649_fallback(count=250):
    """備用：從官網歷史查詢頁面抓"""
    results = []
    try:
        url = f"{BASE_URL}/Lotto649/Lotto649_his.aspx"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        # 解析 HTML 表格（備用）
        from html.parser import HTMLParser

        class LottoParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_table = False
                self.rows = []
                self.current_row = []
                self.in_td = False
                self.current_data = ""

            def handle_starttag(self, tag, attrs):
                if tag == "tr":
                    self.current_row = []
                if tag == "td":
                    self.in_td = True
                    self.current_data = ""

            def handle_endtag(self, tag):
                if tag == "td":
                    self.in_td = False
                    self.current_row.append(self.current_data.strip())
                if tag == "tr" and len(self.current_row) >= 8:
                    self.rows.append(self.current_row)
                    self.current_row = []

            def handle_data(self, data):
                if self.in_td:
                    self.current_data += data

        parser = LottoParser()
        parser.feed(resp.text)

        for row in parser.rows[:count]:
            try:
                nums = sorted([int(x) for x in row[2:8] if x.isdigit()])
                if len(nums) == 6:
                    results.append({
                        "period": row[0],
                        "date": row[1],
                        "numbers": nums,
                        "special": int(row[8]) if len(row) > 8 and row[8].isdigit() else 0
                    })
            except Exception:
                continue

        print(f"[大樂透] 備用方式取得 {len(results)} 期")
    except Exception as e:
        print(f"[大樂透] 備用方式也失敗: {e}")

    return results


def fetch_lottery539(count=250):
    """抓今彩539歷史開獎資料"""
    print(f"[今彩539] 開始抓取最近 {count} 期...")
    results = []

    try:
        url = f"{BASE_URL}/api/v1/game/dailyCash/history"
        params = {"count": count}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("content", []):
            numbers = [
                item.get("no1", 0), item.get("no2", 0), item.get("no3", 0),
                item.get("no4", 0), item.get("no5", 0),
            ]
            numbers = sorted([n for n in numbers if n > 0])
            period = str(item.get("period", ""))
            date = str(item.get("openDate", ""))

            if len(numbers) == 5:
                results.append({
                    "period": period,
                    "date": date,
                    "numbers": numbers,
                    "special": None
                })

        print(f"[今彩539] 成功取得 {len(results)} 期")

    except Exception as e:
        print(f"[今彩539] API 失敗，嘗試備用方式: {e}")
        results = fetch_539_fallback(count)

    return results


def fetch_539_fallback(count=250):
    """備用：從查詢頁面抓"""
    results = []
    try:
        url = f"{BASE_URL}/DailyCash/DailyCash_his.aspx"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        from html.parser import HTMLParser

        class Parser539(HTMLParser):
            def __init__(self):
                super().__init__()
                self.rows = []
                self.current_row = []
                self.in_td = False
                self.current_data = ""

            def handle_starttag(self, tag, attrs):
                if tag == "tr":
                    self.current_row = []
                if tag == "td":
                    self.in_td = True
                    self.current_data = ""

            def handle_endtag(self, tag):
                if tag == "td":
                    self.in_td = False
                    self.current_row.append(self.current_data.strip())
                if tag == "tr" and len(self.current_row) >= 7:
                    self.rows.append(self.current_row)
                    self.current_row = []

            def handle_data(self, data):
                if self.in_td:
                    self.current_data += data

        parser = Parser539()
        parser.feed(resp.text)

        for row in parser.rows[:count]:
            try:
                nums = sorted([int(x) for x in row[2:7] if x.isdigit()])
                if len(nums) == 5:
                    results.append({
                        "period": row[0],
                        "date": row[1],
                        "numbers": nums,
                        "special": None
                    })
            except Exception:
                continue

        print(f"[今彩539] 備用方式取得 {len(results)} 期")
    except Exception as e:
        print(f"[今彩539] 備用方式也失敗: {e}")

    return results


def compute_stats(draws, max_num, has_special=False):
    """計算統計數據"""
    total = len(draws)

    # 頻率
    frequency = {str(i): 0 for i in range(1, max_num + 1)}
    for draw in draws:
        for n in draw["numbers"]:
            if 1 <= n <= max_num:
                frequency[str(n)] += 1

    # 遺漏（多少期沒出現）
    missing = {}
    for num in range(1, max_num + 1):
        last_seen = total  # 預設：從未出現
        for i, draw in enumerate(draws):
            if num in draw["numbers"]:
                last_seen = i
                break
        missing[str(num)] = last_seen

    # 特別號統計（僅大樂透）
    special_frequency = {}
    special_missing = {}
    if has_special:
        special_frequency = {str(i): 0 for i in range(1, max_num + 1)}
        for draw in draws:
            sp = draw.get("special")
            if sp and 1 <= sp <= max_num:
                special_frequency[str(sp)] += 1

        for num in range(1, max_num + 1):
            last_seen = total
            for i, draw in enumerate(draws):
                if draw.get("special") == num:
                    last_seen = i
                    break
            special_missing[str(num)] = last_seen

        sp_sorted_freq = sorted(range(1, max_num + 1), key=lambda x: -special_frequency[str(x)])
        sp_sorted_miss = sorted(range(1, max_num + 1), key=lambda x: -special_missing[str(x)])

    # 排行
    sorted_by_freq = sorted(range(1, max_num + 1), key=lambda x: -frequency[str(x)])
    sorted_by_miss = sorted(range(1, max_num + 1), key=lambda x: -missing[str(x)])

    # 區間設定
    if max_num == 49:
        zones = [16, 33]
    else:
        zones = [13, 26]

    # 區間組合統計
    zone_combos = {}
    zone_freq = [{"total": 0, "avg": 0}, {"total": 0, "avg": 0}, {"total": 0, "avg": 0}]
    zone_trend = []

    num_draw = 6 if max_num == 49 else 5

    for draw in draws:
        z1 = sum(1 for n in draw["numbers"] if n <= zones[0])
        z2 = sum(1 for n in draw["numbers"] if zones[0] < n <= zones[1])
        z3 = sum(1 for n in draw["numbers"] if n > zones[1])
        key = f"{z1}-{z2}-{z3}"
        zone_combos[key] = zone_combos.get(key, 0) + 1
        zone_freq[0]["total"] += z1
        zone_freq[1]["total"] += z2
        zone_freq[2]["total"] += z3

    if total > 0:
        for i in range(3):
            zone_freq[i]["avg"] = round(zone_freq[i]["total"] / total, 2)

    zone_trend = [[
        sum(1 for n in d["numbers"] if n <= zones[0]),
        sum(1 for n in d["numbers"] if zones[0] < n <= zones[1]),
        sum(1 for n in d["numbers"] if n > zones[1])
    ] for d in draws[:20]]

    recent_draws = [{
        "period": d.get("period",""),
        "date": d.get("date",""),
        "numbers": d["numbers"],
        "special": d.get("special"),
        "zones": [
            sum(1 for n in d["numbers"] if n <= zones[0]),
            sum(1 for n in d["numbers"] if zones[0] < n <= zones[1]),
            sum(1 for n in d["numbers"] if n > zones[1])
        ]
    } for d in draws[:10]]

    result = {
        "frequency": frequency,
        "missing": missing,
        "topHot": sorted_by_freq[:10],
        "topCold": sorted_by_freq[-10:][::-1],
        "topMissing": sorted_by_miss[:10],
        "zoneCombos": zone_combos,
        "zoneTrend": zone_trend,
        "zoneFreq": zone_freq,
        "recentDraws": recent_draws,
    }

    if has_special and special_frequency:
        result["specialFrequency"] = special_frequency
        result["specialMissing"] = special_missing
        result["specialTopHot"] = sp_sorted_freq[:10]
        result["specialTopMissing"] = sp_sorted_miss[:10]

    return result
    """組合各期數的統計輸出"""
    output = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lotto649": {},
        "lottery539": {}
    }

    periods = [30, 50, 100, 200]

    for p in periods:
        draws = lotto649_draws[:p]
        if draws:
            stats = compute_stats(draws, 49, has_special=True)
            last = draws[0]
            output["lotto649"][str(p)] = {
                "lastDraw": {
                    "period": last.get("period", ""),
                    "date": last.get("date", ""),
                    "numbers": last["numbers"],
                    "special": last.get("special"),
                    "zones": [
                        sum(1 for n in last["numbers"] if n <= 16),
                        sum(1 for n in last["numbers"] if 16 < n <= 33),
                        sum(1 for n in last["numbers"] if n > 33),
                    ]
                },
                **stats
            }

    for p in periods:
        draws = lottery539_draws[:p]
        if draws:
            stats = compute_stats(draws, 39, has_special=False)
            last = draws[0]
            output["lottery539"][str(p)] = {
                "lastDraw": {
                    "period": last.get("period", ""),
                    "date": last.get("date", ""),
                    "numbers": last["numbers"],
                    "special": None,
                    "zones": [
                        sum(1 for n in last["numbers"] if n <= 13),
                        sum(1 for n in last["numbers"] if 13 < n <= 26),
                        sum(1 for n in last["numbers"] if n > 26),
                    ]
                },
                **stats
            }

    return output


def main():
    os.makedirs("data", exist_ok=True)

    # 抓資料
    lotto649_draws = fetch_lotto649(FETCH_COUNTS["lotto649"])
    lottery539_draws = fetch_lottery539(FETCH_COUNTS["lottery539"])

    if not lotto649_draws and not lottery539_draws:
        print("❌ 兩個彩種都抓取失敗，中止")
        exit(1)

    # 計算統計
    output = build_output(lotto649_draws, lottery539_draws)

    # 寫入 JSON
    with open("data/lottery.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    print(f"✅ 完成！已寫入 data/lottery.json")
    print(f"   大樂透：{len(lotto649_draws)} 期")
    print(f"   今彩539：{len(lottery539_draws)} 期")
    print(f"   更新時間：{output['updatedAt']}")


if __name__ == "__main__":
    main()
