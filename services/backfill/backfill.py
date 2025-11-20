"""
services/backfill/backfill.py
=============================
Fills missing 1-min candles every 20 minutes
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/app/shared')
from mongo_client import MongoDB
from deriv_api import DerivAPI
import config

db = MongoDB()

def floor_minute(dt):
    """Floor to minute"""
    return dt.replace(second=0, microsecond=0, tzinfo=timezone.utc)

async def check_gaps():
    """Check for missing candles"""
    print("[BACKFILL] Checking for gaps...")
    
    now = datetime.now(timezone.utc)
    lookback = int(os.getenv('LOOKBACK_MINUTES', 60))
    
    end_time = floor_minute(now - timedelta(minutes=1))
    start_time = end_time - timedelta(minutes=lookback - 1)
    
    # Generate expected minutes
    expected = []
    current = start_time
    while current <= end_time:
        expected.append(current)
        current += timedelta(minutes=1)
    
    # Get existing candles
    existing = db.get_1m_candles(config.SYMBOL, start_time, end_time + timedelta(minutes=1))
    existing_times = {c['minute_start'] for c in existing}
    
    # Find gaps
    gaps = [t for t in expected if t not in existing_times]
    
    if not gaps:
        print("[BACKFILL] No gaps found")
        return
    
    print(f"[BACKFILL] Found {len(gaps)} gaps. Filling...")
    
    # Fill gaps
    api = DerivAPI(use_auth=False)
    await api.connect()
    
    for gap_time in gaps:
        try:
            start_epoch = int(gap_time.timestamp())
            end_epoch = int((gap_time + timedelta(minutes=1)).timestamp()) - 1
            
            candles = await api.get_candles_history(
                config.SYMBOL,
                start_epoch,
                end_epoch
            )
            
            if candles:
                for c in candles:
                    candle = {
                        'symbol': config.SYMBOL,
                        'minute_start': datetime.fromtimestamp(c['epoch'], timezone.utc),
                        'open': float(c['open']),
                        'high': float(c['high']),
                        'low': float(c['low']),
                        'close': float(c['close']),
                        'range': abs(float(c['close']) - float(c['open'])),  # Approx
                        'tick_count': 30,
                        'filled': True,
                        'created_at': datetime.utcnow()
                    }
                    db.save_1m_candle(candle)
                    print(f"[BACKFILL] Filled: {gap_time}")
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"[BACKFILL] Error filling {gap_time}: {e}")
    
    await api.close()

async def main():
    """Main loop"""
    print("[BACKFILL] Starting...")
    
    interval = int(os.getenv('CHECK_INTERVAL', 1200))
    
    while True:
        try:
            await check_gaps()
        except Exception as e:
            print(f"[BACKFILL] Error: {e}")
        
        await asyncio.sleep(interval)

if __name__ == '__main__':
    asyncio.run(main())