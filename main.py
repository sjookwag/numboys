from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import pandas as pd
import os

app = FastAPI()

# Ensure directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_FILE = "crypto_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/data")
async def get_data(symbol: str = "BTC/USDT", timeframe: str = "1h"):
    conn = get_db_connection()
    query = "SELECT * FROM ohlcv WHERE symbol = ? AND timeframe = ? ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe))
    conn.close()
    
    if df.empty:
        return {"candlestick": [], "volume": []}
    
    candlestick_data = []
    volume_data = []
    for _, row in df.iterrows():
        time_sec = int(row["timestamp"] / 1000)
        candlestick_data.append({
            "time": time_sec,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
        })
        volume_data.append({
            "time": time_sec,
            "value": row["volume"],
            "color": "rgba(0, 150, 136, 0.8)" if row["close"] >= row["open"] else "rgba(255, 82, 82, 0.8)"
        })
        
    return {"candlestick": candlestick_data, "volume": volume_data}

@app.get("/api/symbols")
async def get_symbols():
    return ["BTC/USDT", "ETH/USDT", "XRP/USDT"]

@app.get("/api/timeframes")
async def get_timeframes():
    return ["1m", "15m", "30m", "1h", "4h", "1d"]
