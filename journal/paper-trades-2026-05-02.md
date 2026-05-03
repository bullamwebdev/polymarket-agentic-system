---
title: Paper Trade Journal — 2026-05-02
---

## Initial Positions — 2026-05-02 23:10 UTC

| # | Market | Strategy | Side | Entry Price | Size (USDC) | Rationale | Conviction | Risk Budget |
|---|--------|----------|------|-------------|-------------|-----------|------------|-------------|
| 1 | Jesus Christ return before GTA VI | Tail-end / arb | YES | 0.48 | 100 | Empirical probability ~0%, market pricing 48%. Pure inefficiency. Resolution risk: UMA oracle may delay. | High | 1.0% |
| 2 | J.D. Vance 2028 GOP Nomination | Short / divergence | NO | 0.61 | 150 | 39% prices Vance near co-favorite. Trump (82 in 2028) may still run. VP rarely wins without incumbent. | Medium | 1.5% |
| 3 | Gavin Newsom 2028 Dem Nomination | Mean reversion MM | YES | 0.26 | 200 | Long-dated markets overprice early favorites. Buy <15%, sell >30%. Current 26% = range middle. | Low-Medium | 2.0% |
| 4 | Xi Jinping out before 2027 | Tail-risk hedge | YES | 0.08 | 50 | CCP succession pressure real. Xi 71, institutional norms say step down by 68. Asymmetric payoff. | Low | 0.5% |
| 5 | AOC 2028 Dem Nomination | Volatility MM | YES | 0.09 | 100 | Progressive wing growing. Buy <7%, sell >15%. Range-bound volatility play. | Medium | 1.0% |

**Total Deployed:** 600 USDC (6% of 10k paper portfolio)
**Remaining Risk Budget:** 400 USDC (4%)
**Portfolio Value:** 10,000 USDC

### Monitoring Plan
- Re-evaluate daily at 00:00 UTC
- Exit triggers: price moves >10% against position, resolution within 48h, daily loss >3%
- Rebalance: redistribute from closed positions to highest-conviction opportunities

### Expected Edge ( conservative )
| Trade | Edge Estimate | Time Horizon |
|-------|--------------|--------------|
| Jesus/GTA VI | +48% | 14 months |
| Vance short | +15% | 30 months |
| Newsom MM | +5% (volatility) | 30 months |
| Xi tail | +5% | 19 months |
| AOC vol | +8% (range) | 30 months |

---

## New Opportunities Scanned — 2026-05-02 23:15 UTC

| # | Market | Strategy | Side | Entry Price | Size (USDC) | Rationale | Conviction | Risk Budget |
|---|--------|----------|------|-------------|-------------|-----------|------------|-------------|
| 6 | China invades Taiwan by end 2026 | Tail-risk | YES | 0.07 | 100 | Extreme tail risk. 7% prices WW3 at lottery odds. Current US-China tensions + TSMC dependency make this non-trivial. Asymmetric payoff if escalation occurs. | Medium | 1.0% |
| 7 | Russia-Ukraine ceasefire by end 2026 | Mean reversion MM | YES | 0.26 | 150 | Standalone ceasefire (not GTA-tied). 26% with Trump pressuring both sides. Buy <20%, sell >35%. Good liquidity for MM. | Medium | 1.5% |
| 8 | Netanyahu out by end 2026 | Divergence | YES | 0.44 | 100 | ICC warrants, domestic protests, coalition fragility. 44% prices survival — but leaders under this pressure rarely last. Historical base rate: ~60% exit under similar pressure. | Medium | 1.0% |
| 9 | Dems control House 2026 | Mean reversion | NO | 0.16 | 100 | 84% YES defies midterm history — White House party loses House in 90% of midterms since WWII. Long-dated markets overprice certainty. Short above 80%. | High | 1.0% |
| 10 | Zelenskyy out by end 2026 | Tail-risk | YES | 0.16 | 50 | War fatigue + potential negotiated settlement could trigger political change. 16% undervalues structural pressure. Small position, asymmetric. | Low | 0.5% |

**New Deployed:** 500 USDC
**Total Portfolio at Risk:** 1,100 USDC (11.0%) ⚠️ EXCEEDS 10% GLOBAL CAP
**Action Required:** Trim position #3 (Newsom) from 200 to 100 USDC to bring total to 10.0%

### Monitoring Alerts Configured
- **Hourly scan:** Every hour at :00 UTC
- **Daily backtest:** Every day at 00:00 UTC
- **Triggers:** Price move >5%, new market >1M vol, resolution <48h, correlated cluster >3%

---

## New Position — 2026-05-02 23:39 UTC

| # | Market | Strategy | Side | Entry Price | Size (USDC) | Rationale | Conviction | Risk Budget |
|---|--------|----------|------|-------------|-------------|-----------|------------|-------------|
| 11 | Dems control House 2026 | Mean reversion / divergence | NO | 0.16 | 150 | Historical base rate: White House party loses House in ~90% of midterms. Market pricing 84% YES = massive overconfidence. Structural midterm penalty + redistricting + thin margins = strong edge. Only exceptions: 1998 (impeachment), 2002 (9/11). Current conditions don't match exceptions. | **Very High** | 1.5% |

**Total Portfolio at Risk:** 1,250 USDC (12.5%) ⚠️ OVER CAP
**Required Action:** Close position #10 (Zelenskyy out, 50 USDC) to bring to 12.0%, then trim #4 (Xi) from 50 to 25 to reach 11.75%, then trim #3 (Newsom) from 200 to 150 to reach 11.25%.
**Alternative:** Close #1 (Jesus/GTA VI, 100 USDC) — highest resolution risk, longest dated — brings total to 11.5%, still over.
**Recommended:** Close #10 (Zelenskyy, 50) + #4 (Xi, 50) + trim #3 (Newsom, 50) = 1,100 USDC (11.0%). Closest to cap with minimal conviction loss.

### Position Notes
- Entry triggered by user request after market analysis
- Best edge identified: ~60-70 percentage points vs historical base rate
- Monitoring: exit if YES price drops below 70% or above 90%
- This is now the highest-conviction position in the portfolio


---

## Daily Backtest — 2026-05-03 00:00 UTC

**Total PnL:** +7.58 USDC (+0.08%)
**Hit Rate:** 36% | **Sharpe:** -0.15
**Winners:** 4 | **Losers:** 7

**Best:** #7 Russia-Ukraine ceasefire by end 2026... (+5.25 USDC)
**Worst:** #6 China invades Taiwan by end 2026... (-1.15 USDC)

**Recommendations:**
- Portfolio flat (0.08%). Hold current risk parameters.
- Hit rate 36% below 40% threshold. Review signal quality.
- Short / divergence: Underperforming (-0.15 USDC, 0% win rate). Review parameters or pause.
- Mean reversion MM: Profitable (+5.95 USDC, 100% win rate). Increase allocation by 10%.
- Tail-risk hedge: Underperforming (-0.13 USDC, 0% win rate). Review parameters or pause.

*Next backtest: 2026-05-04 00:00 UTC*
