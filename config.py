"""Configuration for MEXC Market Analysis"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
MEXC_API_KEY = os.getenv('MEXC_API_KEY', '')
MEXC_SECRET_KEY = os.getenv('MEXC_SECRET_KEY', '')
MEXC_BASE_URL = 'https://api.mexc.com'
MEXC_WS_URL = 'wss://wbs.mexc.com/ws'

# Analysis Parameters
PRICE_CHANGE_WINDOW_MINUTES = 15
VOLUME_AVG_WINDOW_MINUTES = 45
CONSOLIDATION_LOOKBACK_MINUTES = 60
MAX_ACCEPTABLE_CHANGE_PCT = 20

# RSI Settings
RSI_PERIOD = 14
RSI_BULLISH_MIN = 55
RSI_BULLISH_MAX = 75
RSI_BEARISH_MIN = 25
RSI_BEARISH_MAX = 45

# Volume Thresholds
MIN_VOLUME_SPIKE_PCT = 200  # 2x average
MAX_VOLUME_SPIKE_PCT = 500  # 5x average
MIN_USDT_VOLUME = 50000  # Minimum 24h volume in USDT

# Risk Parameters
MAX_SLIPPAGE_PCT = 5
STOP_LOSS_PCT_LONG = 3
STOP_LOSS_PCT_SHORT = 3
TAKE_PROFIT_ZONES = [1.5, 3, 5]  # R multiples

# Scanning Settings
SCAN_INTERVAL_SECONDS = int(os.getenv('SCAN_INTERVAL_SECONDS', '60'))
TOP_N_SYMBOLS = 100
EXCLUDED_SYMBOLS = ['UP', 'DOWN', 'BEAR', 'BULL', 'HALF', 'HEDGE']

# Ntfy Notification Settings
NTFY_ENABLED = os.getenv('NTFY_ENABLED', 'false').lower() == 'true'
NTFY_TOPIC = os.getenv('NTFY_TOPIC', '')
NTFY_SERVER = os.getenv('NTFY_SERVER', 'https://ntfy.sh')
NTFY_PRIORITY = os.getenv('NTFY_PRIORITY', 'high')  # low, default, high, urgent
NTFY_MIN_SCORE_NOTIFY = int(os.getenv('NTFY_MIN_SCORE_NOTIFY', '60'))  # Only notify for signals >= this score

# Railway/Production Settings
IS_PRODUCTION = os.getenv('RAILWAY_ENVIRONMENT', '') != '' or os.getenv('PRODUCTION', '').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
