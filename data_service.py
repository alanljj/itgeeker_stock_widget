import re
import requests
import concurrent.futures
import datetime

# ─────────────────────────────────────────────
# 中国 A 股节假日表（仅非周末的补充休市日）
# 每年年初更新一次即可；周末已由 weekday() 判断
# ─────────────────────────────────────────────
CN_HOLIDAYS = {
    # 2025
    datetime.date(2025, 1, 1),   # 元旦
    datetime.date(2025, 1, 28),  # 春节
    datetime.date(2025, 1, 29),
    datetime.date(2025, 1, 30),
    datetime.date(2025, 1, 31),
    datetime.date(2025, 2, 3),
    datetime.date(2025, 2, 4),
    datetime.date(2025, 4, 4),   # 清明
    datetime.date(2025, 5, 1),   # 劳动节
    datetime.date(2025, 5, 2),
    datetime.date(2025, 5, 5),
    datetime.date(2025, 6, 2),   # 端午
    datetime.date(2025, 10, 1),  # 国庆+中秋
    datetime.date(2025, 10, 2),
    datetime.date(2025, 10, 3),
    datetime.date(2025, 10, 6),
    datetime.date(2025, 10, 7),
    datetime.date(2025, 10, 8),
    # 2026
    datetime.date(2026, 1, 1),   # 元旦
    datetime.date(2026, 2, 17),  # 春节（待官方公告确认后可调整）
    datetime.date(2026, 2, 18),
    datetime.date(2026, 2, 19),
    datetime.date(2026, 2, 20),
    datetime.date(2026, 2, 23),
    datetime.date(2026, 2, 24),
    datetime.date(2026, 4, 6),   # 清明
    datetime.date(2026, 5, 1),   # 劳动节
    datetime.date(2026, 5, 4),
    datetime.date(2026, 5, 5),
    datetime.date(2026, 6, 19),  # 端午
    datetime.date(2026, 10, 1),  # 国庆
    datetime.date(2026, 10, 2),
    datetime.date(2026, 10, 5),
    datetime.date(2026, 10, 6),
    datetime.date(2026, 10, 7),
    datetime.date(2026, 10, 8),
}

# 调休补班（周末变成交易日）
CN_EXTRA_TRADING_DAYS = {
    # 2025
    datetime.date(2025, 1, 26),   # 春节调休补班
    datetime.date(2025, 2, 8),
    datetime.date(2025, 4, 27),   # 劳动节调休
    datetime.date(2025, 9, 28),   # 国庆调休
    # 2026
    datetime.date(2026, 2, 15),   # 春节调休（待官方确认）
    datetime.date(2026, 2, 28),
    datetime.date(2026, 5, 9),
    datetime.date(2026, 10, 10),
}


def is_trading_time(now: datetime.datetime = None) -> bool:
    """
    判断当前时间是否在 A 股交易时段。
    交易时段：周一至周五（非节假日），09:30-11:30 / 13:00-15:00。
    调休补班的周末也算交易日。
    """
    if now is None:
        now = datetime.datetime.now()
    today = now.date()
    t = now.time()

    # 调休补班的周末 → 交易日
    if today in CN_EXTRA_TRADING_DAYS:
        pass  # 继续判断时段
    else:
        # 周末
        if today.weekday() >= 5:
            return False
        # 节假日
        if today in CN_HOLIDAYS:
            return False

    # 检查交易时段
    morning_start = datetime.time(9, 30)
    morning_end   = datetime.time(11, 30)
    afternoon_start = datetime.time(13, 0)
    afternoon_end   = datetime.time(15, 0)

    return (morning_start <= t <= morning_end) or (afternoon_start <= t <= afternoon_end)


