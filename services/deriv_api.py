# """
# shared/deriv_api.py
# ===================
# Deriv API WebSocket wrapper
# """
# import asyncio
# import websockets
# import json
# import sys
# import os
# sys.path.insert(0, os.path.dirname(__file__))
# import config

# class DerivAPI:
#     def __init__(self, use_auth: bool = False):
#         self.ws = None
#         self.use_auth = use_auth
#         self.authorized = False
#         self.callbacks = {}
#         self.req_id = 0

#     async def connect(self):
#         """Connect to Deriv WebSocket."""
#         self.ws = await websockets.connect(
#             config.WS_URL,
#             ping_interval=20,
#             ping_timeout=20,
#         )
#         if self.use_auth:
#             await self._authorize()

#     async def _authorize(self):
#         """Authorize with API token."""
#         if not config.DERIV_API_TOKEN:
#             raise Exception("DERIV_API_TOKEN not set")
#         msg = {"authorize": config.DERIV_API_TOKEN}
#         response = await self._send(msg)
#         if "error" in response:
#             raise Exception(f"Auth failed: {response['error']['message']}")
#         self.authorized = True

#     async def _send(self, msg):
#         """Send a request and wait for its response."""
#         self.req_id += 1
#         msg["req_id"] = self.req_id
#         await self.ws.send(json.dumps(msg))
#         while True:
#             response = await self.ws.recv()
#             data = json.loads(response)
#             # reply for this req_id?
#             if data.get("req_id") == self.req_id:
#                 return data
#             # otherwise treat as subscription
#             await self._handle_subscription(data)

#     async def _handle_subscription(self, data):
#         """Dispatch subscription messages."""
#         if "tick" in data:
#             cb = self.callbacks.get("tick")
#             if cb:
#                 await cb(data["tick"])
#         elif "portfolio" in data:
#             cb = self.callbacks.get("portfolio")
#             if cb:
#                 await cb(data["portfolio"])

#     async def subscribe_ticks(self, symbol, callback):
#         """Subscribe to live ticks."""
#         self.callbacks["tick"] = callback
#         await self._send({"ticks": symbol, "subscribe": 1})

#     async def get_candles_history(self, symbol, start_epoch, end_epoch):
#         """Fetch historical 1‑minute candles."""
#         request = {
#             "ticks_history": symbol,
#             "start": start_epoch,
#             "end": end_epoch,
#             "style": "candles",
#             "granularity": 60,
#             "count": 5000,
#         }
#         resp = await self._send(request)
#         return resp.get("candles", [])

#     async def get_balance(self):
#         """Get account balance (requires auth)."""
#         if not self.authorized:
#             raise Exception("Not authorized")
#         resp = await self._send({"balance": 1})
#         if "balance" in resp:
#             return float(resp["balance"]["balance"])
#         return 0.0

#     # async def buy_contract(self, symbol, amount, multiplier, limit_order):
#     #     """Place a multiplier contract (requires auth)."""
#     #     if not self.authorized:
#     #         raise Exception("Not authorized")
#     #     proposal = await self._send({
#     #         "proposal": 1,
#     #         "amount": amount,
#     #         "basis": "stake",
#     #         "contract_type": "MULTUP",
#     #         "currency": "USD",
#     #         "symbol": symbol,
#     #         "multiplier": multiplier,
#     #         "limit_order": limit_order,
#     #     })
#     #     if "error" in proposal:
#     #         return None
#     #     proposal_id = proposal["proposal"]["id"]
#     #     response = await self._send({"buy": proposal_id, "price": amount})
#     #     if "error" in response:
#     #         return None
#     #     return response.get("buy", {})
    
#     # async def buy_contract(self, symbol, amount, multiplier, contract_type="MULTUP", limit_order=None):
    
#     #     if not self.authorized:
#     #         raise Exception("Not authorized")
        
#     #     # Direct buy (no proposal) - like working Colab code
#     #     buy_msg = {
#     #         "buy": 1,
#     #         "price": amount,
#     #         "parameters": {
#     #             "contract_type": "MULTUP",  # Will be set by executor
#     #             "symbol": symbol,
#     #             "amount": amount,
#     #             "basis": "stake",
#     #             "currency": "USD",
#     #             "multiplier": multiplier,
#     #             "limit_order": {
#     #                 "stop_loss": round(abs(limit_order["stop_loss"]), 2),   # Positive value
#     #                 "take_profit": round(abs(limit_order["take_profit"]), 2)
#     #             }
#     #         }
#     #     }
        
#     #     print(f"[API] Buying contract...")
#     #     response = await self._send(buy_msg)
        
