#!/usr/bin/env python3
"""
Polymarket Composite Scoring Engine v1.0

Compiles ALL signal sources into a single trade decision score.
Auto-execution threshold: |score| >= 7/10 with risk check pass.

Signal Sources:
  1. Technical Indicators (RSI, EMA Cross, MACD, Bollinger, Supertrend, MFI, W/M)
  2. Market Cypher Green/Red Dot (1H + 4H)
  3. Perplexity Research Sentiment (bullish/bearish/neutral + conviction)
  4. Market Microstructure (spread, depth, volume trend)
  5. Risk Compliance (position limits, correlation, stop-loss)

Output: CompositeScore with direction, magnitude, confidence, and action.
"""

import json, os, math
from datetime import datetime
from typing import List, Dict, Optional, Tuple

sys_path = os.path.expanduser("~/.openclaw/workspace/polymarket-agentic-system/scripts")
import sys
sys.path.insert(0, sys_path)

from technicals import (
    TechnicalSignal, market_cypher_signal, run_full_analysis,
    rsi, ema, macd, bollinger_bands, supertrend, money_flow_index,
    detect_w_structure, detect_m_structure, support_resistance_levels
)


# ============ SCORING WEIGHTS (backtest-calibrated) ============

WEIGHTS = {
    "technical": {
        "rsi_extreme":       1.5,  # RSI < 25 or > 75
        "ema_cross":         1.0,  # EMA 9/21 cross
        "macd_divergence":   1.0,  # MACD histogram divergence
        "bollinger_extreme": 0.5,  # Price at band edge
        "supertrend":        0.8,  # Directional trend
        "mfi_extreme":       0.5,  # MFI < 20 or > 80
        "w_bottom":          1.0,  # Double support test
        "m_top":             1.0,  # Double resistance test
        "support_touch":     0.5,  # Price near support
        "resistance_touch":  0.5,  # Price near resistance
    },
    "cypher": {
        "green_dot_1h":      1.5,  # Market Cypher 1H green
        "green_dot_4h":      2.0,  # Market Cypher 4H green (stronger)
        "red_dot_1h":        1.5,  # Market Cypher 1H red
        "red_dot_4h":        2.0,  # Market Cypher 4H red (stronger)
    },
    "perplexity": {
        "strong_bullish":    4.0,  # Clear buy signal with high conviction
        "moderate_bullish":  2.5,  # Mild buy signal
        "strong_bearish":    4.0,  # Clear sell signal with high conviction
        "moderate_bearish":  2.5,  # Mild sell signal
        "neutral":           0.0,  # No opinion
    },
    "microstructure": {
        "spread_narrow":     0.5,  # Spread < 2% (good execution)
        "depth_adequate":    0.5,  # Orderbook depth > 5x size
        "volume_rising":     0.5,  # Volume trend increasing
        "spread_wide":      -0.5,  # Spread > 5% (bad execution)
    },
    "risk": {
        "position_within_limit":   0.0,  # No bonus/penalty for compliance
        "position_over_limit":    -3.0,  # Hard block if over risk limit
        "correlation_breach":     -2.0,  # Same-event cluster risk
        "daily_stop_breach":      -5.0,  # Daily loss limit hit = BLOCK
    }
}

# ============ RISK PARAMETERS ============

RISK_LIMITS = {
    "max_total_capital_pct":    0.10,   # 10% of portfolio
    "max_per_market_pct":       0.02,   # 2% per market
    "max_daily_loss_pct":       0.03,   # 3% daily stop
    "max_correlation_cluster":  0.05,   # 5% per entity/event
    "max_crypto_adjacent":      0.15,   # 15% crypto-adjacent
    "max_political":            0.10,   # 10% political
    "min_orderbook_depth_mult":  5.0,   # 5x depth multiplier
    "max_spread_pct":            0.05,  # 5% max spread
    "min_sharpe":                0.5,   # 0.5 minimum Sharpe
    "auto_reject_resolution_h": 24,     # No trades < 24h to resolution
}

