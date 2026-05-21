import requests
import json
import os
from datetime import datetime
from db import init_db, get_connection

# Paths
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

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
                inst_long += int(entry.get("OpenInterest(Long)", 0))
                inst_short += int(entry.get("OpenInterest(Short)", 0))
            # Include Investment Trust (投信) if desired, usually Retail = Total - All Inst
            # But the typical "散戶籌碼" formula uses Top 3 Institutional (外資, 投信, 自營商)
            elif entry.get("Item") in ["投信", "自營商"]:
                inst_long += int(entry.get("OpenInterest(Long)", 0))
                inst_short += int(entry.get("OpenInterest(Short)", 0))
            
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
        print("Error: Could not fetch data from TAIFEX OpenAPI")
        return None
    
    date = inst_data["date"]
    inst_long = inst_data["inst_long"]
    inst_short = inst_data["inst_short"]
    price = market_data["price"]
    total_oi = market_data["total_oi"]
    
    # Formula: 法人淨部位 = 多方總和 - 空方總和
    net_pos = inst_long - inst_short
    # 散戶多空比 (%) = -(法人淨部位) / 全市場未平倉量 * 100
    ratio = -(net_pos) / total_oi * 100 if total_oi > 0 else 0

    # Data quality check: ratio should be within reasonable bounds (-100%, +100%)
    if abs(ratio) > 100:
        print(f"Warning: Calculated ratio {ratio:.1f}% exceeds ±100%, data may be incomplete")

    # Validate price is reasonable (TMF typically trades 2000-3000 range)
    if price < 100 or price > 10000:
        print(f"Warning: Price {price} seems unusual for TMF")
    
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
