import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from db import get_connection, return_connection
import os
import pandas as pd
import numpy as np

# Configure Chinese font support
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang TC', 'Heiti TC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Output directory for charts (runs on host)
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_chart(output_path):
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM tmf_daily ORDER BY date DESC LIMIT 20", conn)

        if df.empty or len(df) < 2:
            print("Error: Insufficient data to generate chart (need at least 2 data points)")
            return False
    except Exception as e:
        print(f"Error: Failed to fetch data from database: {e}")
        return False
    finally:
        if conn:
            return_connection(conn)
        
    df = df.sort_values('date')
    df['date_label'] = df['date'].apply(lambda x: x.strftime('%m-%d') if hasattr(x, 'strftime') else str(x)[5:10]) # MM-DD
    
    # Calculate 5MA for ratio
    df['ma5'] = df['ratio'].rolling(window=5).mean()
    
    # Set dark theme style
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(12, 6), dpi=150)
    fig.patch.set_facecolor('#1a1a2e')
    ax1.set_facecolor('#1a1a2e')
    
    # Left Axis: Price
    color_price = '#00d4ff'
    ax1.plot(df['date_label'], df['price'], color=color_price, linewidth=2.5,
             label='TMF Price', marker='o', markersize=6,
             markeredgecolor='white', markeredgewidth=1.5, zorder=3)
    ax1.set_ylabel('TMF Price', color=color_price, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color_price)
    ax1.grid(True, alpha=0.1, zorder=0)

    # Right Axis: Retail Sentiment Ratio
    ax2 = ax1.twinx()
    color_ratio = '#ff8800'  # Bright orange for visibility
    ax2.plot(df['date_label'], df['ratio'], color=color_ratio, linewidth=2.5,
             label='散戶比例 (%)', marker='o', markersize=6, markeredgecolor='white', markeredgewidth=1.5, zorder=3)
    ax2.plot(df['date_label'], df['ma5'], color='white', linewidth=2, linestyle='--', alpha=0.8, label='5日均線', zorder=2)
    ax2.set_ylabel('Retail Sentiment (%)', color=color_ratio, fontsize=13, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_ratio)

    # Annotate latest ratio (centered above circle with padding)
    latest_ratio = df['ratio'].iloc[-1]
    ax2.annotate(f'{latest_ratio:.1f}%',
                 xy=(df['date_label'].iloc[-1], latest_ratio),
                 xytext=(0, 22), textcoords='offset points',
                 ha='center',
                 color=color_ratio, fontweight='bold', fontsize=14,
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='black', edgecolor=color_ratio, linewidth=2),
                 zorder=100, clip_on=False)
    
    # Horizontal Threshold Lines (Taiwan-calibrated, Taiwan color scheme)
    ax2.axhline(y=0, color='#ff3333', linestyle=':', alpha=0.5, label='零線 (0%)', zorder=1)
    ax2.axhline(y=10, color='#4488ff', linestyle=':', alpha=0.5, label='安全下限 (10%)', zorder=1)
    ax2.axhline(y=30, color='#ffaa00', linestyle=':', alpha=0.6, label='警示線 (30%)', zorder=1)
    ax2.axhline(y=40, color='#00cc66', linestyle=':', alpha=0.8, label='超買線 (40%)', zorder=1)
    ax2.axhline(y=20, color='white', linestyle='-', alpha=0.3, label='均值 (20%)', zorder=1)

    # Shading zones (Taiwan convention: Green=danger/down, Red=squeeze/up, Blue=safe)
    # Safe zone (10-30%): Normal operating range
    ax2.fill_between(df['date_label'], 10, 30,
                    color='#4488ff', alpha=0.08, label='安全區 (10-30%)', zorder=0)

    # Extreme zones
    ax2.fill_between(df['date_label'], 0, df['ratio'], where=(df['ratio'] < 0),
                    color='#ff3333', alpha=0.2, label='軋空區（易漲）', zorder=0)
    ax2.fill_between(df['date_label'], 40, df['ratio'], where=(df['ratio'] > 40),
                    color='#00cc66', alpha=0.25, label='超買區（易跌）', zorder=0)

    # Warning zones
    ax2.fill_between(df['date_label'], 30, df['ratio'], where=((df['ratio'] > 30) & (df['ratio'] <= 40)),
                    color='#ffdd44', alpha=0.15, label='警示區', zorder=0)
    ax2.fill_between(df['date_label'], 0, df['ratio'], where=((df['ratio'] >= 0) & (df['ratio'] < 10)),
                    color='#ffdd44', alpha=0.12, label='偏低區', zorder=0)

    # Annotate significant ratio changes (diff > 10%, Taiwan color: red=up, green=down)
    df['diff'] = df['ratio'].diff()
    significant = df[df['diff'].abs() > 10]

    for idx in significant.index:
        row = df.loc[idx]
        # Taiwan convention: ratio rising = more retail longs = danger (green), falling = safer (red)
        bg_color = '#00aa44' if row['diff'] > 0 else '#dd3333'  # Green for up (danger), Red for down
        ax2.annotate(
            f"{row['diff']:+.1f}%",
            xy=(row['date_label'], row['ratio']),
            xytext=(0, 15 if row['diff'] > 0 else -20),
            textcoords='offset points',
            ha='center',
            fontsize=9,
            color='white',
            weight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=bg_color, alpha=0.8),
            zorder=50
        )

    # Annotate latest price (centered above circle with padding)
    latest_price = df['price'].iloc[-1]
    ax1.annotate(f'{int(latest_price):,}',
                 xy=(df['date_label'].iloc[-1], latest_price),
                 xytext=(0, 22), textcoords='offset points',
                 ha='center',
                 color=color_price, fontweight='bold', fontsize=14,
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='black', edgecolor=color_price, linewidth=2),
                 zorder=100, clip_on=False)

    # Set Y-axis limits for better visibility
    # Right axis (ratio): extend range to -15% to 60% so the line is more centered
    ax2.set_ylim(-15, 60)

    # Titles and Formatting
    plt.title('TMF Retail Sentiment Trend', fontsize=14, pad=20, color='white')
    fig.tight_layout()
    
    # Save chart
    try:
        plt.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches='tight')
        plt.close()
        return True
    except Exception as e:
        print(f"Error: Failed to save chart to {output_path}: {e}")
        plt.close()
        return False

if __name__ == "__main__":
    out = os.path.join(SKILL_DIR, "test_chart.png")
    if generate_chart(out):
        print(f"Chart saved to {out}")
    else:
        print("No data to generate chart")