# ============ AUTO-EXECUTION THRESHOLDS ============

EXECUTION_THRESHOLDS = {
    "strong_execute":  6.0,   # Score >= 6 → auto-execute (was 7)
    "moderate_execute": 3.5,  # Score >= 3.5 → recommend to user (was 5)
    "weak_signal":      1.5,  # Score >= 1.5 → monitor only (was 3)
    "no_action":        0.0,  # Score < 1.5 → no action
}

# ============ CORRELATION CLUSTERS ============

CORRELATION_CLUSTERS = {
    "geopolitical_tail": ["xi", "china", "ceasefire", "zelenskyy", "netanyahu"],
    "us_politics_2028": ["vance", "newsom", "aoc", "demshouse"],
    "meme_absurd": ["jesus"],
}


class PerplexitySignal:
    """Parse Perplexity research output into structured signals."""
    
    def __init__(self, position_key: str, sentiment: str, conviction: str, 
                 rationale: str = "", contradicts_current: bool = False):
        self.position_key = position_key
        self.sentiment = sentiment      # "bullish", "bearish", "neutral"
        self.conviction = conviction    # "strong", "moderate", "weak"
        self.rationale = rationale
        self.contradicts_current = contradicts_current
    
    @classmethod
    def from_research_file(cls, filepath: str) -> Dict[str, 'PerplexitySignal']:
        """Load signals from a perplexity research markdown file."""
        signals = {}
        try:
            with open(filepath) as f:
                content = f.read()
            
            # Parse position sections
            sections = content.split("### ")
            for section in sections[1:]:  # Skip header
                lines = section.strip().split("\n")
                if not lines:
                    continue
                
                header = lines[0].strip()
                # Extract position key from header (e.g., "1. Jesus Christ..." → "jesus")
                position_key = header.split(". ")[1].split(" ")[0].lower() if ". " in header else header.split()[0].lower()
                
                # Parse sentiment and action
                body = "\n".join(lines[1:])
                sentiment = "neutral"
                conviction = "weak"
                contradicts = False
                
                if "SUPPORTED" in body or "✅" in body:
                    sentiment = "bullish"
                elif "CONTRADICTED" in body or "❌" in body:
                    sentiment = "bearish"
                    contradicts = True
                elif "PARTIAL CONTRADICTION" in body or "⚠️" in body:
                    sentiment = "bearish"
                    conviction = "moderate"
                    contradicts = True
                
                if "strong" in body.lower() or "high conviction" in body.lower():
                    conviction = "strong"
                elif "moderate" in body.lower() or "trim" in body.lower():
                    conviction = "moderate"
                
                rationale = body.strip()
                
                signals[position_key] = cls(
                    position_key, sentiment, conviction, rationale, contradicts
                )
        except Exception as e:
            print(f"Warning: Could not parse Perplexity file: {e}")
        
        return signals


