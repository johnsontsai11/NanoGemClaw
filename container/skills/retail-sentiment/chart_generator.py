import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from db import get_connection, return_connection
import os
import pandas as pd
import numpy as np

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
    ax1.plot(df['date_label'], df['price'], color=color_price, linewidth=2.5, label='TMF Price')
    ax1.set_ylabel('TMF Price', color=color_price, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color_price)
    ax1.grid(True, alpha=0.1)
    
    # Annotate latest price
    latest_price = df['price'].iloc[-1]
    ax1.annotate(f'{int(latest_price):,}', 
                 xy=(df['date_label'].iloc[-1], latest_price),
                 xytext=(10, 0), textcoords='offset points',
                 color=color_price, fontweight='bold', fontsize=12)
    
    # Right Axis: Retail Sentiment Ratio
    ax2 = ax1.twinx()
    color_ratio = '#ff6b35'
    ax2.plot(df['date_label'], df['ratio'], color=color_ratio, linewidth=2, label='Retail Ratio (%)')
    ax2.plot(df['date_label'], df['ma5'], color='white', linewidth=1, linestyle='--', alpha=0.7, label='Ratio 5MA')
    ax2.set_ylabel('Retail Sentiment (%)', color=color_ratio, fontsize=12)
    ax2.tick_params(axis='y', labelcolor=color_ratio)
    
    # Horizontal Threshold Lines (Taiwan-calibrated, Taiwan color scheme)
    ax2.axhline(y=-10, color='#ff3333', linestyle=':', alpha=0.6, label='軋空線 (-10%)')
    ax2.axhline(y=30, color='#ffaa00', linestyle=':', alpha=0.6, label='警示線 (30%)')
    ax2.axhline(y=40, color='#00cc66', linestyle=':', alpha=0.8, label='超買線 (40%)')
    ax2.axhline(y=20, color='white', linestyle='-', alpha=0.2, label='均值 (~20%)')

    # Shading extreme zones (Taiwan convention: Green=danger/down, Red=squeeze/up)
    ax2.fill_between(df['date_label'], -10, df['ratio'], where=(df['ratio'] < -10),
                    color='#ff3333', alpha=0.2, label='軋空區（上漲）')
    ax2.fill_between(df['date_label'], 40, df['ratio'], where=(df['ratio'] > 40),
                    color='#00cc66', alpha=0.25, label='超買區（易跌）')
    ax2.fill_between(df['date_label'], 30, df['ratio'], where=((df['ratio'] > 30) & (df['ratio'] <= 40)),
                    color='#ffdd44', alpha=0.15, label='警示區')

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
            bbox=dict(boxstyle='round,pad=0.4', facecolor=bg_color, alpha=0.8)
        )
    
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
