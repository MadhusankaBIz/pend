"""
shared/config.py
================
Configuration constants
"""
import os

# MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'deriv_trading')

# Collections
COLL_1M = 'candles_1m'
COLL_30M = 'candles_30m'
COLL_SIGNALS = 'trade_signals'
COLL_TRADES = 'trades'
COLL_BALANCE = 'balance_history'

# Deriv API
DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN', '')
DERIV_APP_ID = os.getenv('DERIV_APP_ID', '1089')
WS_URL = os.getenv('WS_URL', f'wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}')

# Trading
SYMBOL = os.getenv('SYMBOL', 'R_50')
BASE_STAKE = float(os.getenv('BASE_STAKE', 15.0))
STAKE_INCREMENT = float(os.getenv('STAKE_INCREMENT', 2.5))
PROFIT_MILESTONE = float(os.getenv('PROFIT_MILESTONE', 500.0))
AVAILABLE_MULTIPLIERS = [200, 400, 600, 800]
BREATHING_MULTIPLE = float(os.getenv('BREATHING_MULTIPLE', 1.7))
DOJI_THRESHOLD = float(os.getenv('DOJI_THRESHOLD', 0.85))
SL_BUFFER_PCT = float(os.getenv('SL_BUFFER_PCT', 0.01))

# Mode
MODE = os.getenv('MODE', 'demo')