class CompositeScore:
    """
    Master scoring engine — compiles all signals into one actionable score.
    """
    
    def __init__(self, position_key: str, position: dict):
        """
        position = {
            "name": str,
            "side": "YES" | "NO",
            "entry": float,
            "current": float,
            "size": float,       # USDC at risk
            "category": str,     # "geopolitical", "political", "meme"
            "condition_id": str,
            "slug": str,
        }
        """
        self.position_key = position_key
        self.position = position
        self.scores = {}       # Individual signal scores
        self.total_score = 0.0
        self.direction = "NEUTRAL"  # "LONG", "SHORT", "NEUTRAL"
        self.confidence = 0.0
        self.action = "HOLD"
        self.risk_pass = True
        self.risk_flags = []
        self.details = {}
    
    def add_technical_score(self, analysis: dict):
        """Score from technical indicators."""
        tech_score = 0.0
        current = self.position.get("current", 0)
        
        # RSI extreme
        rsi_val = analysis.get("rsi", 50)
        if rsi_val < 25:
            tech_score += WEIGHTS["technical"]["rsi_extreme"]  # Oversold → LONG
        elif rsi_val > 75:
            tech_score -= WEIGHTS["technical"]["rsi_extreme"]  # Overbought → SHORT
        elif rsi_val < 35:
            tech_score += WEIGHTS["technical"]["rsi_extreme"] * 0.5
        elif rsi_val > 65:
            tech_score -= WEIGHTS["technical"]["rsi_extreme"] * 0.5
        
        # EMA Cross
        ema_cross = analysis.get("ema_cross")
        if ema_cross == "BULLISH_CROSS":
            tech_score += WEIGHTS["technical"]["ema_cross"]
        elif ema_cross == "BEARISH_CROSS":
            tech_score -= WEIGHTS["technical"]["ema_cross"]
        
        # MACD Divergence
        macd_sig = analysis.get("macd")
        if macd_sig == "BULLISH_DIVERGENCE":
            tech_score += WEIGHTS["technical"]["macd_divergence"]
        elif macd_sig == "BEARISH_DIVERGENCE":
            tech_score -= WEIGHTS["technical"]["macd_divergence"]
        
        # Bollinger
        bb = analysis.get("bollinger")
        if bb == "OVERSOLD_BAND":
            tech_score += WEIGHTS["technical"]["bollinger_extreme"]
        elif bb == "OVERBOUGHT_BAND":
            tech_score -= WEIGHTS["technical"]["bollinger_extreme"]
        
        # Supertrend
        st = analysis.get("supertrend")
        if st == "BULLISH":
            tech_score += WEIGHTS["technical"]["supertrend"]
        elif st == "BEARISH":
            tech_score -= WEIGHTS["technical"]["supertrend"]
        
        # MFI extreme
        mfi_val = analysis.get("mfi", 50)
        if mfi_val < 20:
            tech_score += WEIGHTS["technical"]["mfi_extreme"]
        elif mfi_val > 80:
            tech_score -= WEIGHTS["technical"]["mfi_extreme"]
        
        # W/M Patterns
        if analysis.get("w_bottom"):
            tech_score += WEIGHTS["technical"]["w_bottom"]
        if analysis.get("m_top"):
            tech_score -= WEIGHTS["technical"]["m_top"]
        
        # Support/Resistance
        if analysis.get("support_touch"):
            tech_score += WEIGHTS["technical"]["support_touch"]
        if analysis.get("resistance_touch"):
            tech_score -= WEIGHTS["technical"]["resistance_touch"]
        
        self.scores["technical"] = tech_score
        self.details["technical"] = {
            "rsi": rsi_val,
            "ema_cross": ema_cross,
            "macd": macd_sig,
            "bollinger": bb,
            "supertrend": st,
            "mfi": mfi_val,
            "w_bottom": analysis.get("w_bottom"),
            "m_top": analysis.get("m_top"),
        }
        return tech_score
    
    def add_cypher_score(self, cypher_1h: dict, cypher_4h: dict):
        """Score from Market Cypher green/red dot signals."""
        cypher_score = 0.0
        
        if cypher_1h:
            if cypher_1h.get("green_dot"):
                cypher_score += WEIGHTS["cypher"]["green_dot_1h"]
            if cypher_1h.get("red_dot"):
                cypher_score -= WEIGHTS["cypher"]["red_dot_1h"]
        
        if cypher_4h:
            if cypher_4h.get("green_dot"):
                cypher_score += WEIGHTS["cypher"]["green_dot_4h"]
            if cypher_4h.get("red_dot"):
                cypher_score -= WEIGHTS["cypher"]["red_dot_4h"]
        
        self.scores["cypher"] = cypher_score
        self.details["cypher"] = {
            "1h": "🟢" if cypher_1h and cypher_1h.get("green_dot") else "🔴" if cypher_1h and cypher_1h.get("red_dot") else "⚪",
            "4h": "🟢" if cypher_4h and cypher_4h.get("green_dot") else "🔴" if cypher_4h and cypher_4h.get("red_dot") else "⚪",
        }
        return cypher_score
    
    def add_perplexity_score(self, perplexity_signal: PerplexitySignal = None):
        """Score from Perplexity AI research.
        
        Scoring logic:
        - Perplexity sentiment vs our position determines direction
        - bearish + our position is YES = -2.0 (research says SELL our YES)
        - bullish + our position is NO = -2.0 (research says SELL our NO)
        - bearish + our position is NO = +2.0 (research says HOLD our NO / add to NO)
        - bullish + our position is YES = +2.0 (research says HOLD our YES / add to YES)
        - neutral = 0.0
        """
        pp_score = 0.0
        
        if perplexity_signal:
            current_side = self.position.get("side", "YES")
            
            # Base score from sentiment + conviction
            # WEIGHTS keys are: "strong_bullish", "moderate_bullish", "strong_bearish", "moderate_bearish"
            key = f"{perplexity_signal.conviction}_{perplexity_signal.sentiment}"
            raw_score = WEIGHTS["perplexity"].get(key, 0.0)
            
            # Determine alignment
            if perplexity_signal.sentiment == "bullish":
                if current_side == "YES":
                    pp_score = abs(raw_score)   # Research supports our YES
                else:  # NO position
                    pp_score = -abs(raw_score)  # Research contradicts our NO
            elif perplexity_signal.sentiment == "bearish":
                if current_side == "NO":
                    pp_score = abs(raw_score)   # Research supports our NO
                else:  # YES position
                    pp_score = -abs(raw_score)  # Research contradicts our YES
            else:
                pp_score = 0.0
        
        self.scores["perplexity"] = pp_score
        self.details["perplexity"] = {
            "sentiment": perplexity_signal.sentiment if perplexity_signal else "none",
            "conviction": perplexity_signal.conviction if perplexity_signal else "none",
            "aligned_with_position": pp_score > 0,
        }
        return pp_score
    
    def add_microstructure_score(self, spread_pct: float = 0.02, 
                                  depth_ratio: float = 10.0,
                                  volume_trend: str = "stable"):
        """Score from market microstructure."""
        micro_score = 0.0
        
        # Spread
        if spread_pct < 0.02:
            micro_score += WEIGHTS["microstructure"]["spread_narrow"]
        elif spread_pct > 0.05:
            micro_score += WEIGHTS["microstructure"]["spread_wide"]
        
        # Depth
        if depth_ratio >= RISK_LIMITS["min_orderbook_depth_mult"]:
            micro_score += WEIGHTS["microstructure"]["depth_adequate"]
        
        # Volume trend
        if volume_trend == "rising":
            micro_score += WEIGHTS["microstructure"]["volume_rising"]
        
        self.scores["microstructure"] = micro_score
        self.details["microstructure"] = {
            "spread_pct": spread_pct,
            "depth_ratio": depth_ratio,
            "volume_trend": volume_trend,
        }
        return micro_score
    
    def check_risk(self, portfolio_positions: dict, daily_pnl: float = 0, 
                    portfolio_size: float = 10000):
        """Check risk limits and apply penalties.
        
        Risk scores are ASYMMETRIC:
        - CLOSING/reducing positions gets LOWER risk penalty (closing is risk-reducing)
        - OPENING/adding positions gets FULL risk penalty (adding increases risk)
        - Hard blocks (daily stop) still block everything
        """
        risk_score = 0.0
        self.risk_pass = True
        self.risk_flags = []
        
        # Determine if this signal would REDUCE or INCREASE risk
        # LONG direction on YES position = adding (increase risk)
        # SHORT direction on YES position = closing (reduce risk)
        current_side = self.position.get("side", "YES")
        is_closing = False
        if self.total_score < 0 and current_side == "YES":
            is_closing = True  # Short signal on YES = close
        elif self.total_score > 0 and current_side == "NO":
            is_closing = True  # Long signal on NO = close
        
        # Total capital at risk
        total_at_risk = sum(p.get("size", 0) for p in portfolio_positions.values())
        total_pct = total_at_risk / portfolio_size if portfolio_size > 0 else 0
        
        if total_pct > RISK_LIMITS["max_total_capital_pct"]:
            if is_closing:
                # Reducing position when over limit = GOOD, light penalty only
                risk_score += WEIGHTS["risk"]["position_over_limit"] * 0.2
                self.risk_flags.append(f"OVER_TOTAL_CAP:{total_pct:.1%}>10%(closing)")
            else:
                # Adding when over limit = BAD, full penalty + block
                risk_score += WEIGHTS["risk"]["position_over_limit"]
                self.risk_flags.append(f"OVER_TOTAL_CAP: {total_pct:.1%} > {RISK_LIMITS['max_total_capital_pct']:.0%}")
                self.risk_pass = False
        
        # Per-market limit
        market_pct = self.position.get("size", 0) / portfolio_size
        if market_pct > RISK_LIMITS["max_per_market_pct"]:
            risk_score += WEIGHTS["risk"]["position_over_limit"] * 0.5
            self.risk_flags.append(f"OVER_MARKET_CAP: {market_pct:.1%} > {RISK_LIMITS['max_per_market_pct']:.0%}")
        
        # Correlation clusters
        for cluster_name, cluster_keys in CORRELATION_CLUSTERS.items():
            if self.position_key in cluster_keys:
                cluster_risk = sum(
                    portfolio_positions[k].get("size", 0) 
                    for k in cluster_keys if k in portfolio_positions
                )
                cluster_pct = cluster_risk / portfolio_size
                if cluster_pct > RISK_LIMITS["max_correlation_cluster"]:
                    risk_score += WEIGHTS["risk"]["correlation_breach"]
                    self.risk_flags.append(f"CORRELATION_{cluster_name}: {cluster_pct:.1%}")
        
        # Daily stop
        daily_loss_pct = abs(daily_pnl) / portfolio_size if daily_pnl < 0 else 0
        if daily_loss_pct > RISK_LIMITS["max_daily_loss_pct"]:
            risk_score += WEIGHTS["risk"]["daily_stop_breach"]
            self.risk_flags.append(f"DAILY_STOP: -{daily_loss_pct:.1%} > -{RISK_LIMITS['max_daily_loss_pct']:.0%}")
            self.risk_pass = False
        
        self.scores["risk"] = risk_score
        self.details["risk"] = {
            "total_at_risk_pct": total_pct,
            "market_pct": market_pct,
            "daily_loss_pct": daily_loss_pct,
            "risk_pass": self.risk_pass,
            "flags": self.risk_flags,
        }
        return risk_score
    
    def compute(self) -> dict:
        """Compute final composite score and determine action."""
        self.total_score = sum(self.scores.values())
        
        # Determine direction from total score
        # Lowered thresholds to make signals more responsive
        if self.total_score >= 1.5:
            self.direction = "LONG"
        elif self.total_score <= -1.5:
            self.direction = "SHORT"
        else:
            self.direction = "NEUTRAL"
        
        # Confidence = |score| / max_possible (10)
        self.confidence = min(abs(self.total_score) / 10.0, 1.0)
        
        # Determine action based on score + risk
        abs_score = abs(self.total_score)
        
        if not self.risk_pass:
            self.action = "🚫 BLOCKED — Risk limit breached"
        elif abs_score >= EXECUTION_THRESHOLDS["strong_execute"]:
            self.action = f"⚡ AUTO-EXECUTE {self.direction}"
        elif abs_score >= EXECUTION_THRESHOLDS["moderate_execute"]:
            self.action = f"📊 RECOMMEND {self.direction}"
        elif abs_score >= EXECUTION_THRESHOLDS["weak_signal"]:
            self.action = f"👀 MONITOR — Weak {self.direction} signal"
        else:
            self.action = "⏸️ HOLD — No actionable signal"
        
        # Check if signal contradicts current position
        current_side = self.position.get("side", "YES")
        contradicts = False
        if self.direction == "LONG" and current_side == "NO":
            contradicts = True
        elif self.direction == "SHORT" and current_side == "YES":
            contradicts = True
        
        return {
            "position_key": self.position_key,
            "position_name": self.position.get("name", ""),
            "current_side": current_side,
            "total_score": self.total_score,
            "direction": self.direction,
            "confidence": self.confidence,
            "action": self.action,
            "risk_pass": self.risk_pass,
            "risk_flags": self.risk_flags,
            "contradicts_position": contradicts,
            "scores": self.scores,
            "details": self.details,
        }


