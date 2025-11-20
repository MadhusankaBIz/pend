import json
import websocket
from dotenv import load_dotenv
import os

load_dotenv('.env.demo')

APP_ID = "1089"
TOKEN = os.getenv('DERIV_API_TOKEN')

def place_trade():
    # Connect
    ws = websocket.create_connection(f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}")
    
    # Authorize
    print("🔐 Authorizing...")
    ws.send(json.dumps({"authorize": TOKEN}))
    auth_resp = json.loads(ws.recv())
    
    if "error" in auth_resp:
        print(f"❌ Auth error: {auth_resp['error']}")
        ws.close()
        return
    
    print(f"✅ Authorized: {auth_resp['authorize']['loginid']}")
    balance = auth_resp['authorize']['balance']
    print(f"💰 Balance: ${balance}")
    
    # Get current price
    print("\n📊 Getting current price...")
    ws.send(json.dumps({"ticks": "R_50", "subscribe": 1}))
    
    current_price = None
    while not current_price:
        msg = json.loads(ws.recv())
        if "tick" in msg:
            current_price = float(msg["tick"]["quote"])
            print(f"Current R_50: {current_price}")
            break
    
    # Calculate SL/TP
    sl = -5
    tp = 8
    
    print(f"\n🎯 Trade params:")
    print(f"   Current price: {current_price}")
    print(f"   SL: -$10.00")
    print(f"   TP: +$20.00")
    print(f"   Stake: $15")
    print(f"   Multiplier: 200x")
    
    input("\nPress ENTER to place trade...")
    
    # Place trade
    # Place trade - DIRECT BUY (like Colab)
    print("\n💳 Placing trade...")
    buy_msg = {
        "buy": 1,
        "price": 15,
        "parameters": {
            "contract_type": "MULTUP",
            "symbol": "R_50",
            "amount": 15,
            "basis": "stake",
            "currency": "USD",
            "multiplier": 200,
            "limit_order": {
                "stop_loss": 10,   # Positive value!
                "take_profit": 20
            }
        }
    }

    ws.send(json.dumps(buy_msg))

    buy_resp = None
    while not buy_resp:
        msg = json.loads(ws.recv())
        if msg.get("msg_type") == "buy":
            buy_resp = msg
            break
        elif "error" in msg:
            print(f"❌ Buy error: {json.dumps(msg['error'], indent=2)}")
            ws.close()
            return

    print(f"\n🎉 TRADE PLACED!")
    print(f"Contract ID: {buy_resp['buy']['contract_id']}")
    print(f"Buy price: ${buy_resp['buy']['buy_price']}")
    
    ws.close()

if __name__ == "__main__":
    place_trade()