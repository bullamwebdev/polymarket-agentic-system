#!/usr/bin/env python3
"""
Polymarket Daily Consortium Backtest — 2026-05-03
Parses paper trade journal, fetches live prices, computes PnL + metrics, writes reports.
"""

import json
import os
import re
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CLOB_HOST = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
PORTFOLIO_VALUE = 10000.0
RISK_CAP_PCT = 10.0

# Token ID cache for markets we know
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

class Position:
    def __init__(self, number: int, market: str, strategy: str, side: str,
                 entry: float, size: float, rationale: str = "", conviction: str = "", risk_budget: str = ""):
        self.number = number
        self.market = market.strip()
        self.strategy = strategy.strip()
        self.side = side.strip().upper()
        self.entry = float(entry)
        self.size = float(size)
        self.rationale = rationale
        self.conviction = conviction
        self.risk_budget = risk_budget
        self.current_price: Optional[float] = None
        self.token_id: Optional[str] = None
        self.pnl_usdc: float = 0.0
        self.pnl_pct: float = 0.0
        self.days_held: int = 1  # Since 2026-05-02

    def __repr__(self):
        return f"Position({self.number}: {self.market} {self.side} @ {self.entry})"

def parse_journal(path: str) -> List[Position]:
    """Parse paper trade journal markdown into Position objects"""
    positions = []
    with open(path, 'r') as f:
        content = f.read()

    # Find all tables with position data
    # Match rows in markdown tables: | # | Market | Strategy | Side | Entry | Size | ...
    lines = content.split('\n')
    in_position_table = False

    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]

        # Header detection
        if len(parts) >= 5 and parts[0] == '#' and parts[1] == 'Market':
            in_position_table = True
            continue
        if len(parts) >= 5 and parts[0] in ('#', '---', ''):
            continue
        if not in_position_table:
            continue

        # Data row: | # | Market | Strategy | Side | Entry Price | Size (USDC) | ... |
        if len(parts) >= 6:
            try:
                num = int(parts[0])
                market = parts[1]
                strategy = parts[2]
                side = parts[3]
                entry = float(parts[4])
                size = float(parts[5].replace('USDC', '').strip())
                pos = Position(num, market, strategy, side, entry, size)
                # Try to get token_id from cache
                pos.token_id = TOKEN_CACHE.get(market)
                # Skip duplicate positions (same market + same side)
                if not any(p.number == num for p in positions):
                    positions.append(pos)
            except (ValueError, IndexError):
                continue

    return positions

def fetch_midpoint(token_id: str) -> Optional[float]:
    if not token_id:
        return None
    try:
        url = f"{CLOB_HOST}/midpoint?token_id={token_id}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "mid" in data:
                return float(data["mid"])
            elif isinstance(data, (int, float)):
                return float(data)
            elif isinstance(data, str):
                try:
                    return float(data)
                except:
                    pass
        return None
    except Exception as e:
        print(f"Error fetching midpoint: {e}", file=sys.stderr)
        return None

def search_gamma_token(market_name: str) -> Optional[str]:
    """Search Gamma API for token_id by market title"""
    try:
        url = f"{GAMMA_API}/markets"
        params = {"active": "true", "closed": "false", "limit": "100"}
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        markets = r.json()
        # Try exact-ish match first
        search_lower = market_name.lower()
        for m in markets:
            title = m.get("question", "").lower()
            if search_lower in title or title in search_lower:
                tokens = m.get("tokens", [])
                for t in tokens:
                    if t.get("outcome", "").lower() == "yes":
                        return t.get("token_id")
                if tokens:
                    return tokens[0].get("token_id")
        # Fallback: keyword matching
        keywords = [w for w in search_lower.split() if len(w) > 3]
        for m in markets:
            title = m.get("question", "").lower()
            score = sum(1 for k in keywords if k in title)
            if score >= 2:
                tokens = m.get("tokens", [])
                for t in tokens:
                    if t.get("outcome", "").lower() == "yes":
                        return t.get("token_id")
                if tokens:
                    return tokens[0].get("token_id")
        return None
    except Exception as e:
        print(f"Gamma search error: {e}", file=sys.stderr)
        return None


