"""
services/aggregator/aggregator.py
=================================
Aggregates 1-min candles into 30-min candles
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/app/shared')
from mongo_client import MongoDB
import config

db = MongoDB()

def floor_30min(dt):
    """Floor to 30-min boundary"""
    minute_block = (dt.minute // 30) * 30
    return dt.replace(minute=minute_block, second=0, microsecond=0, tzinfo=timezone.utc)

async def aggregate():
    """Aggregate last completed 30-min window"""
    now = datetime.now(timezone.utc)
    window_end = floor_30min(now)
    window_start = window_end - timedelta(minutes=30)
    
    # Check if already exists
    existing = db.db[config.COLL_30M].find_one({
        'symbol': config.SYMBOL,
        'window_start': window_start
    })
    
    if existing:
        return
    
    # Get 1-min candles
    candles_1m = db.get_1m_candles(
        config.SYMBOL,
        window_start,
        window_end
    )
    
    if len(candles_1m) < 25:  # Need at least 25/30 candles
        print(f"[AGGREGATOR] Not enough candles ({len(candles_1m)}/30) for {window_start}")
        return
    
    # Aggregate
    prices = []
    total_range = 0
    tick_count = 0
    
    for c in candles_1m:
        prices.extend([c['open'], c['high'], c['low'], c['close']])
        total_range += c['range']
        tick_count += c['tick_count']
    
    candle_30m = {
        'symbol': config.SYMBOL,
        'window_start': window_start,
        'open': candles_1m[0]['open'],
        'high': max(prices),
        'low': min(prices),
        'close': candles_1m[-1]['close'],
        'range': total_range,  # SUM of 1-min ranges
        'tick_count': tick_count,
        'candle_count': len(candles_1m),
        'created_at': datetime.utcnow()
    }
    
    db.save_30m_candle(candle_30m)
    
    print(f"[AGGREGATOR] Saved 30m: {window_start} | Range:{total_range:.4f} | Candles:{len(candles_1m)}")

async def scheduler():
    """Wait for 30-min boundaries"""
    while True:
        now = datetime.now(timezone.utc)
        next_boundary = floor_30min(now) + timedelta(minutes=30)
        wait_seconds = (next_boundary - now).total_seconds()
        
        await asyncio.sleep(max(0, wait_seconds + 10))  # Wait 10s after boundary
        await aggregate()

async def main():
    """Main loop"""
    print("[AGGREGATOR] Starting...")
    await scheduler()

if __name__ == '__main__':
    asyncio.run(main())