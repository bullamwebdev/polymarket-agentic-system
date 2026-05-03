#!/usr/bin/env python3
"""
Polymarket Hourly Opportunity Scan — 2026-05-03 00:15 UTC
Checks all active non-sports markets for opportunities and alerts.
"""

import json
import os
import re
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

CLOB_HOST = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

PORTFOLIO_VALUE = 10000.0
RISK_CAP_PCT = 10.0
MOVE_ALERT_PCT = 5.0  # Alert if position moves >5% against entry
NEW_VOLUME_THRESHOLD = 1_000_000  # 1M USDC
RESOLUTION_ALERT_DAYS = 2  # Alert if market resolves within 48h
CORRELATED_MOVE_PCT = 3.0  # Alert if correlated cluster moves >3%

# Sports keywords to exclude
SPORTS_KEYWORDS = [
    "nba", "nfl", "mlb", "nhl", "fifa", "world cup", "super bowl", "stanley cup",
    "masters", "wimbledon", "olympic", "ufc", "boxing", "mma", "racing", "grand prix",
    "champions league", "premier league", "la liga", "serie a", "bundesliga",
    "mvp", "win the 2026", "finals", "tournament", "pga", "cy young",
    "mets", "yankees", "dodgers", "braves", "red sox", "astros",
    "cavaliers", "knicks", "celtics", "timberwolves", "thunder", "lakers", "magic",
    "hurricanes", "avalanche", "golden knights", "lightning", "wild", "flyers",
    "ducks", "canadiens", "sabres", "panthers", "predators", "blues", "stars",
    "raptors", "pistons", "76ers", "heat", "bulls", "nets", "bucks", "pacers",
    "hawks", "wizards", "kings", "warriors", "suns", "clippers", "mavericks",
    "nuggets", "trail blazers", "grizzlies", "rockets", "spurs", "jazz", "hornets",
]

class MarketSnapshot:
    def __init__(self, data: Dict):
        self.id = data.get("id", "")
        self.question = data.get("question", "")
        self.slug = data.get("slug", "")
        self.end_date = data.get("endDate", "")
        self.volume = float(data.get("volumeNum", 0))
        self.volume_24h = float(data.get("volume24hr", 0))
        self.liquidity = float(data.get("liquidityNum", 0))
        self.outcomes = json.loads(data.get("outcomes", "[]"))
        self.outcome_prices = json.loads(data.get("outcomePrices", "[]"))
        self.created_at = data.get("createdAt", "")
        self.updated_at = data.get("updatedAt", "")
        self.active = data.get("active", False)
        self.closed = data.get("closed", False)
        self.clob_token_ids = json.loads(data.get("clobTokenIds", "[]"))
        
    def is_sports(self) -> bool:
        q = self.question.lower()
        return any(sport in q for sport in SPORTS_KEYWORDS)
    
    def is_political(self) -> bool:
        q = self.question.lower()
        return any(k in q for k in ["election", "trump", "biden", "vance", "democrat", "republican", "gop", "president", "congress", "senate", "house", "vote", "ballot", "campaign"])
    
    def days_to_resolution(self) -> Optional[float]:
        try:
            if not self.end_date:
                return None
            end = datetime.fromisoformat(self.end_date.replace("Z", "+00:00"))
            now = datetime.now().astimezone()
            return (end - now).total_seconds() / 86400
        except:
            return None
    
    def __repr__(self):
        return f"Market({self.question[:40]}... vol={self.volume:.0f})"

def fetch_markets() -> List[MarketSnapshot]:
    """Fetch all active markets from Gamma API"""
    try:
        url = f"{GAMMA_API}/markets"
        params = {"active": "true", "closed": "false", "limit": "500"}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            print(f"Failed to fetch markets: {r.status_code}")
            return []
        data = r.json()
        markets = [MarketSnapshot(m) for m in data]
        return [m for m in markets if not m.is_sports()]
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

def load_journal_positions() -> List[Dict]:
    """Load tracked positions from journal"""
    journal_path = os.path.join(os.path.dirname(__file__), '..', 'journal', 'paper-trades-2026-05-02.md')
    if not os.path.exists(journal_path):
        return []
    
    positions = []
    with open(journal_path, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]
        
        if len(parts) >= 5 and parts[0] == '#' and parts[1] == 'Market':
            in_table = True
            continue
        if len(parts) >= 5 and parts[0] in ('#', '---', ''):
            continue
        if not in_table:
            continue
        
        if len(parts) >= 6:
            try:
                num = int(parts[0])
                market = parts[1]
                strategy = parts[2]
                side = parts[3]
                entry = float(parts[4])
                size = float(parts[5].replace('USDC', '').strip())
                positions.append({
                    "number": num,
                    "market": market,
                    "strategy": strategy,
                    "side": side,
                    "entry": entry,
                    "size": size
                })
            except (ValueError, IndexError):
                continue
    
    return positions