class PortfolioScorer:
    """Score entire portfolio and generate execution queue."""
    
    def __init__(self, portfolio: dict, portfolio_size: float = 10000):
        self.portfolio = portfolio
        self.portfolio_size = portfolio_size
        self.results = []
    
    def score_all(self, price_data: dict, perplexity_signals: dict = None) -> List[dict]:
        """
        price_data = {key: {"prices": [...], "volumes": [...]}}
        perplexity_signals = {key: PerplexitySignal}
        """
        perplexity_signals = perplexity_signals or {}
        self.results = []
        
        daily_pnl = sum(
            (p.get("current", 0) - p.get("entry", 0)) * p.get("size", 0) 
            if p.get("side") == "YES" 
            else ((1 - p.get("current", 0)) - (1 - p.get("entry", 0))) * p.get("size", 0)
            for p in self.portfolio.values()
        )
        
        for key, pos in self.portfolio.items():
            scorer = CompositeScore(key, pos)
            
            # Technical analysis
            if key in price_data:
                pd = price_data[key]
                prices = pd.get("prices", [])
                volumes = pd.get("volumes", [])
                
                if len(prices) >= 50:
                    analysis = TechnicalSignal(key, prices, volumes).analyze()
                    scorer.add_technical_score(analysis)
                    
                    # Cypher signals
                    cypher_1h = market_cypher_signal(prices, volumes, "1h")
                    prices_4h = prices[::4]
                    volumes_4h = [sum(volumes[i:i+4]) for i in range(0, len(volumes), 4)]
                    cypher_4h = market_cypher_signal(prices_4h, volumes_4h, "4h")
                    scorer.add_cypher_score(cypher_1h, cypher_4h)
            
            # Perplexity signal
            pp_signal = perplexity_signals.get(key)
            scorer.add_perplexity_score(pp_signal)
            
            # Microstructure (defaults)
            scorer.add_microstructure_score(
                spread_pct=0.02,
                depth_ratio=10.0,
                volume_trend="stable"
            )
            
            # Risk check
            scorer.check_risk(self.portfolio, daily_pnl, self.portfolio_size)
            
            result = scorer.compute()
            self.results.append(result)
        
        # Sort by absolute score (strongest signals first)
        self.results.sort(key=lambda r: abs(r["total_score"]), reverse=True)
        return self.results
    
    def execution_queue(self) -> List[dict]:
        """Return only positions that need action, sorted by priority."""
        return [
            r for r in self.results 
            if abs(r["total_score"]) >= EXECUTION_THRESHOLDS["weak_signal"] 
            or not r["risk_pass"]
        ]
    
    def summary_table(self) -> str:
        """Generate formatted summary table."""
        lines = []
        lines.append("=" * 120)
        lines.append("COMPOSITE SCORING ENGINE — PORTFOLIO ANALYSIS")
        lines.append("=" * 120)
        lines.append(f"{'#':<3} {'Market':<35} {'Side':<5} {'Tech':<6} {'Cyph':<6} {'Pplx':<6} {'Micro':<6} {'Risk':<6} {'TOTAL':<7} {'Dir':<7} {'Action'}")
        lines.append("-" * 120)
        
        for i, r in enumerate(self.results, 1):
            scores = r.get("scores", {})
            tech = scores.get("technical", 0)
            cyph = scores.get("cypher", 0)
            pplx = scores.get("perplexity", 0)
            micro = scores.get("microstructure", 0)
            risk = scores.get("risk", 0)
            total = r.get("total_score", 0)
            direction = r.get("direction", "NEUTRAL")
            action = r.get("action", "HOLD")
            
            lines.append(
                f"{i:<3} {r['position_name'][:35]:<35} {r['current_side']:<5} "
                f"{tech:+5.1f}  {cyph:+5.1f}  {pplx:+5.1f}  {micro:+5.1f}  {risk:+5.1f}  "
                f"{total:+6.1f}  {direction:<7} {action}"
            )
        
        lines.append("=" * 120)
        lines.append("")
        lines.append("THRESHOLDS:")
        lines.append(f"  ⚡ Auto-execute: |score| >= {EXECUTION_THRESHOLDS['strong_execute']}")
        lines.append(f"  📊 Recommend:    |score| >= {EXECUTION_THRESHOLDS['moderate_execute']}")
        lines.append(f"  👀 Monitor:      |score| >= {EXECUTION_THRESHOLDS['weak_signal']}")
        lines.append("")
        
        return "\n".join(lines)


