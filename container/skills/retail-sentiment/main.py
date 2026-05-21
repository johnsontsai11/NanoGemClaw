import os
import sys
import json
import time
from datetime import datetime

# Local imports
import taifex_scraper
import analysis_engine
import chart_generator

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
# Host-side execution: output to skill directory
OUTPUT_DIR = os.path.join(SKILL_DIR, "output")
# IPC not used when running on host
IPC_DIR = None
MESSAGES_DIR = None

def ensure_dirs():
    """Ensure writable directories exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)


def cleanup_old_charts(days=1):
    """Remove chart files older than the specified timeframe (in days)."""
    now = time.time()
    cutoff = now - (days * 86400)
    
    for d in [OUTPUT_DIR]:
        if not os.path.exists(d):
            continue
        for filename in os.listdir(d):
            if filename.startswith("sentiment_chart_") and filename.endswith(".png"):
                filepath = os.path.join(d, filename)
                try:
                    if os.path.isfile(filepath) and os.stat(filepath).st_mtime < cutoff:
                        os.remove(filepath)
                except Exception as e:
                    print(f"Warning: Failed to remove old chart {filename}: {e}")

def main():
    try:
        ensure_dirs()
        # 0. Clean up old charts (older than 1 day)
        cleanup_old_charts(days=1)

        # 1. Scrape latest data
        print("➤ Step 1/3: 正在從 TAIFEX 抓取最新數據...")
        sys.stdout.flush()
        current_data = taifex_scraper.scrape_and_store()
        if not current_data:
            print("⚠️ 無法獲取今日即時數據，將使用歷史存檔進行分析。")
        
        # 2. Analyze
        print("➤ Step 2/3: 正在執行量價型態分析...")
        sys.stdout.flush()
        report_data = analysis_engine.analyze()
        if isinstance(report_data, str):
            print(f"❌ 分析中斷: {report_data}")
            return
        
        report_text = analysis_engine.format_report(report_data)
        
        # 3. Generate Chart
        print("➤ Step 3/3: 正在繪製籌碼趨勢圖表...")
        sys.stdout.flush()
        chart_filename = f"sentiment_chart_{datetime.now().strftime('%H%M%S')}.png"
        chart_path = os.path.join(OUTPUT_DIR, chart_filename)
        
        success = chart_generator.generate_chart(chart_path)
        
        # 4. Output to stdout (for Gemini to read)
        print("\n" + "="*40)
        print(report_text)
        print("="*40 + "\n")
        
        # 5. Tell Gemini to send the chart
        if success:
            print(f"[SYSTEM MESSAGE] Chart successfully generated at absolute path: {chart_path}")
            print(f"DEBUG: Output path is {chart_path}")
            print("Please use the 'send_document' tool to send this file to the user.")
        else:
            print("⚠️ 警告：圖表生成失敗。")
            
    except Exception as e:
        print(f"\n❌ 執行過程中發生致命錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
