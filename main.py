#!/usr/bin/env python3
"""Railway-compatible entry point with ntfy notifications"""

import logging
import sys
import time
from datetime import datetime
from market_analyzer import MarketAnalyzer
from ntfy_notifier import NtfyNotifier
from signal_generator import TradingSignal
from config import SCAN_INTERVAL_SECONDS, NTFY_MIN_SCORE_NOTIFY, IS_PRODUCTION, LOG_LEVEL

# Configure logging for Railway
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class RailwayAnalyzer:
    def __init__(self):
        self.analyzer = MarketAnalyzer()
        self.notifier = NtfyNotifier()
        self.last_notified_signals = set()  # Track recently notified signals
        
    def run(self):
        """Main loop for Railway deployment"""
        logger.info("="*60)
        logger.info("MEXC Momentum Analyzer - Railway Deployment")
        logger.info("="*60)
        
        if self.notifier.enabled:
            logger.info(f"Notifications enabled for topic: {self.notifier.topic}")
        else:
            logger.info("Notifications disabled (set NTFY_ENABLED=true to enable)")
        
        # Initial symbol fetch
        self.analyzer.fetch_symbols()
        
        if self.notifier.enabled:
            self.notifier.notify_startup(len(self.analyzer.symbols))
        
        logger.info(f"Scanning {len(self.analyzer.symbols)} symbols every {SCAN_INTERVAL_SECONDS}s")
        
        while True:
            try:
                self.scan_cycle()
                time.sleep(SCAN_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Error in scan cycle: {e}", exc_info=True)
                if self.notifier.enabled:
                    self.notifier.notify_error(str(e))
                time.sleep(10)  # Shorter retry on error
    
    def scan_cycle(self):
        """Single scan cycle"""
        start_time = time.time()
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Starting market scan...")
        
        # Run analysis
        signals = self.analyzer.scan_market()
        
        # Log results
        if signals:
            logger.info(f"Found {len(signals)} signals")
            self.process_signals(signals)
        else:
            logger.debug("No signals detected")
        
        elapsed = time.time() - start_time
        logger.info(f"Scan complete in {elapsed:.1f}s")
    
    def process_signals(self, signals: list):
        """Process and notify for new signals"""
        for signal in signals:
            # Create unique ID for this signal
            signal_id = f"{signal.symbol}_{signal.direction.value}_{signal.score:.0f}"
            
            # Log signal details
            logger.info(f"SIGNAL: {signal.symbol} | {signal.direction.value} | Score: {signal.score:.0f} | Vol: +{signal.volume_spike_pct:.1f}%")
            
            # Send notification for high-quality signals
            if signal.score >= NTFY_MIN_SCORE_NOTIFY:
                if signal_id not in self.last_notified_signals:
                    if self.notifier.notify_signal(signal):
                        self.last_notified_signals.add(signal_id)
                        logger.info(f"Notification sent for {signal.symbol}")
                else:
                    logger.debug(f"Already notified for {signal_id}")
        
        # Cleanup old signal IDs (keep last 100)
        if len(self.last_notified_signals) > 100:
            self.last_notified_signals = set(list(self.last_notified_signals)[-50:])


def main():
    """Entry point"""
    analyzer = RailwayAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
