# MEXC Momentum Market Analyzer

A professional cryptocurrency market analysis tool that monitors MEXC exchange for high-probability momentum trading opportunities using early signal detection. Deployable on Railway with ntfy push notifications to your phone.

## Features

- **Price Action Analysis**: Detects rapid price acceleration and consolidation breakouts
- **Volume Analysis**: Flags assets with 2x-5x volume spikes above average
- **RSI Momentum**: Bullish (55-75) and bearish (25-45) zone detection
- **VWAP Deviation**: Trend confirmation using volume-weighted average price
- **Manipulation Detection**: Filters suspicious trading patterns
- **Risk Assessment**: Automatic stop-loss and take-profit calculations
- **Push Notifications**: Get instant alerts on your phone via ntfy when signals trigger

## Quick Start (Local)

```bash
pip install -r requirements.txt
python analyze.py              # Single scan
python market_analyzer.py -c   # Continuous monitoring
```

## Deploy to Railway (With Mobile Notifications)

### 1. Setup ntfy (for mobile push notifications)

1. **Install ntfy app** on your phone:
   - [iOS App Store](https://apps.apple.com/us/app/ntfy/id1625396347)
   - [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)

2. **Create a topic** in the app (e.g., `mexc-alerts-yourname`)

3. **Subscribe** to that topic on your phone

### 2. Deploy to Railway

**Option A: One-Click Deploy**
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

**Option B: Manual Deploy**
1. Fork/clone this repository
2. Create project on [Railway](https://railway.app)
3. Add environment variables (see below)
4. Deploy!

### 3. Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NTFY_ENABLED` | Yes | Set to `true` to enable notifications |
| `NTFY_TOPIC` | Yes | Your ntfy topic name (e.g., `mexc-alerts`) |
| `SCAN_INTERVAL_SECONDS` | No | Seconds between scans (default: 60) |
| `NTFY_MIN_SCORE_NOTIFY` | No | Min signal score to notify (default: 60) |
| `NTFY_PRIORITY` | No | `low`, `default`, `high`, `urgent` |

### 4. Notification Example

When a high-quality signal is detected, you'll get a push notification like:

```
🟢 BTCUSDT LONG Signal (Score: 72)
RSI 62.4 in bullish zone; Bullish breakout from consolidation

📊 Metrics:
• Volume Spike: +285%
• Price Change (15m): +3.45%
• Risk Level: Medium

🎯 Trade Setup:
• Entry: 43250.00 - 43450.00
• Stop Loss: 41950.00
• Take Profits: TP1: 43800 | TP2: 44250 | TP3: 44800

[Open MEXC] button
```

## Output Format

For each valid signal:

```
#1 BTCUSDT
  Direction: LONG
  Confidence Score: 75/100
  Entry Zone: 43250.00 - 43450.00
  Stop Loss: 41950.00
  Take Profits: TP1: 43800 | TP2: 44250 | TP3: 44800
  Risk Level: Medium
  Volume Spike: +285%
  Price Change (15m): +3.45%
  Reason: RSI 62.4 in bullish zone; Bullish breakout from consolidation
```

## Configuration

Edit `config.py` to customize:

- `RSI_BULLISH_MIN/MAX`: RSI range for long setups
- `RSI_BEARISH_MIN/MAX`: RSI range for short setups
- `MIN_VOLUME_SPIKE_PCT`: Minimum volume spike threshold (200 = 2x)
- `SCAN_INTERVAL_SECONDS`: Time between scans
- `MIN_USDT_VOLUME`: Minimum 24h volume filter

## Signal Criteria

Signals require:
1. Volume spike of 2x-5x above average
2. RSI in momentum zone (not overbought/oversold extremes)
3. Price acceleration or breakout confirmation
4. Score >= 50/100 (minimum confidence threshold)

Risk levels adjust based on:
- Volume spike magnitude
- Price change magnitude
- Detection of manipulation patterns
- Acceleration rate

## Project Structure

```
MEXC/
├── market_analyzer.py    # Main scanner with continuous monitoring
├── analyze.py            # Quick single scan entry point
├── mexc_client.py        # MEXC API client
├── technical_analysis.py # Indicators (RSI, VWAP, breakout detection)
├── signal_generator.py   # Signal generation logic
├── config.py             # Configuration parameters
└── requirements.txt        # Python dependencies
```

## API Note

This tool uses MEXC's public API endpoints. No API key required for basic market data. Optional authentication for higher rate limits.

## Disclaimer

This tool is for analysis purposes only. Always conduct your own research and manage risk appropriately. Not financial advice.
