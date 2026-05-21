---
name: Retail Sentiment Analysis  
description: Taiwan Futures (TMF) retail vs institutional sentiment analysis
enabled: true
---

# retail-sentiment

**IMPORTANT: This skill runs on the HOST, not in a container. You have full database access to localhost:5432.**

When the user asks for "散戶籌碼分析" or "retail sentiment analysis", use the `execute_bash_script` tool with this command:

```bash
bash /workspace/scripts/run-retail-sentiment.sh
```

The script will:
1. Connect to PostgreSQL at localhost:5432 (credentials from .env)
2. Scrape latest TAIFEX data
3. Run analysis engine
4. Generate chart at `/Volumes/DevDisk/NanoGemClaw/container/skills/retail-sentiment/output/sentiment_chart_*.png`
5. Output text report to stdout

After the script completes successfully, use the `send_document` tool to send the chart file to the user.

**Example workflow:**
1. Call `execute_bash_script` with command: `bash /workspace/scripts/run-retail-sentiment.sh`
2. Read the stdout for the text report
3. Parse the chart path from stdout (format: `Chart successfully generated at absolute path: /path/to/chart.png`)
4. Call `send_document` with the chart path and the report text as caption
