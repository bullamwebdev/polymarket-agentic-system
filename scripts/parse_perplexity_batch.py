#!/usr/bin/env python3
"""Batch parse Perplexity research into composite scores."""

import sys
sys.path.insert(0, '/home/noze-bot/.openclaw/workspace/polymarket-agentic-system/scripts')

from technicals import generate_binary_price_path, TechnicalSignal, market_cypher_signal
from scoring_engine import CompositeScore, PerplexitySignal

# All 10 positions with Perplexity research
positions = {
    "jesus": {
        "name": "Jesus Christ return before GTA VI",
        "side": "YES", "entry": 0.48, "current": 0.485, "size": 100,
        "pp_sentiment": "bullish", "pp_conviction": "moderate",
        "pp_verdict": "UNDERPRICED YES — fair ~0.50 vs 0.485",
        "contradicts": False,
        "48h": "NO"
    },
    "vance": {
        "name": "J.D. Vance 2028 GOP Nom",
        "side": "NO", "entry": 0.61, "current": 0.610, "size": 150,
        "pp_sentiment": "bullish", "pp_conviction": "moderate",
        "pp_verdict": "UNDERPRICED YES — fair 50-60% vs 39% implied",
        "contradicts": True,
        "48h": "NO"
    },
    "newsom": {
        "name": "Gavin Newsom 2028 Dem Nom",
        "side": "YES", "entry": 0.26, "current": 0.264, "size": 200,
        "pp_sentiment": "bullish", "pp_conviction": "strong",
        "pp_verdict": "UNDERPRICED — fair low-30s vs 26",
        "contradicts": False,
        "48h": "NO"
    },
    "xi": {
        "name": "Xi Jinping out before 2027",
        "side": "YES", "entry": 0.08, "current": 0.075, "size": 50,
        "pp_sentiment": "bearish", "pp_conviction": "weak",
        "pp_verdict": "FAIRLY PRICED — tail hedge not alpha",
        "contradicts": False,
        "48h": "NO"
    },
    "aoc": {
        "name": "AOC 2028 Dem Nom",
        "side": "YES", "entry": 0.09, "current": 0.083, "size": 100,
        "pp_sentiment": "bearish", "pp_conviction": "weak",
        "pp_verdict": "OVERPRICED — fair single-digit vs 8-10%",
        "contradicts": True,
        "48h": "NO"
    },
    "china": {
        "name": "China invades Taiwan by end 2026",
        "side": "YES", "entry": 0.07, "current": 0.074, "size": 100,
        "pp_sentiment": "bearish", "pp_conviction": "moderate",
        "pp_verdict": "OVERPRICED — fair 4-5% vs 7%",
        "contradicts": True,
        "48h": "NO"
    },
    "ceasefire": {
        "name": "RU-UA ceasefire by end 2026",
        "side": "YES", "entry": 0.26, "current": 0.255, "size": 150,
        "pp_sentiment": "bearish", "pp_conviction": "moderate",
        "pp_verdict": "SLIGHTLY OVERPRICED — fair low-20s vs 26%",
        "contradicts": True,
        "48h": "NO"
    },
    "netanyahu": {
        "name": "Netanyahu out by end 2026",
        "side": "YES", "entry": 0.44, "current": 0.435, "size": 100,
        "pp_sentiment": "bullish", "pp_conviction": "strong",
        "pp_verdict": "UNDERPRICED — fair low-50s vs 44%",
        "contradicts": False,
        "48h": "NO"
    },
    "demshouse": {
        "name": "Dems control House 2026",
        "side": "NO", "entry": 0.16, "current": 0.155, "size": 250,
        "pp_sentiment": "bullish", "pp_conviction": "moderate",
        "pp_verdict": "OVERPRICED NO — fair 20-30% vs 16%",
        "contradicts": True,
        "48h": "NO"
    },
    "zelenskyy": {
        "name": "Zelenskyy out by end 2026",
        "side": "YES", "entry": 0.16, "current": 0.155, "size": 50,
        "pp_sentiment": "bullish", "pp_conviction": "moderate",
        "pp_verdict": "FAIR to UNDERPRICED — fair mid-20s vs 16% entry",
        "contradicts": False,
        "48h": "NO"
    }
}

results = []
portfolio = {k: {"name": v["name"], "side": v["side"], "entry": v["entry"], "current": v["current"], "size": v["size"]} for k, v in positions.items()}