# Token ID cache (same as backtest script)
TOKEN_CACHE = {
    "Jesus Christ return before GTA VI": "90435811253665578014957380826505992530054077692143838383981805324273750424057",
    "J.D. Vance 2028 GOP Nomination": "40081275558852222228080198821361202017557872256707631666334039001378518619916",
    "Gavin Newsom 2028 Dem Nomination": "54533043819946592547517511176940999955633860128497669742211153063842200957669",
    "Xi Jinping out before 2027": "32338220190071351435772801779725302244575775216413325951443816017994629993401",
    "AOC 2028 Dem Nomination": "107064985435494333113391038470401719113272800530429703182710416066774068907304",
    "China invades Taiwan by end 2026": "94559586571241563470235664821564670251180951772614764383113614156422396181162",
    "Russia-Ukraine ceasefire by end 2026": "104071616575689490708756996503755160411785604144351427331378560378097635400347",
    "Netanyahu out by end 2026": "114694726451307654528948558967898493662917070661203465131156925998487819889437",
    "Dems control House 2026": "83247781037352156539108067944461291821683755894607244160607042790356561625563",
    "Zelenskyy out by end 2026": "108187737663325442737199857734058032845728149267925579081973309839049299838520",
}

def get_token_id(position: Dict) -> Optional[str]:
    """Get token ID for a tracked position"""
    return TOKEN_CACHE.get(position["market"])

def match_position_to_market(position: Dict, markets: List[MarketSnapshot]) -> Optional[MarketSnapshot]:
    """Find market snapshot matching a tracked position using exact title matching"""
    pos_name = position["market"].lower()
    
    # Try exact-ish match first
    for m in markets:
        q = m.question.lower()
        if pos_name in q or q in pos_name:
            return m
    
    # Keyword matching with stricter rules
    pos_words = [w for w in pos_name.split() if len(w) > 3]
    for m in markets:
        q = m.question.lower()
        score = sum(1 for w in pos_words if w in q)
        # Need ALL keywords to match for specificity
        if score >= len(pos_words) and len(pos_words) >= 2:
            return m
    return None

def check_position_moves(positions: List[Dict], markets: List[MarketSnapshot]) -> List[Dict]:
    """Alert if any tracked position moves >5% against entry"""
    alerts = []
    for pos in positions:
        # Try CLOB first for more accurate price
        token_id = get_token_id(pos)
        if token_id:
            try:
                r = requests.get(f"{CLOB_HOST}/midpoint?token_id={token_id}", timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, dict) and "mid" in data:
                        current_yes = float(data["mid"])
                    else:
                        current_yes = float(data)
                else:
                    current_yes = None
            except:
                current_yes = None
        else:
            current_yes = None
        
        # Fallback to Gamma
        if current_yes is None:
            market = match_position_to_market(pos, markets)
            if not market or not market.outcome_prices:
                continue
            try:
                current_yes = float(market.outcome_prices[0])
            except (IndexError, ValueError):
                continue
        
        entry = pos["entry"]
        side = pos["side"]
        size = pos["size"]
        
        if side == "YES":
            current = current_yes
            pnl_pct = (current - entry) / entry * 100
            move_against_pct = (entry - current) / entry * 100 if current < entry else 0
        else:  # NO
            current_no = 1.0 - current_yes
            pnl_pct = (current_no - entry) / entry * 100
            move_against_pct = (entry - current_no) / entry * 100 if current_no < entry else 0
        
        # Alert if moved >5% against position (PnL is negative and >5%)
        if move_against_pct > MOVE_ALERT_PCT:
            alerts.append({
                "type": "position_move",
                "severity": "high",
                "position": pos,
                "current_yes": current_yes,
                "pnl_pct": pnl_pct,
                "move_against": move_against_pct,
                "message": f"#{pos['number']} {pos['market'][:40]} moved {move_against_pct:.1f}% against. Entry {side} {entry:.4f}, current {current_yes:.4f} (PnL: {pnl_pct:+.1f}%)"
            })
    
    return alerts

