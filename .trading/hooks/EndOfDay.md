> Objective: Freeze, audit, and learn.

## Steps

1. **Close overnight-violating positions:**
   - Any position in market resolving within 24h → close
   - Any position > per-market cap after revaluation → trim
   - Any correlated group > group cap → trim largest

2. **Ask journal-analyzer to summarize:**
   - PnL by strategy, by market, by time bucket
   - Hit rate, average edge vs mid, slippage
   - Sharpe ratio per strategy
   - Edge decay or improvement over session

3. **Ask oracle-auditor to review:**
   - Newly resolved markets for anomalies
   - UMA disputes, unusual delays
   - Flag markets with suspicious resolution patterns

4. **Update strategy weights:**
   - Increase allocation to top-performing strategies
   - Reduce or pause underperforming strategies
   - Document reasoning in journal

## Output
Emit EOD report:
```json
{
  "session_id": "YYYY-MM-DD",
  "total_pnl": float,
  "realized_pnl": float,
  "unrealized_pnl": float,
  "trades_count": int,
  "strategies_performance": [
    {"strategy": "divergence", "pnl": float, "sharpe": float, "hit_rate": float}
  ],
  "markets_closed": ["slug1", "slug2"],
  "oracle_flags": ["market_id: reason"],
  "risk_budget_remaining_pct": float,
  "recommendations": ["..."]
}
```
