"""
shared/calculator.py
====================
Trading calculations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import config

def calculate_stake(balance):
    """Calculate stake based on balance"""
    if balance < 1000:
        return config.BASE_STAKE
    
    profit_bands = int((balance - 1000) / config.PROFIT_MILESTONE)
    stake = config.BASE_STAKE + (profit_bands * config.STAKE_INCREMENT)
    
    # Cap at 5% of balance
    max_stake = balance * 0.05
    return min(stake, max_stake)

def calculate_multiplier(entry, sl, stake):
    """Calculate multiplier using breathing room"""
    sl_dist = entry - sl
    
    if sl_dist <= 0 or entry <= 0:
        return None
    
    k = config.BREATHING_MULTIPLE
    mult_cap = entry / (k * sl_dist)
    
    valid = [m for m in config.AVAILABLE_MULTIPLIERS if m <= mult_cap]
    
    return max(valid) if valid else None

def is_doji(candle):
    """Check if candle is doji"""
    body = abs(candle['close'] - candle['open'])
    rng = candle['high'] - candle['low']
    
    if rng == 0:
        return False
    
    body_pct = body / rng
    return body_pct < config.DOJI_THRESHOLD

def is_bullish(candle):
    """Check if candle is bullish"""
    return candle['close'] > candle['open']