def check_new_high_volume_markets(markets: List[MarketSnapshot], last_scan_time: datetime) -> List[Dict]:
    """Alert if new market launched with >1M volume"""
    alerts = []
    for m in markets:
        if m.volume < NEW_VOLUME_THRESHOLD:
            continue
        try:
            created = datetime.fromisoformat(m.created_at.replace("Z", "+00:00"))
            if created > last_scan_time:
                alerts.append({
                    "type": "new_market",
                    "severity": "medium",
                    "market": m,
                    "message": f"New high-volume market: {m.question[:60]}... ({m.volume:.0f} USDC vol)"
                })
        except:
            continue
    return alerts

def check_resolution_approaching(markets: List[MarketSnapshot]) -> List[Dict]:
    """Alert if any market resolves within 48h"""
    alerts = []
    for m in markets:
        days = m.days_to_resolution()
        if days is not None and 0 < days <= RESOLUTION_ALERT_DAYS:
            try:
                current_yes = float(m.outcome_prices[0])
            except:
                current_yes = None
            alerts.append({
                "type": "resolution_approaching",
                "severity": "high",
                "market": m,
                "days_remaining": days,
                "current_yes": current_yes,
                "message": f"RESOLUTION ALERT: {m.question[:50]}... resolves in {days:.1f}d (YES @ {current_yes})"
            })
    return alerts

def check_correlated_cluster(markets: List[MarketSnapshot], positions: List[Dict]) -> List[Dict]:
    """Check if correlated tracked positions move together >3%"""
    # Group tracked positions by correlation theme (only check OUR positions)
    themes = {
        "2028_nominations": ["J.D. Vance 2028 GOP Nomination", "Gavin Newsom 2028 Dem Nomination", "AOC 2028 Dem Nomination"],
        "china_taiwan": ["China invades Taiwan by end 2026", "Xi Jinping out before 2027"],
        "ukraine_russia": ["Russia-Ukraine ceasefire by end 2026", "Zelenskyy out by end 2026"],
        "israel_netanyahu": ["Netanyahu out by end 2026"],
        "us_house_senate": ["Dems control House 2026"],
    }
    
    # Pre-build market lookup by token_id for exact matching
    market_by_tid = {}
    for m in markets:
        try:
            token_ids = json.loads(m.get("clobTokenIds", "[]"))
            for tid in token_ids:
                market_by_tid[tid] = m
        except:
            pass
    
    alerts = []
    for theme_name, market_names in themes.items():
        moved = []
        for pos in positions:
            if pos["market"] not in market_names:
                continue
            # Exact match by token_id
            tid = get_token_id(pos)
            if tid and tid in market_by_tid:
                m = market_by_tid[tid]
                if m.outcome_prices:
                    try:
                        current_yes = float(m.outcome_prices[0])
                        entry = pos["entry"]
                        side = pos["side"]
                        if side == "YES":
                            move = (current_yes - entry) / entry * 100
                        else:
                            current_no = 1.0 - current_yes
                            move = (current_no - entry) / entry * 100
                        moved.append({"pos": pos, "move": move, "market": m})
                    except:
                        continue
        
        if len(moved) >= 2:
            avg_move = sum(m["move"] for m in moved) / len(moved)
            if abs(avg_move) > CORRELATED_MOVE_PCT:
                direction = "UP" if avg_move > 0 else "DOWN"
                alerts.append({
                    "type": "correlated_cluster",
                    "severity": "medium",
                    "theme": theme_name,
                    "markets": moved,
                    "avg_move": avg_move,
                    "message": f"Correlated cluster '{theme_name}' moving {direction} {abs(avg_move):.1f}% ({len(moved)} positions)"
                })
    
    return alerts

