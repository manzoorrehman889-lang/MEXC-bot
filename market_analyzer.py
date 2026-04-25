"""Main Market Analyzer - Continuously monitors MEXC for momentum opportunities"""

import time
import sys
import logging
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from mexc_client import MexcClient
from technical_analysis import KlineData
from signal_generator import generate_signal, TradingSignal, Direction
from config import (
    SCAN_INTERVAL_SECONDS, TOP_N_SYMBOLS, EXCLUDED_SYMBOLS,
    PRICE_CHANGE_WINDOW_MINUTES, VOLUME_AVG_WINDOW_MINUTES,
    CONSOLIDATION_LOOKBACK_MINUTES, IS_PRODUCTION
)

# Setup logging
logger = logging.getLogger(__name__)

# Use colorama only in development
if not IS_PRODUCTION:
    from colorama import init, Fore, Style
    init(autoreset=True)
else:
    # Dummy classes for production
    class _DummyStyle:
        def __getattr__(self, name):
            return ''
    Fore = _DummyStyle()
    Style = _DummyStyle()


class MarketAnalyzer:
    def __init__(self):
        self.client = MexcClient()
        self.symbols: List[str] = []
        self.ticker_data: Dict[str, Dict] = {}
        self.last_scan_time = 0
        
    def fetch_symbols(self) -> List[str]:
        """Fetch available USDT trading pairs"""
        logger.info("Fetching available symbols...")
        
        exchange_info = self.client.get_exchange_info()
        if not exchange_info:
            logger.error("Failed to fetch exchange info")
            return []
        
        symbols = []
        for symbol_info in exchange_info.get('symbols', []):
            symbol = symbol_info.get('symbol', '')
            
            # Filter for USDT pairs only
            if not symbol.endswith('USDT'):
                continue
            
            # Skip excluded patterns
            if any(excluded in symbol for excluded in EXCLUDED_SYMBOLS):
                continue
            
            # Check status (MEXC uses "1" for enabled)
            if str(symbol_info.get('status')) != '1':
                continue
            
            symbols.append(symbol)
        
        # Sort by 24h volume if available
        self.symbols = sorted(symbols)
        logger.info(f"Found {len(self.symbols)} valid USDT trading pairs")
        return self.symbols
    
    def fetch_ticker_data(self) -> Dict[str, Dict]:
        """Fetch 24h ticker data for all symbols"""
        tickers = self.client.get_ticker_24h()
        if tickers:
            self.ticker_data = {t['symbol']: t for t in tickers if 'symbol' in t}
        return self.ticker_data
    
    def fetch_klines_for_symbol(self, symbol: str) -> Optional[List[KlineData]]:
        """Fetch kline data for analysis"""
        # Fetch 60 minutes of 1m candles (need enough for calculations)
        limit = max(CONSOLIDATION_LOOKBACK_MINUTES, 60)
        
        klines_raw = self.client.get_klines(symbol, interval='1m', limit=limit)
        if not klines_raw or len(klines_raw) < 30:
            return None
        
        klines = [KlineData.from_list(k) for k in klines_raw]
        return klines
    
    def analyze_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """Analyze a single symbol for momentum signals"""
        try:
            klines = self.fetch_klines_for_symbol(symbol)
            if not klines:
                return None
            
            ticker = self.ticker_data.get(symbol)
            signal = generate_signal(symbol, klines, ticker)
            return signal
        except Exception as e:
            return None
    
    def scan_market(self) -> List[TradingSignal]:
        """Scan all symbols for trading signals"""
        if not self.symbols:
            self.fetch_symbols()
        
        # Refresh ticker data
        self.fetch_ticker_data()
        
        logger.info(f"Scanning {len(self.symbols)} symbols...")
        
        signals = []
        analyzed = 0
        
        # Use thread pool for parallel analysis
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.analyze_symbol, symbol): symbol 
                      for symbol in self.symbols}
            
            for future in as_completed(futures):
                symbol = futures[future]
                analyzed += 1
                
                if analyzed % 50 == 0:
                    logger.debug(f"Analyzed {analyzed}/{len(self.symbols)} symbols...")
                
                try:
                    signal = future.result(timeout=10)
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol}: {e}")
        
        # Sort by score (descending)
        signals.sort(key=lambda x: x.score, reverse=True)
        
        return signals
    
    def format_signal_output(self, signals: List[TradingSignal]) -> str:
        """Format signals for display"""
        if not signals:
            return f"\n{Fore.YELLOW}No high-quality momentum setups detected at this time.{Style.RESET_ALL}\n"
        
        output = []
        output.append(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        output.append(f"{Fore.GREEN}MOMENTUM TRADING SIGNALS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        output.append(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
        
        for i, signal in enumerate(signals[:10], 1):
            direction_color = Fore.GREEN if signal.direction == Direction.LONG else Fore.RED
            risk_color = Fore.GREEN if signal.risk_level.value == "Low" else (Fore.YELLOW if signal.risk_level.value == "Medium" else Fore.RED)
            
            output.append(f"{Fore.CYAN}#{i} {Fore.WHITE}{signal.symbol}{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Direction:{direction_color} {signal.direction.value}{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Confidence Score:{Fore.YELLOW} {signal.score:.0f}/100{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Entry Zone:{Fore.CYAN} {signal.entry_zone}{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Stop Loss:{Fore.RED} {signal.stop_loss}{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Take Profits:{Fore.GREEN} {signal.take_profit_zones}{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Risk Level:{risk_color} {signal.risk_level.value}{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Volume Spike:{Fore.MAGENTA} +{signal.volume_spike_pct:.1f}%{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Price Change (15m):{Fore.CYAN} {signal.price_change_pct:+.2f}%{Style.RESET_ALL}")
            output.append(f"  {Fore.WHITE}Reason: {signal.reason}{Style.RESET_ALL}")
            
            # Additional metrics
            add_data = signal.additional_data
            if add_data.get('rsi'):
                rsi_val = add_data['rsi']
                rsi_color = Fore.GREEN if 50 < rsi_val < 70 else (Fore.YELLOW if 30 < rsi_val < 80 else Fore.RED)
                output.append(f"  {Fore.WHITE}RSI:{rsi_color} {rsi_val:.1f}{Style.RESET_ALL}")
            
            if add_data.get('acceleration'):
                accel = add_data['acceleration']
                accel_color = Fore.GREEN if accel > 0 else Fore.RED
                output.append(f"  {Fore.WHITE}Acceleration:{accel_color} {accel:+.2f}%/min{Style.RESET_ALL}")
            
            output.append(f"{Fore.DIM}{'-'*80}{Style.RESET_ALL}\n")
        
        return "\n".join(output)
    
    def run_continuous_scan(self):
        """Run continuous market scanning"""
        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}MEXC MOMENTUM ANALYZER - Starting Continuous Scan{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Configuration:{Style.RESET_ALL}")
        print(f"  - Scan Interval: {SCAN_INTERVAL_SECONDS} seconds")
        print(f"  - Volume Spike Threshold: 200%+")
        print(f"  - RSI Bullish Zone: 55-75")
        print(f"  - RSI Bearish Zone: 25-45")
        print(f"  - Minimum Signal Score: 50/100")
        print(f"\n{Fore.CYAN}Press Ctrl+C to stop{Style.RESET_ALL}\n")
        
        try:
            while True:
                start_time = time.time()
                
                # Run scan
                signals = self.scan_market()
                
                # Display results
                output = self.format_signal_output(signals)
                print(output)
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(1, SCAN_INTERVAL_SECONDS - elapsed)
                
                if not signals:
                    print(f"{Fore.DIM}Next scan in {sleep_time:.0f} seconds...{Style.RESET_ALL}\n")
                else:
                    print(f"{Fore.CYAN}Found {len(signals)} signals. Next scan in {sleep_time:.0f} seconds...{Style.RESET_ALL}\n")
                
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Scan stopped by user.{Style.RESET_ALL}")
            sys.exit(0)
    
    def run_single_scan(self):
        """Run a single market scan"""
        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}MEXC MOMENTUM ANALYZER - Single Scan{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
        
        signals = self.scan_market()
        output = self.format_signal_output(signals)
        print(output)
        
        return signals


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MEXC Market Momentum Analyzer')
    parser.add_argument('--continuous', '-c', action='store_true',
                       help='Run continuous scanning')
    parser.add_argument('--interval', '-i', type=int, default=SCAN_INTERVAL_SECONDS,
                       help=f'Scan interval in seconds (default: {SCAN_INTERVAL_SECONDS})')
    
    args = parser.parse_args()
    
    analyzer = MarketAnalyzer()
    
    if args.continuous:
        # Override interval if provided
        if args.interval != SCAN_INTERVAL_SECONDS:
            import config
            config.SCAN_INTERVAL_SECONDS = args.interval
        analyzer.run_continuous_scan()
    else:
        analyzer.run_single_scan()


if __name__ == "__main__":
    main()
