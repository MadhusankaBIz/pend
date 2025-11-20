"""
services/ingestor/ingestor.py
=============================
Real-time tick aggregation into 1-min candles.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

# Make shared modules importable
sys.path.insert(0, "/app/shared")

from mongo_client import MongoDB
from deriv_api import DerivAPI
import config

db = MongoDB()

current_minute = None
tick_buffer = []
previous_price = None


def floor_minute(dt: datetime) -> datetime:
    """Floor datetime to the start of the minute (UTC)."""
    return dt.replace(second=0, microsecond=0, tzinfo=timezone.utc)


async def on_tick(tick: dict):
    """Process each incoming tick from Deriv."""
    global current_minute, tick_buffer, previous_price

    price = float(tick["quote"])
    epoch = int(tick["epoch"])
    ts = datetime.fromtimestamp(epoch, timezone.utc)
    minute_start = floor_minute(ts)

    # If we moved into a new minute, save the previous one.
    if current_minute and current_minute != minute_start:
        await save_candle()
        tick_buffer = []

    current_minute = minute_start
    tick_buffer.append({"price": price, "epoch": epoch})
    previous_price = price


async def save_candle():
    """Aggregate buffered ticks into a 1-minute candle and save to Mongo."""
    if not tick_buffer:
        return

    prices = [t["price"] for t in tick_buffer]

    # Use summed absolute price moves as a range proxy.
    summed_range = sum(
        abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))
    )

    candle = {
        "symbol": config.SYMBOL,
        "minute_start": current_minute,
        "open": prices[0],
        "high": max(prices),
        "low": min(prices),
        "close": prices[-1],
        "range": summed_range,
        "tick_count": len(prices),
        "created_at": datetime.now(timezone.utc),
    }

    db.save_1m_candle(candle)
    print(
        f"[INGESTOR] Saved 1m: {current_minute} | "
        f"O:{prices[0]:.4f} C:{prices[-1]:.4f} | "
        f"Range:{summed_range:.4f} | Ticks:{len(prices)}"
    )


async def main():
    """Main ingestion loop."""
    print(f"[INGESTOR] Starting for {config.SYMBOL}...")
    api = DerivAPI(use_auth=False)

    while True:
        try:
            await api.connect()
            # Subscribe for ticks – this just tells Deriv what we want.
            await api.subscribe_ticks(config.SYMBOL, on_tick)

            # Now *we* continuously read from the WebSocket and forward ticks.
            while True:
                raw = await api.ws.recv()
                data = json.loads(raw)
                tick = data.get("tick")
                if tick:
                    await on_tick(tick)

        except Exception as e:
            print(f"[INGESTOR] Error: {e}. Reconnecting...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
