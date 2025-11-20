"""
services/detector/detector.py
=============================
Watches 30-minute candles and emits trade signals when a bearish →
bullish → bearish‑doji pattern (010) appears.  Uses the doji threshold
from shared/config.py.
"""

import asyncio
from datetime import datetime
from shared.mongo_client import MongoDB
from shared.calculator import is_bullish, is_doji

class PatternDetector:
    def __init__(self):
        self.active_patterns = {}
        self.db = MongoDB()

    async def check_new_pattern(self):
        """
        Called on each new 30‑minute candle.  Looks at the last two
        completed candles (oldest = c1, newest = c2) and, if they form
        a bearish→bullish sequence (0→1), registers the pattern as
        "waiting for doji".  The pattern key is the timestamp of c2.
        """
        candles = self.db.get_last_30m_candles(2)
        if len(candles) < 2:
            return

        c1, c2 = candles[-2], candles[-1]  # c1 is older
        # Bearish → Bullish (010 start)
        if not is_bullish(c1) and is_bullish(c2):
            pattern_id = c2["window_start"]
            self.active_patterns[pattern_id] = {"c1": c1, "c2": c2}
            print(f"[DETECTOR] New 010 pattern started at {pattern_id}")

    async def monitor_active_patterns(self):
        """
        For each pattern previously started, evaluate the next 30‑minute
        candle (c3).  The pattern completes successfully if c3 is
        bearish and a doji.  If so, insert a trade signal and remove
        the pattern.  Otherwise, the pattern is discarded.
        """
        c3_list = self.db.get_last_30m_candles(1)
        if not c3_list:
            return
        c3 = c3_list[0]
        to_remove = []

        for pid, pat in self.active_patterns.items():
            c2 = pat["c2"]
            # Only evaluate when a new candle forms after c2
            if c3["window_start"] <= c2["window_start"]:
                continue

            # Require the doji candle to be bearish (close ≤ open)
            if is_bullish(c3):
                print(f"[DETECTOR] Pattern {pid}: c3 bullish → discarded")
                to_remove.append(pid)
                continue

            # Require c3 to be a doji (body/true range < DOJI_THRESHOLD)
            if not is_doji(c3):
                print(f"[DETECTOR] Pattern {pid}: c3 not doji → discarded")
                to_remove.append(pid)
                continue

            # Success → emit trade signal
            signal = {
                "pattern_id": pid,
                "symbol": c3["symbol"],
                "c1": pat["c1"],
                "c2": c2,
                "c3": c3,
                "created_at": datetime.utcnow(),
                "type": "010_doji"
            }
            self.db.insert_trade_signal(signal)
            print(f"[DETECTOR] Pattern {pid}: 010+doji → trade signal emitted")
            to_remove.append(pid)

        # Remove processed or discarded patterns
        for pid in to_remove:
            del self.active_patterns[pid]

    async def run(self):
        """
        Main loop: periodically check for new patterns and evaluate
        existing ones.  Runs forever.
        """
        while True:
            try:
                await self.check_new_pattern()
                await self.monitor_active_patterns()
            except Exception as exc:
                print(f"[DETECTOR] Error: {exc}")
            # Sleep for a fraction of 30 minutes (e.g. every 5 minutes)
            await asyncio.sleep(300)

if __name__ == "__main__":
    detector = PatternDetector()
    asyncio.run(detector.run())





"""
services/detector/detector.py
=============================
Simple detector:
- Every new 30m candle becomes a trade signal.
- direction = 1 if bullish (close > open), 0 if bearish.
- No 010 pattern, no doji filter.
"""

# import asyncio
# import sys
# from datetime import datetime

# sys.path.insert(0, "/app/shared")
# from mongo_client import MongoDB
# import config

# db = MongoDB()

# CHECK_INTERVAL = 60  # seconds between checks