#     #     if 'error' in response:
#     #         print(f"[API] ❌ Buy error: {response['error']}")
#     #         return None
        
#     #     print(f"[API] ✅ Buy successful!")
#     #     return response.get('buy', {})


#     async def buy_contract(self, symbol, amount, multiplier, contract_type="MULTUP", limit_order=None):
    
#         if not self.authorized:
#             raise Exception("Not authorized")
        
#         import websocket as ws_sync
#         import json
        
#         # Use sync websocket like working test
#         ws = ws_sync.create_connection(config.WS_URL)
        
#         # Authorize
#         ws.send(json.dumps({"authorize": config.DERIV_API_TOKEN}))
#         auth_resp = json.loads(ws.recv())
        
#         if "error" in auth_resp:
#             ws.close()
#             print(f"[API] ❌ Auth error: {auth_resp['error']}")
#             return None
        
#         # Direct buy
#         buy_msg = {
#             "buy": 1,
#             "price": amount,
#             "parameters": {
#                 "contract_type": contract_type,
#                 "symbol": symbol,
#                 "amount": amount,
#                 "basis": "stake",
#                 "currency": "USD",
#                 "multiplier": multiplier,
#                 "limit_order": {
#                     "stop_loss": round(abs(limit_order["stop_loss"]), 2),
#                     "take_profit": round(abs(limit_order["take_profit"]), 2)
#                 }
#             }
#         }
        
#         ws.send(json.dumps(buy_msg))
        
#         # Wait for buy response
#         while True:
#             msg = json.loads(ws.recv())
#             if msg.get("msg_type") == "buy":
#                 ws.close()
#                 print(f"[API] ✅ Buy successful!")
#                 return msg.get('buy', {})
#             elif "error" in msg:
#                 ws.close()
#                 print(f"[API] ❌ Buy error: {msg['error']}")
#                 return None
        
#     async def subscribe_portfolio(self, callback):
#         """Subscribe to portfolio updates (requires auth)."""
#         if not self.authorized:
#             raise Exception("Not authorized")
#         self.callbacks["portfolio"] = callback
#         await self._send({"portfolio": 1, "subscribe": 1})

#     async def close(self):
#         """Close the WebSocket."""
#         if self.ws:
#             await self.ws.close()

#     async def listen(self):
#         """
#         Continuously listen for subscription messages (ticks and portfolio) and
#         dispatch them to the registered callbacks.  Call this once per connection,
#         after you have sent any subscriptions.
#         """
#         while True:
#             try:
#                 response = await self.ws.recv()
#                 data = json.loads(response)
#                 # Handle only subscription messages here.
#                 if "tick" in data or "portfolio" in data:
#                     await self._handle_subscription(data)
#             except Exception as e:
#                 # Stop listening on any error; outer code should reconnect.
#                 print(f"[API] Listen error: {e}")
#                 break







"""
shared/deriv_api.py
===================
Thin Deriv API wrapper using synchronous websocket-client,
wrapped in async methods so the rest of the code can `await`
get_balance() and buy_contract().

Both auth and requests follow the same pattern you tested in
Colab (ws_auth + buy multiplier).  We avoid the async
`websockets` library completely here.

Requirements:
- websocket-client==1.8.0 (already in requirements)
"""

import json
import time
import asyncio
from typing import Tuple, Optional

import websocket  # websocket-client

import config


APP_ID = config.DERIV_APP_ID
DERIV_TOKEN = config.DERIV_API_TOKEN
WS_URL = config.WS_URL or f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"


