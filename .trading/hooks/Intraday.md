> Objective: Intraday re-scan, execute opportunities, and adjust orders.

## Cycle
Every K minutes (default: 300s / 5min):

1. **Call commands/scan-markets** → aggregate candidate trades from all skills/*

2. **For each candidate, run risk-manager vetting:**
   - Check against RISK.md constraints
   - Check correlation limits
   - Verify orderbook depth
   - Compute position size

3. **Approved trades → execution-engine:**
   - Convert TradeIntents to CLOB orders
   - Choose maker vs taker
   - Split large orders into tranches
   - Submit via CLOB client

4. **Monitor open positions:**
   - PnL tracking
   - Position health vs risk limits
   - Cancel/replace stale orders

## TradeIntent Schema
```json
{
  "market_id": "slug",
  "condition_id": "0x...",
  "token_id": "0x...",
  "side": "YES" | "NO",
  "strategy": "divergence" | "mm-bands" | "tail-end" | "copy-trader",
  "type": "maker" | "taker",
  "confidence": 0.0-1.0,
  "edge_bps": float,
  "target_size_usdc": float,
  "max_price_impact_bps": float,
  "time_in_force": "GTC" | "IOC" | "FOK"
}
```

## Emergency Triggers
- Daily loss > Z% → STOP ALL, close positions
- Spread > 10% on active position → cancel orders, reassess
- Oracle dispute detected → freeze affected markets

## Output
Log: trades_executed, orders_cancelled, positions_updated, pnl_realized, pnl_unrealized