def get_market_status(now: datetime.datetime = None) -> str:
    """
    返回当前市场状态描述字符串，用于 Widget 标题栏显示。
    - 交易时段：返回空字符串（由调用方显示最后拉取时间）
    - 收盘后/开盘前（交易日）：返回"已收盘"或"未开盘"
    - 周末：返回"周末休市"
    - 节假日：返回"节假日"
    - 午休：返回"午休"
    """
    if now is None:
        now = datetime.datetime.now()
    today = now.date()
    t = now.time()

    # 判断是否是交易日
    is_extra = today in CN_EXTRA_TRADING_DAYS
    is_weekend = today.weekday() >= 5
    is_holiday = today in CN_HOLIDAYS

    if is_extra:
        is_trading_day = True
    elif is_weekend:
        return "周末休市"
    elif is_holiday:
        return "节假日"
    else:
        is_trading_day = True

    # 交易日内的时段判断
    morning_start   = datetime.time(9, 30)
    morning_end     = datetime.time(11, 30)
    afternoon_start = datetime.time(13, 0)
    afternoon_end   = datetime.time(15, 0)

    if morning_start <= t <= morning_end:
        return ""   # 上午交易中
    elif afternoon_start <= t <= afternoon_end:
        return ""   # 下午交易中
    elif t < morning_start:
        return "未开盘"
    elif morning_end < t < afternoon_start:
        return "午休"
    else:
        return "已收盘"


def format_stock_code(code):
    """将股票代码转为 600900.sh 格式"""
    code = code.strip().lower()
    if not code:
        return ""
    # 如果已经是 xxx.xx 格式（区域代码在后面），直接返回
    if '.' in code:
        parts = code.split('.')
        if len(parts) == 2:
            num, region = parts
            return f"{num}.{region.lower()}"
    # 如果是 sh/sz/hk/bj 前缀格式（如 sh600900）
    if code.startswith(('sh', 'sz', 'hk', 'bj', 'us')):
        if len(code) >= 3:
            return f"{code[2:]}.{code[:2]}"
        return code
    # 如果只是纯数字
    if len(code) == 5 and code.isdigit():
        return f"{code}.hk"
    if len(code) == 6 and code.isdigit():
        if code.startswith(('60', '68')):
            return f"{code}.sh"
        elif code.startswith(('00', '30')):
            return f"{code}.sz"
        elif code.startswith(('43', '83', '87', '92')):
            return f"{code}.bj"
    return code

def to_api_code(code):
    """将 600900.sh 格式转为 API 所需的 sh600900 格式"""
    if '.' in code:
        parts = code.split('.')
        if len(parts) == 2:
            return f"{parts[1]}{parts[0]}"
    return code

def fetch_minute_data(code):
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={code}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if 'data' in data and code in data['data']:
            stock_data = data['data'][code]
            if 'data' in stock_data and 'data' in stock_data['data']:
                min_lines = stock_data['data']['data']
                prices = []
                for line in min_lines:
                    parts = line.split(' ')
                    if len(parts) >= 2:
                        prices.append(float(parts[1]))
                return prices
    except Exception as e:
        print(f"Failed to fetch minute data for {code}:", e)
    return []

def fetch_stock_data(raw_codes):
    if not raw_codes:
        return []
    # 格式化代码用于显示
    codes = [format_stock_code(c) for c in raw_codes if c]
    # 转换为 API 格式
    api_codes = [to_api_code(c) for c in codes]
    url = f"https://qt.gtimg.cn/q={','.join(api_codes)}"
    try:
        response = requests.get(url, timeout=5)
        text = response.text
        results = []
        for line in text.split('\n'):
            if not line:
                continue
            if line.startswith("v_"):
                parts = line.split('=')
                if len(parts) < 2:
                    continue
                api_code = parts[0][2:]  # sh600900
                data_str = parts[1].strip('";')
                fields = data_str.split('~')
                if len(fields) > 32:
                    name = fields[1]
                    try:
                        current = float(fields[3])
                        prev_close = float(fields[4])
                        change_percent = float(fields[32])
                    except ValueError:
                        continue
                    
                    # 转换显示格式
                    display_code = format_stock_code(api_code)
                    results.append({
                        "code": display_code,
                        "api_code": api_code,  # 保存 API 格式用于分时数据查询
                        "name": name,
                        "current": current,
                        "change_percent": change_percent,
                        "is_up": change_percent >= 0,
                    })

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_code = {executor.submit(fetch_minute_data, res['api_code']): res for res in results}
            for future in concurrent.futures.as_completed(future_to_code):
                res = future_to_code[future]
                trend = future.result()
                if not trend:
                    trend = [res['current'], res['current']]
                res['trend'] = trend

        code_to_res = {r['code']: r for r in results}
        ordered_results = [code_to_res[code] for code in codes if code in code_to_res]
        return ordered_results

    except Exception as e:
        print("Error fetching data:", e)
        return []


