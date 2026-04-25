#!/usr/bin/env python3
"""Quick entry point for market analysis"""

import sys
from market_analyzer import MarketAnalyzer

def main():
    analyzer = MarketAnalyzer()
    signals = analyzer.run_single_scan()
    
    if not signals:
        print("No high-quality momentum setups detected at this time.")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
