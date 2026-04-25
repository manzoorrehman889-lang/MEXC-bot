"""Technical Analysis Module for Momentum Detection"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class KlineData:
    """Kline data structure"""
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    
    @classmethod
    def from_list(cls, data: List) -> 'KlineData':
        return cls(
            open_time=int(data[0]),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            close_time=int(data[6])
        )


def calculate_rsi(prices: np.ndarray, period: int = 14) -> Optional[float]:
    """Calculate RSI for price series"""
    if len(prices) < period + 1:
        return None
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Calculate smoothed RSI
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_vwap(klines: List[KlineData]) -> Optional[float]:
    """Calculate Volume Weighted Average Price"""
    if not klines:
        return None
    
    typical_prices = [(k.high + k.low + k.close) / 3 for k in klines]
    volumes = [k.volume for k in klines]
    
    if sum(volumes) == 0:
        return None
    
    vwap = sum(tp * vol for tp, vol in zip(typical_prices, volumes)) / sum(volumes)
    return vwap


def calculate_volume_metrics(klines: List[KlineData], 
                           recent_periods: int = 15,
                           avg_periods: int = 45) -> Dict:
    """Calculate volume spike metrics"""
    if len(klines) < avg_periods:
        return {'spike_pct': 0, 'recent_vol': 0, 'avg_vol': 0}
    
    recent_volumes = [k.volume for k in klines[-recent_periods:]]
    avg_volumes = [k.volume for k in klines[-avg_periods:]]
    
    recent_vol = sum(recent_volumes)
    avg_vol = sum(avg_volumes) / len(avg_volumes) * recent_periods
    
    if avg_vol == 0:
        return {'spike_pct': 0, 'recent_vol': recent_vol, 'avg_vol': avg_vol}
    
    spike_pct = ((recent_vol - avg_vol) / avg_vol) * 100
    
    return {
        'spike_pct': spike_pct,
        'recent_vol': recent_vol,
        'avg_vol': avg_vol
    }


def detect_consolidation_breakout(klines: List[KlineData], 
                                  consolidation_periods: int = 30) -> Dict:
    """Detect if price is breaking out of consolidation range"""
    if len(klines) < consolidation_periods + 5:
        return {'is_breakout': False, 'range_high': 0, 'range_low': 0}
    
    # Get consolidation range (excluding last few candles)
    consolidation_candles = klines[-consolidation_periods-5:-5]
    range_high = max(k.high for k in consolidation_candles)
    range_low = min(k.low for k in consolidation_candles)
    
    # Current price
    current_close = klines[-1].close
    prev_close = klines[-2].close if len(klines) > 1 else klines[-1].open
    
    # Check for breakout
    bullish_breakout = current_close > range_high and prev_close <= range_high
    bearish_breakout = current_close < range_low and prev_close >= range_low
    
    range_size_pct = ((range_high - range_low) / range_low) * 100 if range_low > 0 else 0
    
    return {
        'is_bullish_breakout': bullish_breakout,
        'is_bearish_breakout': bearish_breakout,
        'range_high': range_high,
        'range_low': range_low,
        'range_size_pct': range_size_pct,
        'breakout_strength': abs(current_close - (range_high if bullish_breakout else range_low)) / ((range_high + range_low) / 2) * 100
    }


def calculate_price_momentum(klines: List[KlineData], 
                             lookback_periods: List[int] = [5, 15, 30]) -> Dict:
    """Calculate price change across multiple timeframes"""
    if not klines or len(klines) < max(lookback_periods) + 1:
        return {}
    
    current_price = klines[-1].close
    results = {'current': current_price}
    
    for period in lookback_periods:
        if len(klines) >= period:
            past_price = klines[-period].close
            change_pct = ((current_price - past_price) / past_price) * 100
            results[f'change_{period}m'] = change_pct
    
    # Calculate acceleration (rate of change of rate of change)
    if len(klines) >= 15:
        price_5m_ago = klines[-5].close
        price_10m_ago = klines[-10].close
        price_15m_ago = klines[-15].close
        
        velocity_1 = (price_5m_ago - price_10m_ago) / price_10m_ago * 100
        velocity_2 = (current_price - price_5m_ago) / price_5m_ago * 100
        
        acceleration = velocity_2 - velocity_1
        results['acceleration'] = acceleration
    
    return results


def detect_manipulation(klines: List[KlineData]) -> Dict:
    """Detect potential manipulation patterns"""
    if len(klines) < 10:
        return {'is_suspicious': False, 'reason': ''}
    
    recent = klines[-10:]
    wicks = []
    
    for k in recent:
        body = abs(k.close - k.open)
        upper_wick = k.high - max(k.close, k.open)
        lower_wick = min(k.close, k.open) - k.low
        
        if body > 0:
            wick_ratio = (upper_wick + lower_wick) / body
            wicks.append(wick_ratio)
    
    avg_wick_ratio = np.mean(wicks) if wicks else 0
    
    # Check for immediate sharp pullback after spike
    if len(klines) >= 5:
        last_3_changes = []
        for i in range(1, 4):
            change = abs(klines[-i].close - klines[-i-1].close) / klines[-i-1].close * 100
            last_3_changes.append(change)
        
        # Large move followed by immediate reversal
        if len(last_3_changes) >= 2:
            if last_3_changes[0] > 5 and last_3_changes[1] > last_3_changes[0] * 0.8:
                if klines[-1].close < klines[-2].open and klines[-2].close > klines[-3].open:
                    return {'is_suspicious': True, 'reason': 'Immediate sharp pullback after spike'}
    
    # High wick ratios indicate manipulation
    if avg_wick_ratio > 3:
        return {'is_suspicious': True, 'reason': 'Excessive wicks (potential manipulation)'}
    
    return {'is_suspicious': False, 'reason': ''}
