#!/usr/bin/env python3
"""Test indicator calculations on a sample symbol"""

from mexc_client import MexcClient
from technical_analysis import (
    KlineData, calculate_rsi, calculate_volume_metrics, 
    calculate_price_momentum, detect_consolidation_breakout, detect_manipulation
)
import numpy as np

client = MexcClient()

for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
    print(f"\n{'='*50}")
    print(f"Analysis for {symbol}")
    print('='*50)
    
    klines_raw = client.get_klines(symbol, interval='1m', limit=60)
    if not klines_raw:
        print("Failed to fetch klines")
        continue
        
    klines = [KlineData.from_list(k) for k in klines_raw]
    
    closes = np.array([k.close for k in klines])
    print(f"Price: {closes[-1]:.2f}")
    print(f"Price Change 5m: {((closes[-1] - closes[-5])/closes[-5]*100):+.2f}%")
    print(f"Price Change 15m: {((closes[-1] - closes[-15])/closes[-15]*100):+.2f}%")
    
    rsi = calculate_rsi(closes)
    print(f"RSI(14): {rsi:.1f}" if rsi else "RSI: N/A")
    
    vol_metrics = calculate_volume_metrics(klines)
    print(f"Volume Spike: {vol_metrics['spike_pct']:+.1f}%")
    
    momentum = calculate_price_momentum(klines)
    print(f"Acceleration: {momentum.get('acceleration', 0):+.3f}")
    
    breakout = detect_consolidation_breakout(klines)
    print(f"Breakout: Bullish={breakout['is_bullish_breakout']}, Bearish={breakout['is_bearish_breakout']}")
    
    manip = detect_manipulation(klines)
    print(f"Suspicious: {manip['is_suspicious']}")
    
    # Check signal criteria
    print(f"\nSignal Check:")
    print(f"  - Volume spike >200%: {vol_metrics['spike_pct'] > 200}")
    print(f"  - RSI 55-75: {55 <= rsi <= 75}" if rsi else "  - RSI: N/A")
    print(f"  - Breakout: {breakout['is_bullish_breakout'] or breakout['is_bearish_breakout']}")
    print(f"  - No manipulation: {not manip['is_suspicious']}")