def resolve_all_via_gamma() -> Dict[str, str]:
    """Bulk resolve all market token IDs from Gamma API"""
    try:
        url = f"{GAMMA_API}/markets"
        params = {"active": "true", "closed": "false", "limit": "500"}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return {}
        markets = r.json()
        resolved = {}
        name_map = {
            "Jesus Christ return before GTA VI": ["jesus", "gta"],
            "J.D. Vance 2028 GOP Nomination": ["vance", "2028"],
            "Gavin Newsom 2028 Dem Nomination": ["newsom", "2028"],
            "Xi Jinping out before 2027": ["xi", "jinping", "2027"],
            "AOC 2028 Dem Nomination": ["ocasio", "2028"],
            "China invades Taiwan by end 2026": ["china", "taiwan", "2026"],
            "Russia-Ukraine ceasefire by end 2026": ["ceasefire", "2026"],
            "Netanyahu out by end 2026": ["netanyahu", "2026"],
            "Dems control House 2026": ["democrats", "house", "2026"],
            "Zelenskyy out by end 2026": ["zelenskyy", "2026"],
        }
        for m in markets:
            title = m.get("question", "").lower()
            tokens = m.get("tokens", [])
            yes_token = None
            for t in tokens:
                if t.get("outcome", "").lower() == "yes":
                    yes_token = t.get("token_id")
                    break
            if not yes_token and tokens:
                yes_token = tokens[0].get("token_id")
            if not yes_token:
                continue
            for canonical, keywords in name_map.items():
                score = sum(1 for k in keywords if k in title)
                if score >= len(keywords) - 1:  # Allow 1 miss
                    resolved[canonical] = yes_token
                    break
        return resolved
    except Exception as e:
        print(f"Bulk gamma error: {e}", file=sys.stderr)
        return {}


def resolve_token_ids(positions: List[Position]) -> None:
    """Resolve missing token IDs via Gamma API"""
    # Try bulk resolution first
    bulk = resolve_all_via_gamma()
    resolved_count = 0
    for pos in positions:
        if pos.token_id:
            continue
        # Check bulk cache
        if pos.market in bulk:
            pos.token_id = bulk[pos.market]
            resolved_count += 1
            continue
        # Fallback to individual search
        tid = search_gamma_token(pos.market)
        if tid:
            pos.token_id = tid
            resolved_count += 1
    if resolved_count:
        print(f"  Resolved {resolved_count} token IDs via Gamma API")

def fetch_all_prices(positions: List[Position]) -> None:
    """Fetch current midpoint prices for all positions — CLOB first, Gamma fallback."""
    # First, try bulk Gamma API for fallback prices
    gamma_prices = _fetch_gamma_prices_bulk()
    
    for pos in positions:
        # Try CLOB midpoint first (most accurate for live markets)
        if pos.token_id:
            price = fetch_midpoint(pos.token_id)
            if price is not None:
                pos.current_price = price
                print(f"  {pos.market[:45]}...: {price:.4f} (clob)")
                continue
        # Then try Gamma match
        gamma_key = pos.market
        if gamma_key in gamma_prices:
            pos.current_price = gamma_prices[gamma_key]
            print(f"  {pos.market[:45]}...: {pos.current_price:.4f} (gamma)")
            continue
        print(f"  NO PRICE: {pos.market[:45]}...")

def _fetch_gamma_prices_bulk() -> Dict[str, float]:
    """Bulk fetch prices from Gamma API, return {market_name: yes_price}"""
    result = {}
    # Mapping of our short names to Gamma title substrings
    # MUST match very specifically — use exact title substrings
    name_map = {
        "Jesus Christ return before GTA VI": ["jesus christ", "gta"],
        "J.D. Vance 2028 GOP Nomination": ["j.d. vance", "republican presidential nomination"],
        "Gavin Newsom 2028 Dem Nomination": ["gavin newsom", "democratic presidential nomination"],
        "Xi Jinping out before 2027": ["xi jinping", "2027"],
        "AOC 2028 Dem Nomination": ["alexandria ocasio-cortez", "democratic presidential nomination"],
        "China invades Taiwan by end of 2026": ["china invade taiwan", "2026"],
        "Russia-Ukraine ceasefire by end 2026": ["russia", "ukraine", "ceasefire", "2026"],
        "Netanyahu out by end 2026": ["netanyahu out", "2026"],
        "Dems control House 2026": ["democratic party control the house", "2026"],
        "Zelenskyy out by end 2026": ["zelenskyy out", "ukraine", "2026"],
    }
    try:
        url = f"{GAMMA_API}/markets"
        params = {"active": "true", "closed": "false", "limit": "500"}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return result
        markets = r.json()
        for m in markets:
            title = m.get("question", "")
            outcome_prices = json.loads(m.get("outcomePrices", "[]"))
            if not outcome_prices:
                continue
            yes_price = float(outcome_prices[0])
            title_lower = title.lower()
            # Try matching each of our names
            for short_name, keywords in name_map.items():
                if short_name in result:
                    continue
                score = sum(1 for k in keywords if k in title_lower)
                # Need ALL keywords to match for specificity
                if score >= len(keywords):
                    result[short_name] = yes_price
                    break
    except Exception as e:
        print(f"Gamma bulk fetch error: {e}", file=sys.stderr)
    return result