class DerivAPI:
    def __init__(self, use_auth: bool = False):
        """
        use_auth is kept for compatibility with existing code.
        If use_auth=True we expect a valid DERIV_API_TOKEN in env/.env.
        """
        self.use_auth = use_auth
        if use_auth and not DERIV_TOKEN:
            raise RuntimeError("DERIV_API_TOKEN is empty – set it in your .env file.")

    # ------------------------------------------------------------------
    # Low-level synchronous helpers (same style as your Colab notebook)
    # ------------------------------------------------------------------
    def _ws_auth(self, timeout: float = 10.0) -> Tuple[websocket.WebSocket, str]:
        """
        Open a sync websocket, send authorize, and return (ws, loginid).
        Raises RuntimeError on auth error, TimeoutError on no response.
        """
        ws = websocket.create_connection(WS_URL)

        # send authorize
        ws.send(json.dumps({"authorize": DERIV_TOKEN}))
        t0 = time.time()

        while time.time() - t0 < timeout:
            raw = ws.recv()
            data = json.loads(raw)

            # Any Deriv error
            if "error" in data:
                try:
                    msg = data["error"].get("message", data["error"])
                except Exception:
                    msg = data["error"]
                ws.close()
                raise RuntimeError(f"Auth error: {msg}")

            # Successful authorize
            if data.get("msg_type") == "authorize" and "authorize" in data:
                loginid = data["authorize"].get("loginid", "<unknown>")
                # print(f"✅ Authorized: {loginid}")
                return ws, loginid

            # else: ignore (time/other)
        ws.close()
        raise TimeoutError("Timed out waiting for authorize response.")

    def _get_balance_sync(self) -> float:
        """
        Sync implementation of balance request using websocket-client.
        Called from async get_balance() via asyncio.to_thread.
        """
        ws, _ = self._ws_auth()
        ws.send(json.dumps({"balance": 1, "account": "current"}))

        balance_val: Optional[float] = None

        while True:
            data = json.loads(ws.recv())

            if "error" in data:
                ws.close()
                raise RuntimeError(f"Balance error: {data['error']}")

            if data.get("msg_type") == "balance" and "balance" in data:
                bal_obj = data["balance"]
                # Deriv returns "balance": {"balance": <amount>, "currency": "USD", ...}
                balance_val = float(bal_obj.get("balance", 0.0))
                break

        ws.close()
        if balance_val is None:
            raise RuntimeError("Did not receive balance from Deriv.")
        return balance_val

    def _buy_multiplier_sync(
        self,
        symbol: str,
        amount: float,
        multiplier: int,
        contract_type: str,
        stop_loss_usd: float,
        take_profit_usd: float,
    ) -> Optional[dict]:
        """
        Sync implementation of multiplier buy, mirroring your Colab
        `place_multiplier()` logic.
        Returns the raw 'buy' response dict, or None on failure.
        """
        ws, _ = self._ws_auth()

        buy_payload = {
            "buy": 1,
            "price": float(amount),
            "parameters": {
                "contract_type": contract_type,  # MULTUP / MULTDOWN
                "symbol": symbol,
                "amount": float(amount),
                "basis": "stake",
                "currency": "USD",
                "multiplier": int(multiplier),
                "limit_order": {
                    "stop_loss": float(stop_loss_usd),
                    "take_profit": float(take_profit_usd),
                },
            },
        }

        ws.send(json.dumps(buy_payload))
        contract_id = None
        buy_response = None

        while True:
            data = json.loads(ws.recv())

            if "error" in data:
                ws.close()
                raise RuntimeError(f"Buy error: {data['error']}")

            if data.get("msg_type") == "buy":
                buy_response = data["buy"]
                contract_id = buy_response.get("contract_id")
                # print(f"🛒 Bought multiplier | id={contract_id}")
                break

            # ignore unrelated messages

        # optional: one snapshot just to confirm open (can be removed to speed up)
        if contract_id is not None:
            ws.send(
                json.dumps(
                    {
                        "proposal_open_contract": 1,
                        "contract_id": int(contract_id),
                    }
                )
            )
            while True:
                data = json.loads(ws.recv())
                if data.get("msg_type") == "proposal_open_contract":
                    # we don't really need to store it; this is just a sanity ping
                    break

        ws.close()
        return buy_response

    # ------------------------------------------------------------------
    # Async public methods used by executor
    # ------------------------------------------------------------------
    async def get_balance(self) -> float:
        """
        Async wrapper for _get_balance_sync() so executor can `await` it.
        """
        return await asyncio.to_thread(self._get_balance_sync)

    async def buy_contract(
        self,
        symbol: str,
        amount: float,
        multiplier: int,
        contract_type: str,
        limit_order: dict,
    ) -> Optional[dict]:
        """
        Async wrapper for _buy_multiplier_sync().
        `limit_order` is expected to have `stop_loss` and `take_profit` in USD.
        Returns the 'buy' response dict (with contract_id, etc.).
        """
        sl_usd = float(limit_order.get("stop_loss", 0))
        tp_usd = float(limit_order.get("take_profit", 0))

        return await asyncio.to_thread(
            self._buy_multiplier_sync,
            symbol,
            amount,
            multiplier,
            contract_type,
            sl_usd,
            tp_usd,
        )

    # ------------------------------------------------------------------
    # No-op portfolio methods (kept for compatibility)
    # ------------------------------------------------------------------
    async def connect(self):
        """
        Kept for backwards compatibility.  We no longer maintain a long-lived
        async websocket connection from this class, because all critical
        operations now go through sync websocket-client calls.
        """
        return

    async def subscribe_portfolio(self, callback):
        """
        Stub method: you can later implement portfolio streaming using
        the same ws_auth pattern if you want, but executor currently
        does not call this in your latest version.
        """
        return