for key, pos in positions.items():
    # Generate synthetic price data
    prices = generate_binary_price_path(pos["entry"], pos["current"])
    volumes = [1000000/168] * 168
    
    # Create Perplexity signal
    pp = PerplexitySignal(
        key, pos["pp_sentiment"], pos["pp_conviction"],
        pos["pp_verdict"], pos["contradicts"]
    )
    
    # Score
    scorer = CompositeScore(key, portfolio[key])
    
    # Technical
    analysis = TechnicalSignal(key, prices, volumes).analyze()
    scorer.add_technical_score(analysis)
    
    # Cypher
    c1 = market_cypher_signal(prices, volumes, "1h")
    c4 = market_cypher_signal(prices[::4], [sum(volumes[i:i+4]) for i in range(0,len(volumes),4)], "4h")
    scorer.add_cypher_score(c1, c4)
    
    # Perplexity
    scorer.add_perplexity_score(pp)
    
    # Microstructure
    scorer.add_microstructure_score(0.02, 10.0, "stable")
    
    # Risk
    scorer.check_risk(portfolio, 0, 10000)
    
    result = scorer.compute()
    results.append((key, pos, result))

# Sort by total score (most negative = strongest sell signal)
results.sort(key=lambda x: x[2]["total_score"], reverse=True)

print("=" * 130)
print("🔥 COMPOSITE SCORING ENGINE — PERPLEXITY RESEARCH INTEGRATED")
print("=" * 130)
print(f"{'#':<3} {'Market':<35} {'Side':<5} {'Tech':<6} {'Cyph':<6} {'Pplx':<6} {'Risk':<6} {'TOTAL':<7} {'Dir':<7} {'Action':<25} {'Close?'}")
print("-" * 130)

for i, (key, pos, r) in enumerate(results, 1):
    scores = r.get("scores", {})
    tech = scores.get("technical", 0)
    cyph = scores.get("cypher", 0)
    pplx = scores.get("perplexity", 0)
    risk = scores.get("risk", 0)
    total = r["total_score"]
    direction = r["direction"]
    action = r["action"]
    
    side = pos["side"]
    if direction == "SHORT" and side == "YES":
        close_label = "🔴 CLOSE YES"
    elif direction == "LONG" and side == "NO":
        close_label = "🟢 CLOSE NO"
    elif r.get("contradicts_position"):
        close_label = "⚠️ CONTRADICTS"
    else:
        close_label = "✅ HOLDS"
    
    print(f"{i:<3} {pos['name'][:35]:<35} {side:<5} {tech:+5.1f}  {cyph:+5.1f}  {pplx:+5.1f}  {risk:+5.1f}  {total:+6.1f}  {direction:<7} {action[:25]:<25} {close_label}")

print("=" * 130)

# Summary
print("\n📊 SUMMARY:")
close_signals = [(k, p, r) for k, p, r in results if (r["direction"] == "SHORT" and p["side"] == "YES") or (r["direction"] == "LONG" and p["side"] == "NO")]
hold_signals = [(k, p, r) for k, p, r in results if not ((r["direction"] == "SHORT" and p["side"] == "YES") or (r["direction"] == "LONG" and p["side"] == "NO"))]

print(f"\n  🔴 CLOSE SIGNALS ({len(close_signals)}):")
for k, p, r in close_signals:
    size = p["size"]
    if p["side"] == "YES":
        print(f"    {p['name'][:30]:<30} Score: {r['total_score']:+5.1f} | CLOSE YES | Frees: {size} USDC")
    else:
        print(f"    {p['name'][:30]:<30} Score: {r['total_score']:+5.1f} | CLOSE NO | Frees: {size} USDC")

print(f"\n  ✅ HOLD SIGNALS ({len(hold_signals)}):")
for k, p, r in hold_signals:
    print(f"    {p['name'][:30]:<30} Score: {r['total_score']:+5.1f} | {r['direction']:<7} | {r['action'][:30]}")

# Calculate capital freed
freed = sum(p["size"] for k, p, r in close_signals)
print(f"\n  💰 Capital freed if all closes executed: {freed} USDC")
print(f"  New portfolio at risk: {sum(p['size'] for p in portfolio.values()) - freed} USDC")

# Risk status
total_at_risk = sum(p["size"] for p in portfolio.values())
print(f"\n  Current total at risk: {total_at_risk} USDC ({total_at_risk/10000:.1%} of portfolio)")
print(f"  Risk limit: 1000 USDC (10%)")
print(f"  Status: {'🚫 OVER LIMIT' if total_at_risk > 1000 else '✅ OK'}")

# Save results
output = []
for k, p, r in results:
    output.append(f"### {p['name']}\n")
    output.append(f"Score: {r['total_score']:+.1f}/10 | Direction: {r['direction']} | Action: {r['action']}\n")
    output.append(f"Perplexity: {p['pp_verdict']} | 48h Alert: {p['48h']}\n\n")

with open("journal/perplexity-batch-2026-05-03.md", "w") as f:
    f.write("# Perplexity Batch Analysis — 2026-05-03\n\n")
    f.write("".join(output))

print("\n✅ Saved to journal/perplexity-batch-2026-05-03.md")