def compute_pnl(positions: List[Position]) -> None:
    """Compute unrealized PnL for each position.
    
    For YES positions: entry is YES price, current is YES price.
    For NO positions: entry is NO price at entry time, current NO = 1 - current YES price.
    PnL = (current_side_price - entry_side_price) * size.
    """
    for pos in positions:
        if pos.current_price is None:
            pos.pnl_usdc = 0.0
            pos.pnl_pct = 0.0
            continue

        entry = pos.entry
        size = pos.size

        if pos.side == "YES":
            current = pos.current_price  # YES price
            pos.pnl_usdc = (current - entry) * size
            pos.pnl_pct = (current - entry) / entry * 100 if entry != 0 else 0
        else:  # NO
            # entry = NO price at entry (e.g., 0.61 means YES was 0.39)
            # current NO price = 1 - current YES price
            current_no = 1.0 - pos.current_price
            pos.pnl_usdc = (current_no - entry) * size
            pos.pnl_pct = (current_no - entry) / entry * 100 if entry != 0 else 0

def analyze_portfolio(positions: List[Position]) -> Dict:
    """Compute portfolio-level metrics"""
    total_pnl = sum(p.pnl_usdc for p in positions if p.current_price is not None)
    total_deployed = sum(p.size for p in positions)
    positions_with_price = [p for p in positions if p.current_price is not None]
    positions_missing = [p for p in positions if p.current_price is None]

    winners = [p for p in positions_with_price if p.pnl_usdc > 0]
    losers = [p for p in positions_with_price if p.pnl_usdc <= 0]

    hit_rate = len(winners) / len(positions_with_price) * 100 if positions_with_price else 0

    # Approximate Sharpe (using daily returns, assume 1 day)
    returns = [p.pnl_pct for p in positions_with_price]
    avg_return = sum(returns) / len(returns) if returns else 0
    std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
    sharpe_like = avg_return / std_return if std_return > 0 else 0

    # Strategy breakdown
    by_strategy: Dict[str, Dict] = {}
    for p in positions_with_price:
        s = p.strategy
        if s not in by_strategy:
            by_strategy[s] = {"pnl": 0.0, "count": 0, "wins": 0, "deployed": 0.0}
        by_strategy[s]["pnl"] += p.pnl_usdc
        by_strategy[s]["count"] += 1
        by_strategy[s]["deployed"] += p.size
        if p.pnl_usdc > 0:
            by_strategy[s]["wins"] += 1

    # Best/worst performers
    sorted_by_pnl = sorted(positions_with_price, key=lambda x: x.pnl_usdc, reverse=True)
    best = sorted_by_pnl[0] if sorted_by_pnl else None
    worst = sorted_by_pnl[-1] if sorted_by_pnl else None

    # Edge decay: compare expected edge vs actual PnL
    # Conservative expected edges from journal: Jesus +48%, Vance +15%, Newsom +5%, Xi +5%, AOC +8%
    expected_edges = {
        "Tail-end / arb": 48.0,
        "Short / divergence": 15.0,
        "Mean reversion MM": 5.0,
        "Tail-risk hedge": 5.0,
        "Volatility MM": 8.0,
        "Tail-risk": 5.0,
        "Divergence": 15.0,
        "Mean reversion / divergence": 30.0,
    }

    edge_decay = {}
    for s, data in by_strategy.items():
        expected = expected_edges.get(s, 5.0)
        actual = data["pnl"] / data["deployed"] * 100 if data["deployed"] > 0 else 0
        edge_decay[s] = {
            "expected": expected,
            "actual": actual,
            "decay": expected - actual
        }

    return {
        "total_pnl": total_pnl,
        "total_return_pct": total_pnl / PORTFOLIO_VALUE * 100,
        "total_deployed": total_deployed,
        "hit_rate": hit_rate,
        "sharpe_like": sharpe_like,
        "winners_count": len(winners),
        "losers_count": len(losers),
        "missing_price_count": len(positions_missing),
        "by_strategy": by_strategy,
        "best": best,
        "worst": worst,
        "edge_decay": edge_decay,
        "positions_with_price": positions_with_price,
        "positions_missing": positions_missing,
    }