# ============ BACKTEST VALIDATION ============

def backtest_scoring_engine(portfolio: dict, historical_data: dict, 
                             perplexity_data: dict = None) -> dict:
    """
    Validate scoring engine against historical data.
    Simulates what would have happened if we followed the signals.
    """
    from technicals import generate_binary_price_path
    import random
    
    results = {
        "total_trades": 0,
        "auto_executed": 0,
        "recommended": 0,
        "held": 0,
        "blocked": 0,
        "correct_direction": 0,
        "wrong_direction": 0,
        "pnl_if_followed": 0,
        "pnl_if_held": 0,
    }
    
    perplexity_data = perplexity_data or {}
    
    for key, pos in portfolio.items():
        if key not in historical_data:
            continue
        
        prices = historical_data[key]
        volumes = [random.uniform(50000, 150000) for _ in prices]
        
        # Score at each time step
        for t in range(50, len(prices)):
            window_prices = prices[:t+1]
            window_volumes = volumes[:t+1]
            
            analysis = TechnicalSignal(key, window_prices, window_volumes).analyze()
            cypher_1h = market_cypher_signal(window_prices, window_volumes, "1h")
            prices_4h = window_prices[::4]
            volumes_4h = [sum(window_volumes[i:i+4]) for i in range(0, len(window_volumes), 4)]
            cypher_4h = market_cypher_signal(prices_4h, volumes_4h, "4h")
            
            scorer = CompositeScore(key, pos)
            scorer.add_technical_score(analysis)
            scorer.add_cypher_score(cypher_1h, cypher_4h)
            scorer.add_perplexity_score(perplexity_data.get(key))
            scorer.add_microstructure_score(0.02, 10.0, "stable")
            scorer.check_risk(portfolio, 0, 10000)
            
            result = scorer.compute()
            
            results["total_trades"] += 1
            
            abs_score = abs(result["total_score"])
            
            if not result["risk_pass"]:
                results["blocked"] += 1
            elif abs_score >= EXECUTION_THRESHOLDS["strong_execute"]:
                results["auto_executed"] += 1
                # Check if direction was correct (did price move that way?)
                if t + 10 < len(prices):
                    future_move = prices[t+10] - prices[t]
                    if (result["direction"] == "LONG" and future_move > 0) or \
                       (result["direction"] == "SHORT" and future_move < 0):
                        results["correct_direction"] += 1
                    else:
                        results["wrong_direction"] += 1
            elif abs_score >= EXECUTION_THRESHOLDS["moderate_execute"]:
                results["recommended"] += 1
            else:
                results["held"] += 1
    
    # Accuracy
    total_signaled = results["correct_direction"] + results["wrong_direction"]
    accuracy = results["correct_direction"] / total_signaled if total_signaled > 0 else 0
    results["signal_accuracy"] = accuracy
    
    return results


if __name__ == "__main__":
    print("Composite Scoring Engine v1.0 loaded.")
    print("Use: PortfolioScorer(portfolio).score_all(price_data, perplexity_signals)")