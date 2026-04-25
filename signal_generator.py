"""Signal Generation Module"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
from technical_analysis import (
    KlineData, calculate_rsi, calculate_vwap, calculate_volume_metrics,
    detect_consolidation_breakout, calculate_price_momentum, detect_manipulation
)
from config import (
    RSI_BULLISH_MIN, RSI_BULLISH_MAX, RSI_BEARISH_MIN, RSI_BEARISH_MAX,
    MIN_VOLUME_SPIKE_PCT, MAX_ACCEPTABLE_CHANGE_PCT, STOP_LOSS_PCT_LONG,
    STOP_LOSS_PCT_SHORT, TAKE_PROFIT_ZONES, MIN_USDT_VOLUME
)


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class TradingSignal:
    symbol: str
    direction: Direction
    entry_zone: str
    reason: str
    volume_spike_pct: float
    price_change_pct: float
    risk_level: RiskLevel
    stop_loss: str
    take_profit_zones: str
    score: float  # Confidence score 0-100
    additional_data: Dict


def format_price(price: float) -> str:
    """Format price with appropriate decimals"""
    if price >= 1000:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    elif price >= 0.01:
        return f"{price:.6f}"
    else:
        return f"{price:.8f}"


def calculate_entry_zone(current_price: float, direction: Direction, 
                        momentum: Dict) -> str:
    """Calculate suggested entry zone"""
    if direction == Direction.LONG:
        # Entry on pullback to previous resistance (now support) or current level
        entry_low = current_price * 0.995
        entry_high = current_price * 1.005
    else:
        entry_low = current_price * 0.995
        entry_high = current_price * 1.005
    
    return f"{format_price(entry_low)} - {format_price(entry_high)}"


def calculate_stop_loss(current_price: float, direction: Direction,
                       breakout_data: Dict, momentum: Dict) -> str:
    """Calculate suggested stop loss"""
    if direction == Direction.LONG:
        # Stop below breakout level or percentage
        sl_from_breakout = breakout_data.get('range_low', current_price * 0.97)
        sl_from_pct = current_price * (1 - STOP_LOSS_PCT_LONG / 100)
        sl = max(sl_from_breakout * 0.99, sl_from_pct)
    else:
        sl_from_breakout = breakout_data.get('range_high', current_price * 1.03)
        sl_from_pct = current_price * (1 + STOP_LOSS_PCT_SHORT / 100)
        sl = min(sl_from_breakout * 1.01, sl_from_pct)
    
    return format_price(sl)


def calculate_take_profits(current_price: float, direction: Direction,
                          entry_price: float, stop_loss: float) -> str:
    """Calculate take profit zones based on R multiples"""
    if direction == Direction.LONG:
        risk = entry_price - stop_loss
        tp_levels = [entry_price + (risk * r) for r in TAKE_PROFIT_ZONES]
    else:
        stop_value = float(stop_loss) if isinstance(stop_loss, (int, float, str)) else current_price * 1.03
        try:
            stop_val = float(stop_value)
        except:
            stop_val = current_price * 1.03
        risk = stop_val - entry_price
        tp_levels = [entry_price - (risk * r) for r in TAKE_PROFIT_ZONES]
    
    return " | ".join([f"TP{i+1}: {format_price(tp)}" for i, tp in enumerate(tp_levels)])


def determine_risk_level(volume_spike: float, change_pct: float, 
                         momentum: Dict, manipulation: Dict) -> RiskLevel:
    """Determine risk level based on multiple factors"""
    risk_score = 0
    
    # Volume risk
    if volume_spike > 400:
        risk_score += 2
    elif volume_spike > 300:
        risk_score += 1
    
    # Price change risk
    if abs(change_pct) > 15:
        risk_score += 2
    elif abs(change_pct) > 10:
        risk_score += 1
    
    # Manipulation risk
    if manipulation.get('is_suspicious', False):
        risk_score += 2
    
    # Acceleration risk
    acceleration = momentum.get('acceleration', 0)
    if abs(acceleration) > 3:
        risk_score += 1
    
    if risk_score >= 4:
        return RiskLevel.HIGH
    elif risk_score >= 2:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def generate_signal(symbol: str, klines: List[KlineData], 
                   ticker_24h: Optional[Dict]) -> Optional[TradingSignal]:
    """Generate trading signal from market data"""
    
    if len(klines) < 50:
        return None
    
    # Filter low volume coins
    if ticker_24h:
        volume_24h = float(ticker_24h.get('quoteVolume', 0))
        if volume_24h < MIN_USDT_VOLUME:
            return None
    
    # Calculate indicators
    closes = np.array([k.close for k in klines])
    highs = np.array([k.high for k in klines])
    lows = np.array([k.low for k in klines])
    
    rsi = calculate_rsi(closes)
    vwap = calculate_vwap(klines)
    volume_metrics = calculate_volume_metrics(klines)
    breakout_data = detect_consolidation_breakout(klines)
    momentum = calculate_price_momentum(klines)
    manipulation = detect_manipulation(klines)
    
    # Skip if manipulation detected
    if manipulation.get('is_suspicious', False):
        return None
    
    # Skip if volume spike not sufficient
    volume_spike = volume_metrics['spike_pct']
    if volume_spike < MIN_VOLUME_SPIKE_PCT:
        return None
    
    current_price = klines[-1].close
    direction = Direction.NEUTRAL
    reasons = []
    score = 0
    
    # Determine direction and validate criteria
    if rsi is not None:
        # Long setup
        if RSI_BULLISH_MIN <= rsi <= RSI_BULLISH_MAX:
            if breakout_data.get('is_bullish_breakout', False):
                direction = Direction.LONG
                reasons.append(f"RSI {rsi:.1f} in bullish zone")
                reasons.append("Bullish breakout from consolidation")
                score += 30
            elif momentum.get('acceleration', 0) > 0.5:
                # Strong upward acceleration without being overbought
                if rsi < 70:
                    direction = Direction.LONG
                    reasons.append(f"RSI {rsi:.1f} - momentum building")
                    reasons.append("Positive price acceleration")
                    score += 25
        
        # Short setup
        elif RSI_BEARISH_MIN <= rsi <= RSI_BEARISH_MAX:
            if breakout_data.get('is_bearish_breakout', False):
                direction = Direction.SHORT
                reasons.append(f"RSI {rsi:.1f} in bearish zone")
                reasons.append("Bearish breakdown from consolidation")
                score += 30
            elif momentum.get('acceleration', 0) < -0.5:
                if rsi > 30:
                    direction = Direction.SHORT
                    reasons.append(f"RSI {rsi:.1f} - bearish momentum building")
                    reasons.append("Negative price acceleration")
                    score += 25
    
    # Additional score components
    if direction != Direction.NEUTRAL:
        # Volume score
        if volume_spike > 300:
            score += 20
            reasons.append(f"Volume spike: {volume_spike:.1f}%")
        elif volume_spike > 200:
            score += 15
            reasons.append(f"Strong volume: {volume_spike:.1f}%")
        
        # VWAP confirmation
        if vwap:
            if direction == Direction.LONG and current_price > vwap:
                score += 10
                reasons.append("Price above VWAP")
            elif direction == Direction.SHORT and current_price < vwap:
                score += 10
                reasons.append("Price below VWAP")
        
        # Momentum confirmation
        change_5m = momentum.get('change_5m', 0)
        change_15m = momentum.get('change_15m', 0)
        
        if direction == Direction.LONG and change_5m > 0 and change_15m > 0:
            score += 10
            reasons.append(f"Consistent upward momentum ({change_5m:.2f}% 5m)")
        elif direction == Direction.SHORT and change_5m < 0 and change_15m < 0:
            score += 10
            reasons.append(f"Consistent downward momentum ({change_5m:.2f}% 5m)")
    
    # Skip if score too low
    if score < 50:
        return None
    
    # Risk assessment
    risk_level = determine_risk_level(
        volume_spike, 
        momentum.get('change_15m', 0),
        momentum,
        manipulation
    )
    
    # Check excessive movement
    max_change = max(
        abs(momentum.get('change_5m', 0)),
        abs(momentum.get('change_15m', 0))
    )
    if max_change > MAX_ACCEPTABLE_CHANGE_PCT:
        reasons.append(f"CAUTION: Large move ({max_change:.1f}%) - late entry")
        risk_level = RiskLevel.HIGH
    
    # Calculate levels
    entry_zone = calculate_entry_zone(current_price, direction, momentum)
    stop_loss = calculate_stop_loss(current_price, direction, breakout_data, momentum)
    take_profits = calculate_take_profits(current_price, direction, current_price, float(stop_loss))
    
    return TradingSignal(
        symbol=symbol,
        direction=direction,
        entry_zone=entry_zone,
        reason="; ".join(reasons),
        volume_spike_pct=volume_spike,
        price_change_pct=momentum.get('change_15m', 0),
        risk_level=risk_level,
        stop_loss=stop_loss,
        take_profit_zones=take_profits,
        score=score,
        additional_data={
            'rsi': rsi,
            'vwap': vwap,
            'breakout': breakout_data,
            'acceleration': momentum.get('acceleration', 0),
            'change_5m': momentum.get('change_5m', 0),
            'change_30m': momentum.get('change_30m', 0)
        }
    )
