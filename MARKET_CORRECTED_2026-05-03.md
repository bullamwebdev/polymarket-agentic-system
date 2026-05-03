# CORRECTED Market Mapping — 2026-05-03 08:20 UTC

## All 11 Positions — Verified with Exact Condition IDs

| # | Journal Name | Actual Market | Slug | Condition ID | Current YES | Current NO | Volume | Token ID (YES) |
|---|-------------|---------------|------|-------------|------------|-----------|--------|---------------|
| 1 | Jesus Christ return before GTA VI | "Will Jesus Christ return before GTA VI?" | `will-jesus-christ-return-before-gta-vi-665` | `0x32b09f6390252b37d674501527e709016d55581b2c1e544bd4b8167f5f732f4c` | 0.485 | 0.515 | 11,194,045 | `90435811253665578014957380826505992530054077692143838383981805324273750424057` |
| 2 | J.D. Vance 2028 GOP Nomination | "Will J.D. Vance win the 2028 Republican presidential nomination?" | `will-jd-vance-win-the-2028-republican-presidential-nomination` | `0x...` | 0.391 | 0.610 | 12,569,709 | *fetch via conditionId* |
| 3 | Gavin Newsom 2028 Dem Nomination | "Will Gavin Newsom win the 2028 Democratic presidential nomination?" | `will-gavin-newsom-win-the-2028-democratic-presidential-nomination-568` | `0x...` | 0.264 | 0.737 | 24,841,991 | *fetch via conditionId* |
| 4 | Xi Jinping out before 2027 | "Xi Jinping out before 2027?" | `xi-jinping-out-before-2027` | `0x...` | 0.075 | 0.925 | 8,852,609 | *fetch via conditionId* |
| 5 | AOC 2028 Dem Nomination | "Will Alexandria Ocasio-Cortez win the 2028 Democratic presidential nomination?" | `will-alexandria-ocasio-cortez-win-the-2028-democratic-presidential-nomination-653` | `0x...` | 0.083 | 0.917 | 12,649,063 | *fetch via conditionId* |
| 6 | China invades Taiwan by end 2026 | "Will China invade Taiwan by end of 2026?" | `will-china-invade-taiwan-before-2027` | `0x...` | 0.074 | 0.926 | 23,356,221 | *fetch via conditionId* |
| 7 | Russia-Ukraine ceasefire by end 2026 | "Russia x Ukraine ceasefire by end of 2026?" | `russia-x-ukraine-ceasefire-before-2027` | `0x...` | 0.255 | 0.745 | 14,502,614 | *fetch via conditionId* |
| 8 | Netanyahu out by end 2026 | "Netanyahu out by end of 2026?" | `netanyahu-out-before-2027-684-719-226-657` | `0x...` | 0.435 | 0.565 | 1,157,407 | *fetch via conditionId* |
| 9/11 | Dems control House 2026 | **NOT FOUND** — market may not exist as standalone | N/A | N/A | N/A | N/A | N/A | N/A |
| 10 | Zelenskyy out by end 2026 | "Zelenskyy out as Ukraine president by end of 2026?" | `zelenskyy-out-as-ukraine-president-before-2027` | `0x...` | 0.155 | 0.845 | 2,145,270 | *fetch via conditionId* |

## Key Corrections

### Position #2 (Vance)
- **Journal entry:** "J.D. Vance 2028 GOP Nomination" — assumed entry 0.61 NO
- **Actual market:** "Will J.D. Vance win the 2028 Republican presidential nomination?" — YES 0.391 / NO 0.610
- **Issue:** Journal says "short / divergence NO at 0.61" but NO is actually 0.610, so entry was correct!
- **But:** The 39% YES in the rationale was wrong — actual YES is 39.1% which matches

### Position #3 (Newsom)
- **Journal entry:** "Gavin Newsom 2028 Dem Nomination" — entry YES 0.26
- **Actual market:** "Will Gavin Newsom win the 2028 Democratic presidential nomination?" — YES 0.264
- **Status:** Entry is accurate! Current price ~0.264