# def _get_last_30m_candle():
#     """Return the most recent 30m candle for the configured symbol."""
#     coll = db.db[config.COLL_30M]
#     docs = (
#         coll.find({"symbol": config.SYMBOL})
#         .sort("window_start", -1)
#         .limit(1)
#     )
#     candles = list(docs)
#     return candles[0] if candles else None


# def _compute_body_pct(candle: dict) -> float:
#     """
#     Body % using your custom idea of range:
#     - Prefer the 'range' field if present (your tick-sum range).
#     - Fallback to high - low if 'range' is missing.
#     """
#     close = candle["close"]
#     open_ = candle["open"]
#     high = candle["high"]
#     low = candle["low"]

#     body = abs(close - open_)
#     rng = candle.get("range", None)
#     if rng is None:
#         rng = high - low

#     if rng <= 0:
#         return 0.0
#     return body / rng


# async def detector_loop():
#     print(f"[DETECTOR] Starting for {config.SYMBOL}…")
#     print("[DETECTOR] Mode: EVERY 30m CANDLE → SIGNAL (no pattern, no doji)")

#     last_seen_ts = None

#     while True:
#         try:
#             candle = _get_last_30m_candle()
#             if not candle:
#                 print("[DETECTOR] No 30m candles yet")
#                 await asyncio.sleep(CHECK_INTERVAL)
#                 continue

#             ts = candle["window_start"]

#             # If we’ve already processed this candle, just wait
#             if last_seen_ts is not None and ts <= last_seen_ts:
#                 await asyncio.sleep(CHECK_INTERVAL)
#                 continue

#             last_seen_ts = ts

#             close = candle["close"]
#             open_ = candle["open"]
#             direction = 1 if close > open_ else 0  # 1 = bullish, 0 = bearish
#             body_pct = _compute_body_pct(candle)

#             # Avoid duplicate signals for the same candle if detector restarts
#             signals = db.db[config.COLL_SIGNALS]
#             existing = signals.find_one(
#                 {"symbol": config.SYMBOL, "window_start": ts}
#             )
#             if existing:
#                 print(
#                     f"[DETECTOR] Signal already exists for {ts}, skipping."
#                 )
#                 await asyncio.sleep(CHECK_INTERVAL)
#                 continue

#             # Build signal doc – executor expects c1/c2/c3 and pattern_id
#             signal_doc = {
#                 "symbol": config.SYMBOL,
#                 "pattern_id": "every_candle_v1",
#                 "window_start": ts,
#                 "created_at": datetime.utcnow(),
#                 "direction": direction,
#                 "body_pct_c3": body_pct,
#                 "c1": {
#                     "window_start": candle["window_start"],
#                     "open": candle["open"],
#                     "high": candle["high"],
#                     "low": candle["low"],
#                     "close": candle["close"],
#                     "range": candle.get("range"),
#                 },
#                 "c2": {
#                     "window_start": candle["window_start"],
#                     "open": candle["open"],
#                     "high": candle["high"],
#                     "low": candle["low"],
#                     "close": candle["close"],
#                     "range": candle.get("range"),
#                 },
#                 "c3": {
#                     "window_start": candle["window_start"],
#                     "open": candle["open"],
#                     "high": candle["high"],
#                     "low": candle["low"],
#                     "close": candle["close"],
#                     "range": candle.get("range"),
#                 },
#                 "status": "PENDING",
#                 "processed": False,
#             }

#             res = signals.insert_one(signal_doc)

#             dir_text = "BULLISH" if direction == 1 else "BEARISH"
#             print(
#                 f"[DETECTOR] ✅ New signal {res.inserted_id} | "
#                 f"{ts} | {dir_text} | body_pct={body_pct:.3f}"
#             )

#         except Exception as e:
#             print(f"[DETECTOR] ❌ Error in loop: {e}")

#         await asyncio.sleep(CHECK_INTERVAL)


# if __name__ == "__main__":
#     asyncio.run(detector_loop())
