#!/usr/bin/env python3
"""
Backfill historical TMF data from TAIFEX API
Usage: python3 backfill.py [days_back]
"""
import sys
import requests
from datetime import datetime, timedelta
from db import init_db, get_connection

def fetch_historical_data(date_str):
    """
    Fetch institutional OI and market data for a specific date (YYYYMMDD format)
    TAIFEX API endpoints may support date parameters - adjust as needed
    """
    # Note: TAIFEX OpenAPI might require date as query parameter
    # This is a template - adjust based on actual API documentation

    inst_url = f"https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate?date={date_str}"
    market_url = f"https://openapi.taifex.com.tw/v1/DailyMarketReportFut?date={date_str}"

    try:
        inst_response = requests.get(inst_url, timeout=10)
        market_response = requests.get(market_url, timeout=10)

        if inst_response.status_code != 200 or market_response.status_code != 200:
            return None

        inst_data = inst_response.json()
        market_data = market_response.json()

        # Parse institutional data
        inst_long = 0
        inst_short = 0

        for entry in inst_data:
            if entry.get("ContractCode") == "微型臺指期貨":
                if entry.get("Item") in ["外資及陸資", "投信", "自營商"]:
                    inst_long += int(entry.get("OpenInterest(Long)", 0))
                    inst_short += int(entry.get("OpenInterest(Short)", 0))

        # Parse market data
        total_oi = 0
        price = 0
        max_oi = 0

        for entry in market_data:
            if entry.get("Contract") == "TMF":
                oi_val = entry.get("OpenInterest", "0")
                current_oi = int(oi_val) if str(oi_val).isdigit() else 0
                total_oi += current_oi

                if current_oi > max_oi:
                    max_oi = current_oi
                    settle_price = entry.get("SettlementPrice")
                    last_price = entry.get("LastPrice") or entry.get("Last")

                    if settle_price and settle_price != 'NULL' and settle_price != '-':
                        price = float(settle_price)
                    elif last_price and last_price != 'NULL' and last_price != '-':
                        price = float(last_price)

        if total_oi == 0 or price == 0:
            return None

        # Calculate ratio
        net_pos = inst_long - inst_short
        ratio = -(net_pos) / total_oi * 100

        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        return {
            "date": formatted_date,
            "price": price,
            "inst_long": inst_long,
            "inst_short": inst_short,
            "total_oi": total_oi,
            "ratio": ratio
        }
    except Exception as e:
        print(f"Error fetching {date_str}: {e}")
        return None

def backfill(days_back=20):
    """Backfill last N days of data"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now()
    success_count = 0
    skip_count = 0

    print(f"Backfilling last {days_back} days...")

    for i in range(days_back, 0, -1):
        target_date = today - timedelta(days=i)

        # Skip weekends (TAIFEX closed)
        if target_date.weekday() >= 5:
            continue

        date_str = target_date.strftime("%Y%m%d")
        formatted_date = target_date.strftime("%Y-%m-%d")

        # Check if already exists
        cursor.execute("SELECT date FROM tmf_daily WHERE date = %s", (formatted_date,))
        if cursor.fetchone():
            print(f"  {formatted_date}: Already exists, skipping")
            skip_count += 1
            continue

        print(f"  {formatted_date}: Fetching...", end=" ")
        data = fetch_historical_data(date_str)

        if data:
            cursor.execute("""
                INSERT INTO tmf_daily (date, price, inst_long, inst_short, total_oi, ratio)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(date) DO NOTHING
            """, (data["date"], data["price"], data["inst_long"],
                  data["inst_short"], data["total_oi"], data["ratio"]))
            conn.commit()
            print(f"✓ Ratio: {data['ratio']:.1f}%")
            success_count += 1
        else:
            print("✗ No data (market closed or API error)")

    cursor.close()
    conn.close()

    print(f"\nBackfill complete: {success_count} inserted, {skip_count} skipped")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    backfill(days)
