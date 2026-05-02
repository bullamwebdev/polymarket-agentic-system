> Objective: Build today's Polymarket watchlist and allocate risk budgets per bucket.

## Steps

1. **Ask market-researcher for:**
   - Top N markets by 24h volume and open interest
   - Markets with large overnight price moves or spread anomalies
   - Event calendar: macro releases, elections, deadlines, etc.

2. **Ask chief-strategist to map these markets to skills:**
   - divergence, mm-bands, mm-amm, tail-end, copy-trader
   - Assign confidence scores based on historical performance

3. **Ask risk-manager to assign per-market risk caps:**
   - Per-market notional caps
   - Strategy-level notional caps
   - Correlation-adjusted group caps

4. **Emit structured JSON plan:**
```json
{
  "session_id": "YYYY-MM-DD",
  "markets": [
    {
      "market_id": "slug",
      "condition_id": "0x...",
      "question": "...",
      "current_yes_price": 0.55,
      "24h_volume": 150000,
      "open_interest": 500000,
      "assigned_strategies": ["divergence", "mm-bands"],
      "risk_cap_usdc": 2000,
      "confidence": 0.7
    }
  ],
  "risk_budgets": {
    "total_session_cap": 10000,
    "per_market_max": 2000,
    "per_strategy_max": {"divergence": 5000, "mm-bands": 3000}
  },
  "monitoring_frequency_seconds": 300
}
```

## Output
Emit the JSON plan and a human-readable summary with top 5 opportunities.
