"""Ntfy Push Notification Module"""

import requests
import json
from typing import Optional
from config import NTFY_ENABLED, NTFY_TOPIC, NTFY_SERVER, NTFY_PRIORITY


class NtfyNotifier:
    def __init__(self, topic: Optional[str] = None, server: Optional[str] = None):
        self.enabled = NTFY_ENABLED
        self.topic = topic or NTFY_TOPIC
        self.server = server or NTFY_SERVER
        
        if self.enabled and not self.topic:
            print("WARNING: NTFY_ENABLED but no NTFY_TOPIC set. Notifications disabled.")
            self.enabled = False
    
    def send_notification(self, title: str, message: str, 
                         priority: Optional[str] = None,
                         tags: Optional[list] = None,
                         actions: Optional[list] = None) -> bool:
        """Send push notification via ntfy"""
        if not self.enabled or not self.topic:
            return False
        
        url = f"{self.server}/{self.topic}"
        headers = {
            "Title": title.strip(),
            "Priority": (priority or NTFY_PRIORITY).strip(),
        }
        
        if tags:
            headers["Tags"] = ",".join(tags)
        
        if actions:
            headers["Actions"] = json.dumps(actions)
        
        try:
            response = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Ntfy notification failed: {e}")
            return False
    
    def notify_signal(self, signal) -> bool:
        """Send formatted notification for trading signal"""
        direction_emoji = "🟢" if signal.direction.value == "LONG" else "🔴"
        priority = "urgent" if signal.score >= 75 else NTFY_PRIORITY
        
        title = f"{direction_emoji} {signal.symbol} {signal.direction.value} Signal (Score: {signal.score:.0f})"
        
        message = f"""{signal.reason}

📊 Metrics:
• Volume Spike: +{signal.volume_spike_pct:.1f}%
• Price Change (15m): {signal.price_change_pct:+.2f}%
• Risk Level: {signal.risk_level.value}

🎯 Trade Setup:
• Entry: {signal.entry_zone}
• Stop Loss: {signal.stop_loss}
• Take Profits: {signal.take_profit_zones}
"""
        
        tags = ["chart_with_upwards_trend" if signal.direction.value == "LONG" else "chart_with_downwards_trend",
                "money_with_wings"]
        
        # Add MEXC trading URL action
        actions = [{
            "action": "view",
            "label": "Open MEXC",
            "url": f"https://www.mexc.com/exchange/{signal.symbol}"
        }]
        
        return self.send_notification(title, message, priority, tags, actions)
    
    def notify_startup(self, num_symbols: int) -> bool:
        """Notify that analyzer has started"""
        title = "🚀 MEXC Analyzer Started"
        message = f"Monitoring {num_symbols} USDT pairs for momentum signals.\nScan interval: {60}s"
        return self.send_notification(title, message, priority="default", tags=["rocket"])
    
    def notify_error(self, error_message: str) -> bool:
        """Notify about critical errors"""
        title = "⚠️ MEXC Analyzer Error"
        return self.send_notification(title, error_message, priority="high", tags=["warning"])
