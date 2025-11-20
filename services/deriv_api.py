"""
shared/deriv_api.py
===================
Deriv API WebSocket wrapper
"""
import asyncio
import websockets
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import config

class DerivAPI:
    def __init__(self, use_auth: bool = False):
        self.ws = None
        self.use_auth = use_auth
        self.authorized = False
        self.callbacks = {}
        self.req_id = 0

    async def connect(self):
        """Connect to Deriv WebSocket."""
        self.ws = await websockets.connect(
            config.WS_URL,
            ping_interval=20,
            ping_timeout=20,
        )
        if self.use_auth:
            await self._authorize()

    async def _authorize(self):
        """Authorize with API token."""
        if not config.DERIV_API_TOKEN:
            raise Exception("DERIV_API_TOKEN not set")
        msg = {"authorize": config.DERIV_API_TOKEN}
        response = await self._send(msg)
        if "error" in response:
            raise Exception(f"Auth failed: {response['error']['message']}")
        self.authorized = True

    async def _send(self, msg):
        """Send a request and wait for its response."""
        self.req_id += 1
        msg["req_id"] = self.req_id
        await self.ws.send(json.dumps(msg))
        while True:
            response = await self.ws.recv()
            data = json.loads(response)
            # reply for this req_id?
            if data.get("req_id") == self.req_id:
                return data
            # otherwise treat as subscription
            await self._handle_subscription(data)

    async def _handle_subscription(self, data):
        """Dispatch subscription messages."""
        if "tick" in data:
            cb = self.callbacks.get("tick")
            if cb:
                await cb(data["tick"])
        elif "portfolio" in data:
            cb = self.callbacks.get("portfolio")
            if cb:
                await cb(data["portfolio"])

    async def subscribe_ticks(self, symbol, callback):
        """Subscribe to live ticks."""
        self.callbacks["tick"] = callback
        await self._send({"ticks": symbol, "subscribe": 1})

    async def get_candles_history(self, symbol, start_epoch, end_epoch):
        """Fetch historical 1‑minute candles."""
        request = {
            "ticks_history": symbol,
            "start": start_epoch,
            "end": end_epoch,
            "style": "candles",
            "granularity": 60,
            "count": 5000,
        }
        resp = await self._send(request)
        return resp.get("candles", [])

    async def get_balance(self):
        """Get account balance (requires auth)."""
        if not self.authorized:
            raise Exception("Not authorized")
        resp = await self._send({"balance": 1})
        if "balance" in resp:
            return float(resp["balance"]["balance"])
        return 0.0

    # async def buy_contract(self, symbol, amount, multiplier, limit_order):
    #     """Place a multiplier contract (requires auth)."""
    #     if not self.authorized:
    #         raise Exception("Not authorized")
    #     proposal = await self._send({
    #         "proposal": 1,
    #         "amount": amount,
    #         "basis": "stake",
    #         "contract_type": "MULTUP",
    #         "currency": "USD",
    #         "symbol": symbol,
    #         "multiplier": multiplier,
    #         "limit_order": limit_order,
    #     })
    #     if "error" in proposal:
    #         return None
    #     proposal_id = proposal["proposal"]["id"]
    #     response = await self._send({"buy": proposal_id, "price": amount})
    #     if "error" in response:
    #         return None
    #     return response.get("buy", {})
    
    async def buy_contract(self, symbol, amount, multiplier, contract_type="MULTUP", limit_order=None):
    
        if not self.authorized:
            raise Exception("Not authorized")
        
        # Direct buy (no proposal) - like working Colab code
        buy_msg = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "contract_type": "MULTUP",  # Will be set by executor
                "symbol": symbol,
                "amount": amount,
                "basis": "stake",
                "currency": "USD",
                "multiplier": multiplier,
                "limit_order": {
                    "stop_loss": round(abs(limit_order["stop_loss"]), 2),   # Positive value
                    "take_profit": round(abs(limit_order["take_profit"]), 2)
                }
            }
        }
        
        print(f"[API] Buying contract...")
        response = await self._send(buy_msg)
        
        if 'error' in response:
            print(f"[API] ❌ Buy error: {response['error']}")
            return None
        
        print(f"[API] ✅ Buy successful!")
        return response.get('buy', {})

    async def subscribe_portfolio(self, callback):
        """Subscribe to portfolio updates (requires auth)."""
        if not self.authorized:
            raise Exception("Not authorized")
        self.callbacks["portfolio"] = callback
        await self._send({"portfolio": 1, "subscribe": 1})

    async def close(self):
        """Close the WebSocket."""
        if self.ws:
            await self.ws.close()

    async def listen(self):
        """
        Continuously listen for subscription messages (ticks and portfolio) and
        dispatch them to the registered callbacks.  Call this once per connection,
        after you have sent any subscriptions.
        """
        while True:
            try:
                response = await self.ws.recv()
                data = json.loads(response)
                # Handle only subscription messages here.
                if "tick" in data or "portfolio" in data:
                    await self._handle_subscription(data)
            except Exception as e:
                # Stop listening on any error; outer code should reconnect.
                print(f"[API] Listen error: {e}")
                break
