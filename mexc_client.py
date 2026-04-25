"""MEXC API Client"""

import requests
import time
import hmac
import hashlib
import logging
from typing import Optional, Dict, List, Any
from config import MEXC_BASE_URL, MEXC_API_KEY, MEXC_SECRET_KEY, API_REQUEST_DELAY, RATE_LIMIT_BACKOFF

logger = logging.getLogger(__name__)


class MexcClient:
    def __init__(self):
        self.base_url = MEXC_BASE_URL
        self.api_key = MEXC_API_KEY
        self.secret_key = MEXC_SECRET_KEY
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_delay = API_REQUEST_DELAY
        
    def _generate_signature(self, params: Dict) -> str:
        """Generate HMAC signature for authenticated requests"""
        if not self.secret_key:
            return ''
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 authenticated: bool = False, retry_on_rate_limit: bool = True) -> Any:
        """Make API request with rate limiting"""
        # Rate limiting - ensure minimum delay between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if authenticated and self.api_key:
            params = params or {}
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
            headers['X-MEXC-APIKEY'] = self.api_key
        
        try:
            response = self.session.request(method, url, params=params, headers=headers, timeout=10)
            self.last_request_time = time.time()
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry_on_rate_limit:
                    logger.warning(f"Rate limited on {endpoint}, waiting {RATE_LIMIT_BACKOFF}s...")
                    time.sleep(RATE_LIMIT_BACKOFF)
                    return self._request(method, endpoint, params, authenticated, retry_on_rate_limit=False)
                else:
                    logger.debug(f"Rate limited (429) for {endpoint}")
                    return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.debug(f"API Error for {endpoint}: {e}")
            return None
    
    def get_ticker_24h(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get 24h ticker statistics"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/api/v3/ticker/24hr', params)
    
    def get_klines(self, symbol: str, interval: str = '1m', 
                   limit: int = 100, start_time: Optional[int] = None,
                   end_time: Optional[int] = None) -> List[List]:
        """Get kline/candlestick data
        
        Returns: List of [open_time, open, high, low, close, volume, close_time]
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        return self._request('GET', '/api/v3/klines', params)
    
    def get_exchange_info(self) -> Dict:
        """Get exchange information including trading pairs"""
        return self._request('GET', '/api/v3/exchangeInfo')
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book data"""
        return self._request('GET', '/api/v3/depth', {'symbol': symbol, 'limit': limit})
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        return self._request('GET', '/api/v3/trades', {'symbol': symbol, 'limit': limit})
