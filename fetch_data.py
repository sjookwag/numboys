import ccxt
import sqlite3
import pandas as pd
import time
import os

DB_FILE = "crypto_data.db"
EXCHANGE = ccxt.bitget()
SYMBOLS = ["BTC/USDT", "ETH/USDT", "XRP/USDT"]
TIMEFRAMES = {
    "1m": 1440,
    "15m": 672,
    "30m": 672,
    "1h": 720,
    "4h": 540,
    "1d": 365,
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            symbol TEXT,
            timeframe TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.commit()
    return conn

def fetch_and_store_data(conn):
    for symbol in SYMBOLS:
        for timeframe, limit in TIMEFRAMES.items():
            print(f"Fetching {limit} candles for {symbol} at {timeframe}...")
            
            timeframe_ms = EXCHANGE.parse_timeframe(timeframe) * 1000
            # Calculate the starting time to fetch 'limit' number of candles
            since = EXCHANGE.milliseconds() - (limit * timeframe_ms)
            
            fetched_data = []
            while len(fetched_data) < limit:
                fetch_limit = min(1000, limit - len(fetched_data))
                try:
                    ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe, since=since, limit=fetch_limit)
                    if not ohlcv:
                        break
                    fetched_data.extend(ohlcv)
                    since = ohlcv[-1][0] + timeframe_ms
                    time.sleep(EXCHANGE.rateLimit / 1000)
                except Exception as e:
                    print(f"Error fetching {symbol} {timeframe}: {e}")
                    break
            
            if not fetched_data:
                continue
            
            df = pd.DataFrame(fetched_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['symbol'] = symbol
            df['timeframe'] = timeframe
            
            # Use a temporary table to insert or ignore duplicates
            df.to_sql("ohlcv_temp", conn, if_exists="replace", index=False)
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
                SELECT symbol, timeframe, timestamp, open, high, low, close, volume FROM ohlcv_temp
            """)
            conn.commit()
            print(f"Saved {len(fetched_data)} records for {symbol} {timeframe}")

if __name__ == "__main__":
    conn = init_db()
    fetch_and_store_data(conn)
    conn.close()