def fetch_stock_basics(raw_codes):
    """用于在编辑界面快速拉取名称，不需要分时数据"""
    if not raw_codes:
        return []
    codes = [format_stock_code(c) for c in raw_codes if c]
    api_codes = [to_api_code(c) for c in codes]
    url = f"https://qt.gtimg.cn/q={','.join(api_codes)}"
    try:
        response = requests.get(url, timeout=5)
        text = response.text
        results = []
        for line in text.split('\n'):
            if not line:
                continue
            if line.startswith("v_"):
                parts = line.split('=')
                if len(parts) < 2:
                    continue
                api_code = parts[0][2:] 
                data_str = parts[1].strip('";')
                fields = data_str.split('~')
                if len(fields) > 32:
                    name = fields[1]
                    try:
                        current = float(fields[3])
                        change_percent = float(fields[32])
                    except ValueError:
                        current = 0.0
                        change_percent = 0.0
                    
                    display_code = format_stock_code(api_code)
                    results.append({
                        "code": display_code,
                        "name": name,
                        "current": current,
                        "change_percent": change_percent
                    })
        return results
    except Exception as e:
        print("Error fetching basics:", e)
        return []

def fetch_daily_kline(code):
    """获取日K线数据"""
    # 转换为 API 格式
    api_code = to_api_code(code)
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={api_code},day,,,50,qfq"
        response = requests.get(url, timeout=5)
        data = response.json()
        if 'data' in data and api_code in data['data']:
            qfqday = data['data'][api_code].get('qfqday', [])
            if not qfqday:
                qfqday = data['data'][api_code].get('day', [])

            klines = []
            for k in qfqday:
                klines.append({
                    "date": k[0],
                    "open": float(k[1]),
                    "close": float(k[2]),
                    "high": float(k[3]),
                    "low": float(k[4])
                })
            return klines
    except Exception as e:
        print(f"Failed to fetch kline data for {code}:", e)
    return []


def search_stocks(keyword, limit=20):
    """
    按关键词（股票名称或代码）搜索股票。

    使用腾讯财经 smartbox 接口：
        GET https://smartbox.gtimg.cn/s3/?v=2&q={keyword}&t=all&c={limit}

    返回格式示例（v_hint 字段）：
        sz~000651~\\u683c\\u529b\\u7535\\u5668~gldq~GP-A^...
    每段结构: market~code~name(unicode escape)~pinyin~type

    返回:
        [{"code": "000651.sz", "name": "格力电器", "market": "sz"}, ...]
        code 使用项目标准格式 (xxx.sh / xxx.sz / xxx.hk / xxx.us)。
    """
    if not keyword:
        return []
    keyword = keyword.strip()
    if not keyword:
        return []

    url = "https://smartbox.gtimg.cn/s3/"
    params = {"v": "2", "q": keyword, "t": "all", "c": str(limit)}

    try:
        response = requests.get(url, params=params, timeout=5)
        text = response.text
    except Exception as e:
        print(f"Failed to search stocks for '{keyword}': {e}")
        return []

    m = re.search(r'v_hint="([^"]*)"', text)
    if not m:
        return []
    hint_str = m.group(1)
    if not hint_str:
        return []

    results = []
    for entry in hint_str.split('^'):
        if not entry:
            continue
        parts = entry.split('~')
        if len(parts) < 3:
            continue
        market = parts[0].lower()              # sh / sz / hk / us
        raw_code = parts[1]                    # 000651 / aapl.oq 等
        name_raw = parts[2]                    # \\u683c\\u529b... 字面转义

        # 解码 unicode 转义: \\uXXXX -> 字符
        try:
            name = name_raw.encode("ascii").decode("unicode_escape")
        except Exception:
            name = name_raw

        # 标准化到项目格式 (600900.sh)
        code = format_stock_code(f"{market}{raw_code}")

        if not code or not name:
            continue

        results.append({
            "code": code,
            "name": name,
            "market": market,
        })
        if len(results) >= limit:
            break

    return results

