import requests
import json
import os
from datetime import datetime, timedelta
from db import init_db, get_connection

# Paths
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# Taiwan market holidays 2026 (update annually)
TAIWAN_HOLIDAYS = [
    "2026-01-01",  # New Year
    "2026-01-27", "2026-01-28", "2026-01-29",  # Lunar New Year
    "2026-02-28",  # Peace Memorial Day
    "2026-04-03", "2026-04-04", "2026-04-05",  # Tomb Sweeping Day
    "2026-06-25",  # Dragon Boat Festival
    "2026-10-01",  # Mid-Autumn Festival
    "2026-10-10",  # National Day
]

def is_trading_day(date_str):
    """Check if date is a trading day (Mon-Fri, not holiday)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    # Weekend check
    if dt.weekday() >= 5:  # Sat=5, Sun=6
        return False

    # Holiday check
    if date_str in TAIWAN_HOLIDAYS:
        return False

    return True

def get_oi_field(entry, direction):
    """Robust field name extraction with fallbacks"""
    possible_names = [
        f"OpenInterest({direction})",
        f"OpenInterest{direction}",
        f"open_interest_{direction.lower()}",
        f"oi_{direction.lower()}"
    ]

    for name in possible_names:
        if name in entry:
            val = entry[name]
            # Handle string numbers
            if isinstance(val, str):
                return int(val) if val.isdigit() else 0
            return int(val)

    return 0

def validate_data(inst_long, inst_short, total_oi, price, date):
    """Validate scraped data for sanity"""
    errors = []

    # Check for zeros
    if total_oi == 0:
        errors.append("Total OI is zero")

    # Check if institutional positions exceed total OI
    if inst_long > total_oi:
        errors.append(f"Institutional long exceeds total OI: {inst_long} > {total_oi}")
    if inst_short > total_oi:
        errors.append(f"Institutional short exceeds total OI: {inst_short} > {total_oi}")

    # Check if ratio is impossible
    if total_oi > 0:
        ratio = -(inst_long - inst_short) / total_oi * 100
        if abs(ratio) > 100:
            errors.append(f"Impossible ratio: {ratio:.1f}%")

    # Price sanity (TMF usually 10000-50000 range in points)
    if price > 0 and (price < 1000 or price > 100000):
        errors.append(f"Price out of normal range: {price}")

    return errors

def is_data_stale(date, inst_long, inst_short):
    """Check if today's data matches yesterday's exactly"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT inst_long, inst_short FROM tmf_daily
            WHERE date = %s::date - INTERVAL '1 day'
        """, (date,))
        prev = cursor.fetchone()
        cursor.close()
        conn.close()

        if prev and prev[0] == inst_long and prev[1] == inst_short:
            return True
    except Exception as e:
        print(f"Warning: Could not check data staleness: {e}")

    return False

def fetch_institutional_oi():
    """Fetch institutional long/short positions for TMF."""
    url = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None
    
    data = response.json()
    # Contract Code for Micro Taiwan Index is TMF
    # Filter for TMF and sum up the 3 institutional categories (Dealer, IT, Foreign)
    # Usually near-month has the most OI. 
    # The API returns all contracts, we sum them for the total sentiment or pick the nearest.
    # Specification says "抓取微台(TMF)多空未平倉"
    
    inst_long = 0
    inst_short = 0
    date_str = ""
    
    for entry in data:
        if entry.get("ContractCode") == "微型臺指期貨":
            date_str = entry.get("Date") # YYYYMMDD

            # Identify foreign investors (外資)
            if entry.get("Item") == "外資及陸資":
                inst_long += get_oi_field(entry, "Long")
                inst_short += get_oi_field(entry, "Short")
            # Include Investment Trust (投信) if desired, usually Retail = Total - All Inst
            # But the typical "散戶籌碼" formula uses Top 3 Institutional (外資, 投信, 自營商)
            elif entry.get("Item") in ["投信", "自營商"]:
                inst_long += get_oi_field(entry, "Long")
                inst_short += get_oi_field(entry, "Short")
            
    if not date_str:
        return None
        
    # Format date to YYYY-MM-DD
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return {
        "date": formatted_date,
        "inst_long": inst_long,
        "inst_short": inst_short
    }

def fetch_market_summary():
    """Fetch TMF settlement price and total market OI."""
    url = "https://openapi.taifex.com.tw/v1/DailyMarketReportFut"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None
    
    data = response.json()
    
    total_oi = 0
    price = 0
    max_oi = 0
    found = False

    for entry in data:
        # Micro Taiwan Index Futures code: TMF
        if entry.get("Contract") == "TMF":
            # We want the nearest month (usually first entry for TMF)
            # or sum up OI if preferred. The logic usually focuses on near-month for sentiment.
            # But the formula uses "全市場未平倉量". Let's sum all TMF contracts OI.
            # Handle possible string '-' instead of number
            oi_val = entry.get("OpenInterest", "0")
            current_oi = int(oi_val) if str(oi_val).isdigit() else 0

            total_oi += current_oi
            # Use the settlement price of the most active contract (highest OI)
            if current_oi > max_oi:
                max_oi = current_oi
                settle_price = entry.get("SettlementPrice")
                last_price = entry.get("LastPrice") or entry.get("Last")

                # Use Settlement price if available and not 'NULL', else Last price
                if settle_price and settle_price != 'NULL' and settle_price != '-':
                    price = float(settle_price)
                elif last_price and last_price != 'NULL' and last_price != '-':
                    price = float(last_price)
            found = True
            
    if not found:
        return None
        
    return {
        "price": price,
        "total_oi": total_oi
    }

def scrape_and_store():
    init_db()

    inst_data = fetch_institutional_oi()
    market_data = fetch_market_summary()

    if not inst_data or not market_data:
        print("❌ Error: Could not fetch data from TAIFEX OpenAPI")
        return None

    date = inst_data["date"]
    inst_long = inst_data["inst_long"]
    inst_short = inst_data["inst_short"]
    price = market_data["price"]
    total_oi = market_data["total_oi"]

    # Check if trading day
    if not is_trading_day(date):
        print(f"⚠️ Skipping: {date} is not a trading day (weekend/holiday)")
        print(f"   API returned non-trading day data - likely stale")
        return None

    # Validate data quality
    validation_errors = validate_data(inst_long, inst_short, total_oi, price, date)
    if validation_errors:
        print(f"❌ Data validation failed:")
        for err in validation_errors:
            print(f"   - {err}")
        return None

    # Check for stale data
    if is_data_stale(date, inst_long, inst_short):
        print(f"⚠️ WARNING: Data identical to previous day - possible stale API cache")
        print(f"   Institutional positions unchanged: Long={inst_long}, Short={inst_short}")

    # Formula: 法人淨部位 = 多方總和 - 空方總和
    net_pos = inst_long - inst_short
    # 散戶多空比 (%) = -(法人淨部位) / 全市場未平倉量 * 100
    ratio = -(net_pos) / total_oi * 100 if total_oi > 0 else 0
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tmf_daily (date, price, inst_long, inst_short, total_oi, ratio)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(date) DO UPDATE SET
            price=EXCLUDED.price,
            inst_long=EXCLUDED.inst_long,
            inst_short=EXCLUDED.inst_short,
            total_oi=EXCLUDED.total_oi,
            ratio=EXCLUDED.ratio
    """, (date, price, inst_long, inst_short, total_oi, ratio))
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        "date": date,
        "price": price,
        "ratio": ratio,
        "inst_long": inst_long,
        "inst_short": inst_short,
        "total_oi": total_oi
    }

if __name__ == "__main__":
    result = scrape_and_store()
    if result:
        print(f"Scraped data for {result['date']}: Price={result['price']}, Ratio={result['ratio']:.2f}%")
