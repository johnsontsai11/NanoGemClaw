from db import get_connection, return_connection
import os
import json
import psycopg2.extras

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_data(limit=20):
    conn = get_connection()
    try:
        # Use DictCursor to mimic sqlite3.Row behavior
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Fetch in descending order to get latest, then reverse for chronological order
        cursor.execute("SELECT * FROM tmf_daily ORDER BY date DESC LIMIT %s", (limit,))
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in reversed(rows)]
    finally:
        return_connection(conn)

def detect_trend(ratios):
    """Simple trend detection using recent slope"""
    if len(ratios) < 5:
        return "insufficient_data", 0

    recent = ratios[-5:]
    slope = (recent[-1] - recent[0]) / len(recent)

    if slope > 5:
        return "rising_fast", slope  # +5% per day
    elif slope > 2:
        return "rising", slope
    elif slope < -5:
        return "falling_fast", slope
    elif slope < -2:
        return "falling", slope
    else:
        return "stable", slope

def get_percentile_rank(ratio, lookback_days=60):
    """Calculate where current ratio ranks in historical distribution"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ratio FROM tmf_daily
            WHERE date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY ratio
        """ % lookback_days)

        historical = [r[0] for r in cursor.fetchall()]
        cursor.close()

        if len(historical) < 10:
            return None

        rank = sum(1 for h in historical if h < ratio) / len(historical) * 100
        return rank
    finally:
        return_connection(conn)

def analyze():
    data = get_latest_data(20)
    if len(data) < 1:
        return "暫無足夠資料進行分析。"

    today = data[-1]
    yesterday = data[-2] if len(data) > 1 else today

    # Validate data integrity
    if today['ratio'] is None or today['price'] is None:
        return "今日數據不完整，無法進行分析。"

    ratio = float(today['ratio'])
    prev_ratio = float(yesterday['ratio'])
    diff = ratio - prev_ratio
    
    # Calculate MA (adaptive to available data)
    ratios = [d['ratio'] for d in data]
    ma_period = min(5, len(ratios))
    ma5 = sum(ratios[-ma_period:]) / ma_period
    ma_label = f"{ma_period}日均" if ma_period < 5 else "5日均"

    # Detect trend
    trend, slope = detect_trend(ratios)

    # Get percentile ranking (if enough history)
    percentile = get_percentile_rank(ratio)
    
    # Tsai Sen Logic (Calibrated for Taiwan Futures Market)
    # Note: Taiwan retail tends to be structurally net long (mean ~+20% to +30%)
    # Thresholds adjusted based on Taiwan market characteristics

    signal = "⚖️ 狀態：籌碼中性"
    commentary = "目前籌碼分布相對平衡，建議回歸量價型態觀察，留意關鍵頸線位置。"
    reminder = f"守住 {int(today['price']):,} 點支撐，量縮不跌視為強勢。"

    # Taiwan-calibrated thresholds with safe zone (10-30%)
    if ratio < 0:  # Retail net short (very rare for Taiwan)
        if diff > 15:
            signal = "⚠️ 警告：空頭投降"
            commentary = "空單出現大規模回補（投降），雖然價格可能創新高，但籌碼動能正在衰退，需嚴防高檔反轉構築 M 頭右肩。"
            reminder = "高檔不建議追多，留意頸線支撐是否跌破。"
        else:
            signal = "🔥 趨勢：強勢軋空"
            commentary = "散戶持續看空並持有大量空單，法人反向拉抬。目前處於強勢軋空階段，不宜預設高點。"
            reminder = "順勢操作，只要散戶多空比維持負值，軋空動能仍在。"
    elif ratio < 10:  # Retail unusually low (0-10%)
        signal = "🔵 偏低：散戶偏空"
        commentary = "散戶多單比例偏低，顯示市場偏空氣氛。若為下跌後的低檔區，可能是底部訊號。"
        reminder = "觀察價格是否止穩，等待量價配合的反彈訊號。"
    elif ratio <= 30:  # Safe zone (10-30%)
        signal = "✅ 安全：籌碼健康"
        commentary = "散戶多空比處於健康範圍（10-30%），籌碼分布相對平衡，無明顯擁擠。此時應回歸技術面與基本面分析。"
        reminder = f"正常操作，守住 {int(today['price']):,} 點支撐，依循技術訊號進出。"
    elif ratio > 40:  # Extreme retail long (Taiwan-specific threshold)
        signal = "❄️ 警示：極端多單擁擠"
        commentary = "散戶多單過度擁擠（比例 >40%），需嚴防多頭踩踏引發的快速修正。法人可能正在派發籌碼。"
        reminder = "高度風險，跌破關鍵支撐需果斷減碼，防範急殺。"
    elif ratio > 30:  # Elevated retail long (30-40%)
        signal = "⚠️ 注意：多單偏高"
        commentary = "散戶多單比例偏高，需留意法人動態。若出現價量背離或技術破位，殺盤風險增加。"
        reminder = "保守操作，嚴守停損紀律，不追高。"
        
    report = {
        "date": today['date'],
        "ratio": ratio,
        "diff": diff,
        "ma5": ma5,
        "ma_label": ma_label,
        "price": today['price'],
        "signal": signal,
        "commentary": commentary,
        "reminder": reminder,
        "trend": trend,
        "slope": slope,
        "percentile": percentile
    }
    
    return report

def format_report(report):
    if isinstance(report, str):
        return report

    diff_str = f"↗️ +{report['diff']:.1f}%" if report['diff'] >= 0 else f"↘️ {report['diff']:.1f}%"

    # Trend emoji
    trend_emoji = {
        "rising_fast": "📈 快速上升",
        "rising": "↗️ 上升",
        "stable": "➡️ 持平",
        "falling": "↘️ 下降",
        "falling_fast": "📉 快速下降",
        "insufficient_data": "⏳ 資料不足"
    }

    text = f"📊 微台散戶多空趨勢 ({report['date']})\n"
    text += f"● 今日數值：{report['ratio']:.1f}% ({diff_str})\n"
    text += f"● {report['ma_label']}線：{report['ma5']:.1f}%\n"

    # Add percentile if available
    if report.get('percentile') is not None:
        text += f"● 歷史排名：第 {report['percentile']:.0f} 百分位\n"

    # Add trend if available
    if report.get('trend'):
        text += f"● 趨勢方向：{trend_emoji.get(report['trend'], report['trend'])}\n"

    text += f"● 判斷結果：{report['signal']}\n\n"
    text += f"🔍 蔡森型態進階分析：\n{report['commentary']}\n\n"
    text += f"💡 操盤手提醒：{report['reminder']}"

    return text

if __name__ == "__main__":
    res = analyze()
    print(format_report(res))