def write_alerts_report(alerts: List[Dict], markets: List[MarketSnapshot]) -> str:
    """Write hourly alerts to journal"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    
    report_path = os.path.join(os.path.dirname(__file__), '..', 'journal', f'hourly-alerts-{today}.md')
    
    with open(report_path, 'a') as f:
        f.write(f"\n\n## Hourly Scan — {now} UTC\n\n")
        
        if not alerts:
            f.write("✅ **No alerts triggered.** All positions within normal ranges.\n\n")
        else:
            f.write(f"⚠️ **{len(alerts)} alert(s) triggered**\n\n")
            
            for alert in alerts:
                severity = alert.get("severity", "medium")
                emoji = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
                f.write(f"{emoji} **{alert['type'].upper()}** ({severity})\n")
                f.write(f"{alert['message']}\n\n")
                
                if alert["type"] == "position_move":
                    f.write(f"  - Entry: {alert['position']['side']} @ {alert['position']['entry']:.4f}\n")
                    f.write(f"  - Current YES: {alert['current_yes']:.4f}\n")
                    f.write(f"  - PnL: {alert['pnl_pct']:+.1f}%\n")
                    f.write(f"  - **Action:** Review stop-loss / exit trigger\n\n")
                
                elif alert["type"] == "new_market":
                    m = alert["market"]
                    f.write(f"  - Volume: {m.volume:.0f} USDC\n")
                    f.write(f"  - Volume 24h: {m.volume_24h:.0f} USDC\n")
                    f.write(f"  - **Action:** Evaluate for new position\n\n")
                
                elif alert["type"] == "resolution_approaching":
                    m = alert["market"]
                    f.write(f"  - Resolves in: {alert['days_remaining']:.1f} days\n")
                    if alert.get("current_yes"):
                        f.write(f"  - Current YES: {alert['current_yes']:.4f}\n")
                    f.write(f"  - **Action:** Prepare exit / reduce exposure\n\n")
                
                elif alert["type"] == "correlated_cluster":
                    f.write(f"  - Theme: {alert['theme']}\n")
                    f.write(f"  - Markets affected: {len(alert['markets'])}\n")
                    f.write(f"  - Average move: {alert['avg_move']:+.1f}%\n")
                    f.write(f"  - **Action:** Review portfolio hedging\n\n")
        
        # Price table for all tracked positions (CLOB first, Gamma fallback)
        f.write("### Tracked Positions Price Table\n\n")
        f.write("| # | Market | Side | Entry | Current YES | Current NO | Move from Entry |\n")
        f.write("|---|--------|------|-------|-------------|------------|------------------|\n")
        
        for pos in positions:
            # Try CLOB first
            token_id = get_token_id(pos)
            current_yes = None
            if token_id:
                try:
                    r = requests.get(f"{CLOB_HOST}/midpoint?token_id={token_id}", timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, dict) and "mid" in data:
                            current_yes = float(data["mid"])
                        else:
                            current_yes = float(data)
                except:
                    pass
            
            # Fallback to Gamma
            if current_yes is None:
                market = match_position_to_market(pos, markets)
                if market and market.outcome_prices:
                    try:
                        current_yes = float(market.outcome_prices[0])
                    except:
                        current_yes = None
            
            entry = pos["entry"]
            side = pos["side"]
            if current_yes is not None:
                current_no = 1.0 - current_yes
                if side == "YES":
                    move = (current_yes - entry) / entry * 100
                else:
                    move = (current_no - entry) / entry * 100
                f.write(f"| {pos['number']} | {pos['market'][:40]} | {side} | {entry:.4f} | {current_yes:.4f} | {current_no:.4f} | {move:+.1f}% |\n")
            else:
                f.write(f"| {pos['number']} | {pos['market'][:40]} | {side} | {entry:.4f} | — | — | — |\n")
        
        f.write(f"\n---\n")
    
    return report_path

if __name__ == "__main__":
    print(f"=== Polymarket Hourly Scan — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC ===")
    
    # Load tracked positions
    positions = load_journal_positions()
    print(f"Loaded {len(positions)} tracked positions")
    
    # Fetch markets
    print("Fetching active non-sports markets...")
    markets = fetch_markets()
    print(f"Fetched {len(markets)} non-sports markets")
    
    # Run checks
    print("Checking for alerts...")
    alerts = []
    
    alerts.extend(check_position_moves(positions, markets))
    print(f"  Position moves: {len([a for a in alerts if a['type'] == 'position_move'])}")
    
    # Last scan time (use 24h ago as default for "new" market detection)
    last_scan = datetime.now().astimezone() - timedelta(hours=1)
    alerts.extend(check_new_high_volume_markets(markets, last_scan))
    print(f"  New high-volume markets: {len([a for a in alerts if a['type'] == 'new_market'])}")
    
    alerts.extend(check_resolution_approaching(markets))
    print(f"  Resolution approaching: {len([a for a in alerts if a['type'] == 'resolution_approaching'])}")
    
    alerts.extend(check_correlated_cluster(markets, positions))
    print(f"  Correlated clusters: {len([a for a in alerts if a['type'] == 'correlated_cluster'])}")
    
    # Write report
    report_path = write_alerts_report(alerts, markets)
    print(f"\nAlerts written to: {report_path}")
    
    # Console summary
    if alerts:
        print(f"\n=== ALERTS ({len(alerts)}) ===")
        for a in alerts:
            severity = a.get('severity', 'medium')
            emoji = "🔴" if severity == 'high' else "🟡"
            print(f"{emoji} [{severity.upper()}] {a['message']}")
    else:
        print("\n✅ No alerts — all quiet")
    
    print(f"\nScan complete.")
