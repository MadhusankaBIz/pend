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
    def __init__(self, use_auth=False):
        self.ws = None
        self.use_auth = use_auth
        self.authorized = False
        self.callbacks = {}
        self.req_id = 0
        
    async def connect(self):
        """Connect to Deriv WebSocket"""
        self.ws = await websockets.connect(
            config.WS_URL,
            ping_interval=20,
            ping_timeout=20
        )
        
        if self.use_auth:
            await self._authorize()
    
    async def _authorize(self):
        """Authorize with API token"""
        if not config.DERIV_API_TOKEN:
            raise Exception("DERIV_API_TOKEN not set")
        
        msg = {"authorize": config.DERIV_API_TOKEN}
        response = await self._send(msg)
        
        if 'error' in response:
            raise Exception(f"Auth failed: {response['error']['message']}")
        
        self.authorized = True
    
    async def _send(self, msg):
        """Send request and wait for response"""
        self.req_id += 1
        msg['req_id'] = self.req_id
        
        await self.ws.send(json.dumps(msg))
        
        while True:
            response = await self.ws.recv()
            data = json.loads(response)
            
            if data.get('req_id') == self.req_id:
                return data
            else:
                # Handle subscriptions
                await self._handle_subscription(data)
    
    async def _handle_subscription(self, data):
        """Handle subscription messages"""
        if 'tick' in data:
            cb = self.callbacks.get('tick')
            if cb:
                await cb(data['tick'])
        elif 'portfolio' in data:
            cb = self.callbacks.get('portfolio')
            if cb:
                await cb(data['portfolio'])
    
    async def subscribe_ticks(self, symbol, callback):
        """Subscribe to ticks"""
        self.callbacks['tick'] = callback
        msg = {"ticks": symbol, "subscribe": 1}
        await self._send(msg)
    
    async def get_candles_history(self, symbol, start_epoch, end_epoch):
        """Fetch historical 1-min candles"""
        msg = {
            "ticks_history": symbol,
            "start": start_epoch,
            "end": end_epoch,
            "style": "candles",
            "granularity": 60,
            "count": 5000
        }
        response = await self._send(msg)
        return response.get('candles', [])
    
    async def get_balance(self):
        """Get account balance (requires auth)"""
        if not self.authorized:
            raise Exception("Not authorized")
        
        msg = {"balance": 1}
        response = await self._send(msg)
        
        if 'balance' in response:
            return float(response['balance']['balance'])
        return 0.0
    
    async def buy_contract(self, symbol, amount, multiplier, limit_order):
        """Place multiplier contract (requires auth)"""
        if not self.authorized:
            raise Exception("Not authorized")
        
        # Get proposal
        proposal_msg = {
            "proposal": 1,
            "amount": amount,
            "basis": "stake",
            "contract_type": "MULTUP",
            "currency": "USD",
            "symbol": symbol,
            "multiplier": multiplier,
            "limit_order": limit_order
        }
        
        proposal = await self._send(proposal_msg)
        
        if 'error' in proposal:
            return None
        
        proposal_id = proposal['proposal']['id']
        
        # Buy
        buy_msg = {"buy": proposal_id, "price": amount}
        response = await self._send(buy_msg)
        
        if 'error' in response:
            return None
        
        return response.get('buy', {})
    
    async def subscribe_portfolio(self, callback):
        """Subscribe to portfolio updates (requires auth)"""
        if not self.authorized:
            raise Exception("Not authorized")
        
        self.callbacks['portfolio'] = callback
        msg = {"portfolio": 1, "subscribe": 1}
        await self._send(msg)
    
    async def close(self):
        """Close connection"""
        if self.ws:
            await self.ws.close()