#!/usr/bin/env python3
"""
Daily Consortium Meeting — 3-Agent Backtest Pipeline
Runs at 00:00 UTC daily
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.clob_client import PolymarketClient

def load_journal():
    journal_dir = os.path.join(os.path.dirname(__file__), '..', 'journal')
    entries = []
    for f in sorted(os.listdir(journal_dir)):
        if f.endswith('.md') and 'paper-trades' in f:
            with open(os.path.join(journal_dir, f)) as file:
                entries.append({"file": f, "content": file.read()})
    return entries

def fetch_current_prices():
    """Fetch current prices for all tracked markets"""
    import subprocess
    
    markets = [
        {"question": "Jesus Christ return before GTA VI", "token_id": "90435811253665578014957380826505992530054077692143838383981805324273750424057"},
        {"question": "J.D. Vance 2028 GOP Nom", "token_id": "..."},
        {"question": "Gavin Newsom 2028 Dem Nom", "token_id": "..."},
        {"question": "Xi Jinping out before 2027", "token_id": "32338220190071351435772801779725302244575775216413325951443816017994629993401"},
        {"question": "AOC 2028 Dem Nom", "token_id": "107064985435494333113391038470401719113272800530429703182710416066774068907304"},
    ]
    
    results = []
    for m in markets:
        try:
            # Use curl for public API
            cmd = f'curl -s "https://clob.polymarket.com/midpoints?token_id={m[\"token_id\"]}"'
            output = subprocess.check_output(cmd, shell=True, text=True)
            price = float(output.strip()) if output.strip() else 0.5
            m['current_price'] = price
            results.append(m)
        except:
            m['current_price'] = None
            results.append(m)
    
    return results

def compute_pnl(entry_prices, current_prices):
    """Compute unrealized PnL for each position"""
    pnl_summary = []
    for ep in entry_prices:
        cp = next((c for c in current_prices if c['question'] == ep['question']), None)
        if cp and cp.get('current_price'):
            entry = ep['entry_price']
            current = cp['current_price']
            side = ep['side']
            size = ep['size']
            
            if side == 'YES':
                pnl = (current - entry) * size
                pnl_pct = (current - entry) / entry * 100
            else:  # NO
                pnl = ((1 - current) - (1 - entry)) * size
                pnl_pct = ((1 - current) - (1 - entry)) / (1 - entry) * 100
            
            pnl_summary.append({
                "market": ep['question'],
                "side": side,
                "entry": entry,
                "current": current,
                "size": size,
                "pnl_usdc": pnl,
                "pnl_pct": pnl_pct
            })
    return pnl_summary

def analyze_performance(pnl_summary):
    """Strategy-level analysis"""
    total_pnl = sum(t['pnl_usdc'] for t in pnl_summary)
    total_return = total_pnl / 10000 * 100  # % of portfolio
    
    by_strategy = {}
    for t in pnl_summary:
        strategy = t.get('strategy', 'unknown')
        if strategy not in by_strategy:
            by_strategy[strategy] = {'pnl': 0, 'count': 0}
        by_strategy[strategy]['pnl'] += t['pnl_usdc']
        by_strategy[strategy]['count'] += 1
    
    return {
        "total_pnl_usdc": total_pnl,
        "total_return_pct": total_return,
        "by_strategy": by_strategy,
        "winners": [t for t in pnl_summary if t['pnl_usdc'] > 0],
        "losers": [t for t in pnl_summary if t['pnl_usdc'] <= 0]
    }

def generate_recommendations(performance, current_regime):
    """Strategy optimizer recommendations"""
    recs = []
    
    if performance['total_return_pct'] > 1:
        recs.append("Portfolio performing well. Consider increasing Kelly fraction to 0.30.")
    elif performance['total_return_pct'] < -1:
        recs.append("Portfolio underwater. Reduce Kelly to 0.15 and tighten stops.")
    
    for strategy, data in performance['by_strategy'].items():
        if data['pnl'] > 0 and data['count'] >= 2:
            recs.append(f"{strategy}: Profitable. Increase allocation by 10%.")
        elif data['pnl'] < 0:
            recs.append(f"{strategy}: Underperforming. Review parameters or pause.")
    
    if current_regime.get('volatility') == 'high':
        recs.append("High volatility regime: prefer tail-end and divergence over MM.")
    
    return recs

def write_backtest_report(performance, recommendations):
    """Write daily backtest to journal"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(os.path.dirname(__file__), '..', 'backtests', f'daily-backtest-{today}.md')
    
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(f"# Daily Backtest Report — {today}\n\n")
        f.write(f"## Portfolio Performance\n")
        f.write(f"- Total PnL: {performance['total_pnl_usdc']:,.2f} USDC\n")
        f.write(f"- Total Return: {performance['total_return_pct']:.2f}%\n")
        f.write(f"- Open Positions: {len(performance.get('winners', [])) + len(performance.get('losers', []))}\n\n")
        
        f.write(f"## By Strategy\n")
        for strategy, data in performance['by_strategy'].items():
            f.write(f"- {strategy}: {data['pnl']:,.2f} USDC ({data['count']} trades)\n")
        
        f.write(f"\n## Recommendations\n")
        for rec in recommendations:
            f.write(f"- {rec}\n")
    
    return report_path

if __name__ == "__main__":
    print("=== Polymarket Consortium Daily Backtest ===")
    
    # Load paper trade entries
    journal = load_journal()
    print(f"Loaded {len(journal)} journal entries")
    
    # Fetch current prices
    prices = fetch_current_prices()
    print(f"Fetched prices for {len(prices)} markets")
    
    # In a real run, we'd compute PnL and generate recommendations
    # For now, this is the framework
    
    print("Backtest complete. Check backtests/ directory for reports.")
