"""
shared/mongo_client.py
======================
MongoDB connection helper
"""
from pymongo import MongoClient, ASCENDING
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import config

class MongoDB:
    def __init__(self):
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.DB_NAME]
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes"""
        # 1-min candles
        self.db[config.COLL_1M].create_index(
            [('symbol', ASCENDING), ('minute_start', ASCENDING)],
            unique=True
        )
        
        # 30-min candles
        self.db[config.COLL_30M].create_index(
            [('symbol', ASCENDING), ('window_start', ASCENDING)],
            unique=True
        )
        
        # Trades
        self.db[config.COLL_TRADES].create_index('contract_id', unique=True)
        self.db[config.COLL_TRADES].create_index('status')
    
    def save_1m_candle(self, candle):
        """Save 1-min candle"""
        self.db[config.COLL_1M].update_one(
            {'symbol': candle['symbol'], 'minute_start': candle['minute_start']},
            {'$set': candle},
            upsert=True
        )
    
    def save_30m_candle(self, candle):
        """Save 30-min candle"""
        self.db[config.COLL_30M].update_one(
            {'symbol': candle['symbol'], 'window_start': candle['window_start']},
            {'$set': candle},
            upsert=True
        )
    
    def get_1m_candles(self, symbol, start, end):
        """Get 1-min candles in range"""
        cursor = self.db[config.COLL_1M].find({
            'symbol': symbol,
            'minute_start': {'$gte': start, '$lt': end}
        }).sort('minute_start', ASCENDING)
        return list(cursor)
    
    def get_30m_candles(self, symbol, limit=3):
        """Get last N 30-min candles"""
        cursor = self.db[config.COLL_30M].find({
            'symbol': symbol
        }).sort('window_start', -1).limit(limit)
        return list(reversed(list(cursor)))
    
    def save_signal(self, signal):
        """Save trade signal"""
        self.db[config.COLL_SIGNALS].insert_one(signal)
    
    def get_pending_signals(self):
        """Get unprocessed signals"""
        cursor = self.db[config.COLL_SIGNALS].find({
            'processed': {'$ne': True}
        })
        return list(cursor)
    
    def mark_signal_processed(self, signal_id):
        """Mark signal as processed"""
        self.db[config.COLL_SIGNALS].update_one(
            {'_id': signal_id},
            {'$set': {'processed': True, 'processed_at': datetime.utcnow()}}
        )
    
    def save_trade(self, trade):
        """Save trade record"""
        self.db[config.COLL_TRADES].insert_one(trade)
    
    def update_trade(self, contract_id, updates):
        """Update trade"""
        self.db[config.COLL_TRADES].update_one(
            {'contract_id': contract_id},
            {'$set': updates}
        )
    
    def get_open_trades(self, symbol):
        """Get open trades"""
        cursor = self.db[config.COLL_TRADES].find({
            'symbol': symbol,
            'status': 'OPEN'
        })
        return list(cursor)
    
    def save_balance(self, balance, contract_id=None, pnl=None):
        """Save balance snapshot"""
        self.db[config.COLL_BALANCE].insert_one({
            'time': datetime.utcnow(),
            'balance': balance,
            'contract_id': contract_id,
            'pnl': pnl
        })
    
    def get_latest_balance(self):
        """Get most recent balance"""
        cursor = self.db[config.COLL_BALANCE].find().sort('time', -1).limit(1)
        results = list(cursor)
        return results[0]['balance'] if results else None