def generate_recommendations(analysis: Dict) -> List[str]:
    """Generate actionable parameter tweaks"""
    recs = []
    total_return = analysis["total_return_pct"]
    hit_rate = analysis["hit_rate"]
    sharpe = analysis["sharpe_like"]

    # Portfolio-level
    if total_return > 1:
        recs.append(f"Portfolio up {total_return:.2f}%. Consider increasing Kelly fraction to 0.30.")
    elif total_return < -1:
        recs.append(f"Portfolio down {total_return:.2f}%. Reduce Kelly to 0.15 and tighten stops.")
    else:
        recs.append(f"Portfolio flat ({total_return:.2f}%). Hold current risk parameters.")

    if hit_rate < 40:
        recs.append(f"Hit rate {hit_rate:.0f}% below 40% threshold. Review signal quality.")
    elif hit_rate > 60:
        recs.append(f"Hit rate {hit_rate:.0f}% strong. Consider increasing position sizes by 15%.")

    # Strategy-level
    for strategy, data in analysis["by_strategy"].items():
        win_rate = data["wins"] / data["count"] * 100 if data["count"] > 0 else 0
        if data["pnl"] > 0 and data["count"] >= 2:
            recs.append(f"{strategy}: Profitable (+{data['pnl']:.2f} USDC, {win_rate:.0f}% win rate). Increase allocation by 10%.")
        elif data["pnl"] < 0:
            recs.append(f"{strategy}: Underperforming ({data['pnl']:.2f} USDC, {win_rate:.0f}% win rate). Review parameters or pause.")

    # Edge decay
    for strategy, decay in analysis["edge_decay"].items():
        if decay["decay"] > 20:
            recs.append(f"{strategy}: Edge decay {decay['decay']:.1f}pp. Market may be pricing this in — tighten entry criteria.")

    # Risk management
    total_deployed = analysis["total_deployed"]
    if total_deployed > PORTFOLIO_VALUE * RISK_CAP_PCT / 100:
        recs.append(f"Total deployed {total_deployed:.0f} USDC exceeds {RISK_CAP_PCT}% cap. Trim lowest-conviction positions.")

    return recs

def write_backtest_report(analysis: Dict, recommendations: List[str], today: str) -> str:
    """Write daily backtest markdown report"""
    report_path = os.path.join(
        os.path.dirname(__file__), '..', 'backtests', f'daily-backtest-{today}.md'
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, 'w') as f:
        f.write(f"# Daily Backtest Report — {today}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC\n")
        f.write(f"**Period:** 1 day (since 2026-05-02 entry)\n\n")

        f.write("## Portfolio Snapshot\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total PnL | {analysis['total_pnl']:+.2f} USDC |\n")
        f.write(f"| Total Return | {analysis['total_return_pct']:+.2f}% |\n")
        f.write(f"| Total Deployed | {analysis['total_deployed']:.0f} USDC |\n")
        f.write(f"| Hit Rate | {analysis['hit_rate']:.0f}% |\n")
        f.write(f"| Sharpe-like | {analysis['sharpe_like']:.2f} |\n")
        f.write(f"| Winners | {analysis['winners_count']} |\n")
        f.write(f"| Losers | {analysis['losers_count']} |\n")
        f.write(f"| Missing Prices | {analysis['missing_price_count']} |\n\n")

        f.write("## Position-Level PnL\n\n")
        f.write("| # | Market | Side | Entry | Current | Size | PnL (USDC) | PnL % | Strategy |\n")
        f.write("|---|--------|------|-------|---------|------|------------|-------|----------|\n")
        for p in analysis["positions_with_price"]:
            f.write(f"| {p.number} | {p.market[:40]} | {p.side} | {p.entry:.2f} | {p.current_price:.4f} | {p.size:.0f} | {p.pnl_usdc:+.2f} | {p.pnl_pct:+.1f}% | {p.strategy} |\n")
        if analysis["positions_missing"]:
            f.write("\n**Missing Prices (could not resolve):**\n\n")
            for p in analysis["positions_missing"]:
                f.write(f"- #{p.number}: {p.market} ({p.strategy})\n")

        f.write("\n## Strategy Performance\n\n")
        f.write("| Strategy | PnL | Trades | Win Rate | Deployed |\n")
        f.write("|----------|-----|--------|----------|----------|\n")
        for strategy, data in analysis["by_strategy"].items():
            win_rate = data["wins"] / data["count"] * 100 if data["count"] > 0 else 0
            f.write(f"| {strategy} | {data['pnl']:+.2f} | {data['count']} | {win_rate:.0f}% | {data['deployed']:.0f} |\n")

        f.write("\n## Edge Decay Analysis\n\n")
        f.write("| Strategy | Expected Edge | Actual | Decay |\n")
        f.write("|----------|--------------|--------|-------|\n")
        for strategy, decay in analysis["edge_decay"].items():
            f.write(f"| {strategy} | {decay['expected']:+.1f}% | {decay['actual']:+.1f}% | {decay['decay']:+.1f}pp |\n")

        f.write("\n## Best / Worst Performers\n\n")
        if analysis["best"]:
            b = analysis["best"]
            f.write(f"**Best:** #{b.number} {b.market} ({b.strategy}) — {b.pnl_usdc:+.2f} USDC ({b.pnl_pct:+.1f}%)\n\n")
        if analysis["worst"]:
            w = analysis["worst"]
            f.write(f"**Worst:** #{w.number} {w.market} ({w.strategy}) — {w.pnl_usdc:+.2f} USDC ({w.pnl_pct:+.1f}%)\n\n")

        f.write("## Recommendations\n\n")
        for rec in recommendations:
            f.write(f"- {rec}\n")

    return report_path

