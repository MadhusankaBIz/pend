import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv('.env.demo')
sys.path.insert(0, './shared')

from deriv_api import DerivAPI
import config

async def manual_trade():
    api = DerivAPI(use_auth=True)
    await api.connect()
    
    balance = await api.get_balance()
    print(f"Balance: ${balance}")
    
    # Use current market price (check Deriv app for real value)
    current_price = 143.4360 # REPLACE WITH ACTUAL R_50 PRICE
    
    sl = current_price - 1.0
    tp = current_price + 2.0
    
    print(f"\n🎯 Trade setup:")
    print(f"   Entry: ~{current_price}")
    print(f"   SL: {sl}")
    print(f"   TP: {tp}")
    print(f"   Stake: $15")
    print(f"   Multiplier: 200x")
    
    input("\nPress ENTER to place trade...")
    
    contract = await api.buy_contract(
        symbol="R_50",
        amount=15.0,
        multiplier=200,
        limit_order={
            "stop_loss": sl,
            "take_profit": tp
        }
    )
    
    if contract:
        print(f"\n✅ TRADE PLACED!")
        print(f"Contract ID: {contract.get('contract_id')}")
    else:
        print("\n❌ Failed")
    
    await api.close()

asyncio.run(manual_trade())