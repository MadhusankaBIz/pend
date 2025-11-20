"""
services/executor/executor.py
=============================
Executes trades and monitors positions
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, '/app/shared')
from mongo_client import MongoDB
from deriv_api import DerivAPI
from calculator import calculate_stake, calculate_multiplier
import config

db = MongoDB()
api = None
executing = False

async def check_signals():
    """Check for pending trade signals"""
    signals = db.get_pending_signals()
    
    for signal in signals:
        await execute_trade(signal)
        db.mark_signal_processed(signal['_id'])

# async def execute_trade(signal):
#     """Execute trade from signal"""
#     global executing
    
#     if executing:
#         print("[EXECUTOR] ⚠️  Already executing - skipping")
#         return
    
#     executing = True
    
#     try:
#         c3 = signal['c3']
        
#         # Get real balance
#         balance = await api.get_balance()
#         print(f"[EXECUTOR] 💰 Balance: ${balance:.2f}")
        
#         # Calculate stake
#         stake = calculate_stake(balance)
#         print(f"[EXECUTOR] 📊 Stake: ${stake:.2f}")
        
#         # Calculate entry params
#         entry = c3['close']
#         doji_low = c3['low']
#         doji_high = c3['high']
#         doji_range = c3['range']
        
#         # Calculate SL with buffer
#         sl = doji_low - (config.SL_BUFFER_PCT * doji_range)
#         tp = doji_high
        
#         # Calculate multiplier
#         multiplier = calculate_multiplier(entry, sl, stake)
        
#         if multiplier is None:
#             print("[EXECUTOR] ⚠️  No valid multiplier - skipping")
#             return
        
#         print(f"[EXECUTOR] 🎯 Trade params:")
#         print(f"   Entry: {entry:.5f}")
#         print(f"   SL: {sl:.5f}")
#         print(f"   TP: {tp:.5f}")
#         print(f"   Multiplier: {multiplier}x")
#         print(f"   Stake: ${stake:.2f}")
        
#         # Place trade
#         contract = await api.buy_contract(
#             symbol=config.SYMBOL,
#             amount=stake,
#             multiplier=multiplier,
#             limit_order={
#                 "stop_loss": sl,
#                 "take_profit": tp
#             }
#         )
        
#         if not contract:
#             print("[EXECUTOR] ❌ Trade placement failed")
#             return
        
#         contract_id = contract.get('contract_id')
        
#         # Save trade record
#         trade = {
#             'contract_id': contract_id,
#             'pattern_id': signal['pattern_id'],
#             'symbol': config.SYMBOL,
#             'entry_time': datetime.utcnow(),
#             'entry_price': entry,
#             'sl': sl,
#             'tp': tp,
#             'stake': stake,
#             'multiplier': multiplier,
#             'status': 'OPEN',
#             'balance_before': balance,
#             'c1': signal['c1'],
#             'c2': signal['c2'],
#             'c3': signal['c3']
#         }
        
#         db.save_trade(trade)
        
#         print(f"[EXECUTOR] ✅ TRADE PLACED: {contract_id}")
#         print(f"[EXECUTOR] 🚀 Entry: {entry:.5f} | SL: {sl:.5f} | TP: {tp:.5f}")
        
#     except Exception as e:
#         print(f"[EXECUTOR] ❌ Error: {e}")
    
#     finally:
#         executing = False

async def execute_trade(signal):
    """Execute trade from signal"""
    global executing
    
    if executing:
        print("[EXECUTOR] ⚠️  Already executing - skipping")
        return
    
    executing = True
    
    try:
        c3 = signal['c3']
        
        # Determine direction from signal
        direction = signal.get('direction', 1)  # 1=bullish, 0=bearish
        contract_type = "MULTUP" if direction == 1 else "MULTDOWN"
        
        print(f"[EXECUTOR] 📊 Direction: {'BULLISH' if direction == 1 else 'BEARISH'}")
        
        # Get real balance
        balance = await api.get_balance()
        print(f"[EXECUTOR] 💰 Balance: ${balance:.2f}")
        
        # Calculate stake
        stake = calculate_stake(balance)
        print(f"[EXECUTOR] 📊 Stake: ${stake:.2f}")
        
        # Calculate entry params
        entry = c3['close']
        doji_low = c3['low']
        doji_high = c3['high']
        doji_range = c3['range']
        
        # SL/TP in USD (positive values)
        sl_usd = 10.0
        tp_usd = 15.0
        
        print(f"[EXECUTOR] 🎯 Trade params:")
        print(f"   Type: {contract_type}")
        print(f"   Entry: {entry:.5f}")
        print(f"   SL: ${sl_usd}")
        print(f"   TP: ${tp_usd}")
        print(f"   Multiplier: 200x")
        print(f"   Stake: ${stake:.2f}")
        
        # Place trade - need to modify deriv_api to accept contract_type
        contract = await api.buy_contract(
            symbol=config.SYMBOL,
            amount=stake,
            multiplier=200,
            contract_type=contract_type,  # Pass direction
            limit_order={
                "stop_loss": sl_usd,
                "take_profit": tp_usd
            }
        )
        
        if not contract:
            print("[EXECUTOR] ❌ Trade placement failed")
            return
        
        contract_id = contract.get('contract_id')
        
        # Save trade record
        trade = {
            'contract_id': contract_id,
            'pattern_id': signal['pattern_id'],
            'symbol': config.SYMBOL,
            'direction': direction,
            'contract_type': contract_type,
            'entry_time': datetime.utcnow(),
            'entry_price': entry,
            'sl': sl_usd,
            'tp': tp_usd,
            'stake': stake,
            'multiplier': 200,
            'status': 'OPEN',
            'balance_before': balance,
            'c1': signal['c1'],
            'c2': signal['c2'],
            'c3': signal['c3']
        }
        
        db.save_trade(trade)
        
        print(f"[EXECUTOR] ✅ TRADE PLACED: {contract_id}")
        print(f"[EXECUTOR] 🚀 {contract_type} | Entry: {entry:.5f} | SL: ${sl_usd} | TP: ${tp_usd}")
        
    except Exception as e:
        print(f"[EXECUTOR] ❌ Error: {e}")
    
    finally:
        executing = False

async def on_portfolio_update(portfolio):
    """Handle portfolio updates"""
    try:
        contracts = portfolio.get('contracts', [])
        
        for position in contracts:
            contract_id = position.get('contract_id')
            
            # Check if closed
            if position.get('is_sold', 0) == 1:
                await on_position_closed(contract_id, position)
    
    except Exception as e:
        print(f"[EXECUTOR] Portfolio error: {e}")

async def on_position_closed(contract_id, position):
    """Log closed position"""
    try:
        # Find trade
        trades = db.get_open_trades(config.SYMBOL)
        trade = next((t for t in trades if str(t['contract_id']) == str(contract_id)), None)
        
        if not trade:
            print(f"[EXECUTOR] ⚠️  Trade {contract_id} not found")
            return
        
        # Calculate P&L
        buy_price = position.get('buy_price', trade['stake'])
        sell_price = position.get('sell_price', 0)
        pnl = sell_price - buy_price
        
        result = 'TP' if pnl > 0 else 'SL'
        
        # Update trade
        updates = {
            'exit_time': datetime.utcnow(),
            'exit_price': position.get('exit_tick', trade.get('tp') if result == 'TP' else trade.get('sl')),
            'pnl': pnl,
            'status': 'CLOSED',
            'result': result,
            'sell_price': sell_price,
            'buy_price': buy_price
        }
        
        db.update_trade(contract_id, updates)
        
        # Save balance
        new_balance = await api.get_balance()
        db.save_balance(new_balance, contract_id, pnl)
        
        emoji = '✅' if pnl > 0 else '❌'
        print(f"[EXECUTOR] {emoji} Trade closed: {contract_id}")
        print(f"[EXECUTOR]    Result: {result}")
        print(f"[EXECUTOR]    P&L: ${pnl:.2f}")
        print(f"[EXECUTOR]    Balance: ${new_balance:.2f}")
        
    except Exception as e:
        print(f"[EXECUTOR] Error logging closed trade: {e}")

async def signal_checker():
    """Check for signals every 10 seconds"""
    while True:
        try:
            await check_signals()
        except Exception as e:
            print(f"[EXECUTOR] Signal checker error: {e}")
        
        await asyncio.sleep(10)

async def portfolio_monitor():
    """Monitor portfolio continuously"""
    global api
    
    while True:
        try:
            await api.connect()
            await api.subscribe_portfolio(on_portfolio_update)
            
            # Keep connection alive
            while True:
                await asyncio.sleep(60)
        
        except Exception as e:
            print(f"[EXECUTOR] Portfolio monitor error: {e}. Reconnecting...")
            await asyncio.sleep(5)

async def main():
    """Main loop"""
    global api
    
    print(f"[EXECUTOR] Starting for {config.SYMBOL}...")
    print(f"[EXECUTOR] Mode: {config.MODE}")
    print(f"[EXECUTOR] Base stake: ${config.BASE_STAKE}")
    
    # Initialize API with auth
    api = DerivAPI(use_auth=True)
    
    # Run both tasks
    await asyncio.gather(
        signal_checker(),
        # portfolio_monitor()
    )

if __name__ == '__main__':
    asyncio.run(main())




## **COMPLETE FILE TREE:**
# ```
# deriv_bot/
# ├── docker-compose.yml           ✅
# ├── .env.demo                    ✅
# ├── .env.live                    ✅
# ├── .gitignore                   ✅
# │
# ├── services/
# │   ├── ingestor/
# │   │   ├── Dockerfile           ✅
# │   │   ├── requirements.txt     ✅
# │   │   └── ingestor.py          ✅
# │   │
# │   ├── backfill/
# │   │   ├── Dockerfile           ✅
# │   │   ├── requirements.txt     ✅
# │   │   └── backfill.py          ✅
# │   │
# │   ├── aggregator/
# │   │   ├── Dockerfile           ✅
# │   │   ├── requirements.txt     ✅
# │   │   └── aggregator.py        ✅
# │   │
# │   ├── detector/
# │   │   ├── Dockerfile           ✅
# │   │   ├── requirements.txt     ✅
# │   │   └── detector.py          ✅
# │   │
# │   └── executor/
# │       ├── Dockerfile           ✅
# │       ├── requirements.txt     ✅
# │       └── executor.py          ✅
# │
# ├── shared/
# │   ├── __init__.py              ✅
# │   ├── config.py                ✅
# │   ├── mongo_client.py          ✅
# │   ├── deriv_api.py             ✅
# │   └── calculator.py            ✅
# │
# └── data/
#     └── .gitkeep                 ✅