def append_journal_summary(analysis: Dict, recommendations: List[str], today: str) -> None:
    """Append summary to main journal file"""
    journal_path = os.path.join(
        os.path.dirname(__file__), '..', 'journal', f'paper-trades-2026-05-02.md'
    )

    summary = f"\n\n---\n\n## Daily Backtest — {today} 00:00 UTC\n\n"
    summary += f"**Total PnL:** {analysis['total_pnl']:+.2f} USDC ({analysis['total_return_pct']:+.2f}%)\n"
    summary += f"**Hit Rate:** {analysis['hit_rate']:.0f}% | **Sharpe:** {analysis['sharpe_like']:.2f}\n"
    summary += f"**Winners:** {analysis['winners_count']} | **Losers:** {analysis['losers_count']}\n\n"

    if analysis["best"]:
        b = analysis["best"]
        summary += f"**Best:** #{b.number} {b.market[:50]}... ({b.pnl_usdc:+.2f} USDC)\n"
    if analysis["worst"]:
        w = analysis["worst"]
        summary += f"**Worst:** #{w.number} {w.market[:50]}... ({w.pnl_usdc:+.2f} USDC)\n\n"

    summary += "**Recommendations:**\n"
    for rec in recommendations[:5]:
        summary += f"- {rec}\n"

    summary += f"\n*Next backtest: {(datetime.strptime(today, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')} 00:00 UTC*\n"

    with open(journal_path, 'a') as f:
        f.write(summary)

if __name__ == "__main__":
    today = datetime.now().strftime('%Y-%m-%d')
    journal_file = os.path.join(
        os.path.dirname(__file__), '..', 'journal', 'paper-trades-2026-05-02.md'
    )

    print(f"=== Polymarket Daily Backtest — {today} ===")
    print(f"Loading journal: {journal_file}")

    if not os.path.exists(journal_file):
        print(f"ERROR: Journal not found at {journal_file}")
        sys.exit(1)

    positions = parse_journal(journal_file)
    print(f"Parsed {len(positions)} positions")

    # Resolve missing token IDs
    print("\nResolving token IDs...")
    resolve_token_ids(positions)

    # Fetch prices
    print("\nFetching current prices...")
    fetch_all_prices(positions)

    # Compute PnL
    print("\nComputing PnL...")
    compute_pnl(positions)

    # Analyze
    print("\nAnalyzing performance...")
    analysis = analyze_portfolio(positions)

    # Recommendations
    recommendations = generate_recommendations(analysis)

    # Write reports
    print("\nWriting reports...")
    report_path = write_backtest_report(analysis, recommendations, today)
    print(f"Backtest report: {report_path}")

    append_journal_summary(analysis, recommendations, today)
    print(f"Journal summary appended")

    # Console summary
    print(f"\n=== SUMMARY ===")
    print(f"Total PnL: {analysis['total_pnl']:+.2f} USDC ({analysis['total_return_pct']:+.2f}%)")
    print(f"Hit Rate: {analysis['hit_rate']:.0f}%")
    print(f"Sharpe-like: {analysis['sharpe_like']:.2f}")
    if analysis["best"]:
        print(f"Best: #{analysis['best'].number} {analysis['best'].market[:40]}... ({analysis['best'].pnl_usdc:+.2f})")
    if analysis["worst"]:
        print(f"Worst: #{analysis['worst'].number} {analysis['worst'].market[:40]}... ({analysis['worst'].pnl_usdc:+.2f})")
    print(f"\nRecommendations:")
    for r in recommendations[:3]:
        print(f"  • {r}")
