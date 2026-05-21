from db import get_connection
import os
import json
import psycopg2.extras

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_data(limit=20):
    conn = get_connection()
    # Use DictCursor to mimic sqlite3.Row behavior
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Fetch in descending order to get latest, then reverse for chronological order
    cursor.execute("SELECT * FROM tmf_daily ORDER BY date DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in reversed(rows)]

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
    
    # Calculate 5MA
    ratios = [d['ratio'] for d in data]
    ma5 = sum(ratios[-5:]) / len(ratios[-5:]) if len(ratios) >= 5 else sum(ratios) / len(ratios)
    
    # Tsai Sen Logic
    signal = "⚖️ 狀態：籌碼中性"
    commentary = "目前籌碼分布相對平衡，建議回歸量價型態觀察，留意關鍵頸線位置。"
    reminder = f"守住 {int(today['price']):,} 點支撐，量縮不跌視為強勢。"
    
    if ratio < -15:
        if diff > 10:
            signal = "⚠️ 警告：空頭投降"
            commentary = "空單出現大規模回補（投降），雖然價格可能創新高，但籌碼動能正在衰退，需嚴防高檔反轉構築 M 頭右肩。"
            reminder = "高檔不建議追多，留意頸線支撐是否跌破。"
        else:
            signal = "🔥 趨勢：強勢軋空"
            commentary = "散戶持續看空並持有大量空單，法人反向拉抬。目前處於強勢軋空階段，不宜預設高點。"
            reminder = "順勢操作，只要散戶多空比維持在 -15% 以下，軋空動能仍在。"
    elif ratio > 15:
        signal = "❄️ 警示：殺多預警"
        commentary = "散戶多單過度擁擠，需嚴防多頭踩踏引發的快速修正。法人可能正在派發籌碼。"
        reminder = "保守操作，跌破關鍵支撐需果斷減碼，防範急殺。"
        
    report = {
        "date": today['date'],
        "ratio": ratio,
        "diff": diff,
        "ma5": ma5,
        "price": today['price'],
        "signal": signal,
        "commentary": commentary,
        "reminder": reminder
    }
    
    return report

def format_report(report):
    if isinstance(report, str):
        return report
        
    diff_str = f"↗️ +{report['diff']:.1f}%" if report['diff'] >= 0 else f"↘️ {report['diff']:.1f}%"
    
    text = f"📊 微台散戶多空趨勢 ({report['date']})\n"
    text += f"● 今日數值：{report['ratio']:.1f}% ({diff_str})\n"
    text += f"● 5 日平均：{report['ma5']:.1f}%\n"
    text += f"● 判斷結果：{report['signal']}\n\n"
    text += f"🔍 蔡森型態進階分析：\n{report['commentary']}\n\n"
    text += f"💡 操盤手提醒：{report['reminder']}"
    
    return text

if __name__ == "__main__":
    res = analyze()
    print(format_report(res))