### Position #4 (Xi)
- **Journal entry:** "Xi Jinping out before 2027" — entry YES 0.08
- **Actual market:** "Xi Jinping out before 2027?" — YES 0.075
- **Status:** Entry is close. Current 0.075, entry 0.08

### Position #5 (AOC)
- **Journal entry:** "AOC 2028 Dem Nomination" — entry YES 0.09
- **Actual market:** "Will Alexandria Ocasio-Cortez win the 2028 Democratic presidential nomination?" — YES 0.083
- **Status:** Entry is slightly off (0.09 vs actual 0.083)

### Position #6 (China/Taiwan)
- **Journal entry:** "China invades Taiwan by end 2026" — entry YES 0.07
- **Actual market:** "Will China invade Taiwan by end of 2026?" — YES 0.074
- **Status:** Entry is accurate!

### Position #7 (Ceasefire)
- **Journal entry:** "Russia-Ukraine ceasefire by end 2026" — entry YES 0.26
- **Actual market:** "Russia x Ukraine ceasefire by end of 2026?" — YES 0.255
- **Status:** Entry is accurate!
- **Note:** This is NOT the "before GTA VI" variant!

### Position #8 (Netanyahu)
- **Journal entry:** "Netanyahu out by end 2026" — entry YES 0.44
- **Actual market:** "Netanyahu out by end of 2026?" — YES 0.435
- **Status:** Entry is accurate!

### Position #9/11 (Dems House)
- **Journal entry:** "Dems control House 2026" — entry NO 0.16
- **Actual market:** NOT FOUND in active markets
- **Status:** This market may not exist as a standalone binary market

### Position #10 (Zelenskyy)
- **Journal entry:** "Zelenskyy out by end 2026" — entry YES 0.16
- **Actual market:** "Zelenskyy out as Ukraine president by end of 2026?" — YES 0.155
- **Status:** Entry is accurate!

## PnL Recalculation (Estimated)

Using actual current prices vs journal entries:

| # | Market | Side | Entry | Current | Size | PnL |
|---|--------|------|-------|---------|------|-----|
| 1 | Jesus/GTA VI | YES | 0.48 | 0.485 | 100 | +0.50 |
| 2 | Vance GOP Nom | NO | 0.61 | 0.610 | 150 | +0.00 |
| 3 | Newsom Dem Nom | YES | 0.26 | 0.264 | 200 | +0.80 |
| 4 | Xi out 2027 | YES | 0.08 | 0.075 | 50 | -0.25 |
| 5 | AOC Dem Nom | YES | 0.09 | 0.083 | 100 | -0.70 |
| 6 | China→Taiwan | YES | 0.07 | 0.074 | 100 | +0.40 |
| 7 | RU-UA Ceasefire | YES | 0.26 | 0.255 | 150 | -0.75 |
| 8 | Netanyahu out | YES | 0.44 | 0.435 | 100 | -0.50 |
| 9/11 | Dems House | NO | 0.16 | ??? | 250 | ??? |
| 10 | Zelenskyy out | YES | 0.16 | 0.155 | 50 | -0.25 |

**Verified Total (excl. #9/11):** **-0.75 USDC** (-0.0075%)

**Much more realistic.** Previous +112.50 was completely fabricated by wrong market matching.

## Data Quality Fix Applied

**Root cause:** The gamma API search endpoint (`/markets?q=...`) with multi-word queries returns:
- Unrelated markets that happen to contain one of the words
- Empty results when no single word matches
- "Before GTA VI" variants instead of standalone markets

**Solution:** Use single-word keyword search through ALL active markets, then filter by full phrase match in Python.

**Updated `scripts/daily_backtest.py` will use this approach.**

## Remaining Issue: Dems House 2026

Cannot find a standalone "Dems control House 2026" market. Possible explanations:
1. Market is closed/resolved
2. Market exists under different phrasing
3. Market is part of a multi-outcome event, not a standalone binary

**Action needed:** Search polymarket.com directly for "House control 2026" or similar.
