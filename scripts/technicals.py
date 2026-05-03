#!/usr/bin/env python3
"""
Polymarket Technical Analysis Engine
Binary probability markets — RSI, EMA, MACD, Bollinger, Supertrend, Momentum Wave
"""

import json, sqlite3, math, os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import urllib.request

# ============ DATABASE ============
DB_PATH = os.path.expanduser("~/.openclaw/workspace/polymarket-agentic-system/data/price_history.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY,
            condition_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            yes_price REAL NOT NULL,
            no_price REAL NOT NULL,
            volume REAL DEFAULT 0,
            UNIQUE(condition_id, timestamp)
        )
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_prices_lookup 
        ON prices(condition_id, timestamp DESC)
    ''')
    conn.commit()
    conn.close()

def record_price(condition_id: str, yes_price: float, no_price: float, volume: float = 0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = int(datetime.utcnow().timestamp())
    c.execute('''
        INSERT OR REPLACE INTO prices (condition_id, timestamp, yes_price, no_price, volume)
        VALUES (?, ?, ?, ?, ?)
    ''', (condition_id, ts, yes_price, no_price, volume))
    conn.commit()
    conn.close()

def get_price_history(condition_id: str, hours: int = 168) -> List[Tuple[int, float, float, float]]:
    """Returns [(timestamp, yes_price, no_price, volume), ...] ordered by time ASC"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    c.execute('''
        SELECT timestamp, yes_price, no_price, volume 
        FROM prices 
        WHERE condition_id = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    ''', (condition_id, cutoff))
    rows = c.fetchall()
    conn.close()
    return rows

# ============ INDICATORS ============

def ema(prices: List[float], period: int) -> List[float]:
    """Exponential Moving Average"""
    if len(prices) < period:
        return []
    multiplier = 2 / (period + 1)
    ema_values = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values

def rsi(prices: List[float], period: int = 14) -> List[float]:
    """Relative Strength Index — adapted for 0-1 probability range"""
    if len(prices) < period + 1:
        return []
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_values = []
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))
    return rsi_values

def macd(prices: List[float], fast=12, slow=26, signal=9) -> Tuple[List[float], List[float], List[float]]:
    """MACD line, signal line, histogram"""
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    
    # Align lengths
    offset = slow - fast
    macd_line = [f - s for f, s in zip(ema_fast[offset:], ema_slow)]
    signal_line = ema(macd_line, signal)
    histogram = [m - s for m, s in zip(macd_line[len(macd_line)-len(signal_line):], signal_line)]
    
    # Pad to align with prices
    pad = len(prices) - len(histogram)
    return (
        [None]*pad + macd_line[len(macd_line)-len(histogram):],
        [None]*pad + signal_line,
        [None]*pad + histogram
    )

def bollinger_bands(prices: List[float], period=20, std_dev=2) -> Tuple[List[float], List[float], List[float]]:
    """Upper band, middle band (SMA), lower band"""
    if len(prices) < period:
        return [], [], []
    upper, middle, lower = [], [], []
    for i in range(period - 1, len(prices)):
        window = prices[i-period+1:i+1]
        sma = sum(window) / period
        variance = sum((p - sma) ** 2 for p in window) / period
        std = math.sqrt(variance)
        upper.append(sma + std_dev * std)
        middle.append(sma)
        lower.append(sma - std_dev * std)
    return upper, middle, lower

def supertrend(prices: List[float], highs: List[float], lows: List[float], period=10, multiplier=3.0) -> Tuple[List[float], List[int]]:
    """Supertrend — returns (supertrend_values, direction: 1=bullish, -1=bearish)"""
    if len(prices) < period:
        return [], []
    
    atr_values = []
    for i in range(1, len(prices)):
        tr = max(highs[i] - lows[i], abs(highs[i] - prices[i-1]), abs(lows[i] - prices[i-1]))
        atr_values.append(tr)
    
    atr = [sum(atr_values[:period]) / period]
    for i in range(period, len(atr_values)):
        atr.append((atr[-1] * (period - 1) + atr_values[i]) / period)
    
    # Pad atr to match prices
    atr = [atr[0]] * (len(prices) - len(atr)) + atr
    
    upper_band = [(highs[i] + lows[i]) / 2 + multiplier * atr[i] for i in range(len(prices))]
    lower_band = [(highs[i] + lows[i]) / 2 - multiplier * atr[i] for i in range(len(prices))]
    
    supertrend_values = []
    direction = []
    
    for i in range(len(prices)):
        if i == 0:
            supertrend_values.append(lower_band[i])
            direction.append(1)
        else:
            if prices[i] > upper_band[i-1]:
                supertrend_values.append(lower_band[i])
                direction.append(1)
            elif prices[i] < lower_band[i-1]:
                supertrend_values.append(upper_band[i])
                direction.append(-1)
            else:
                supertrend_values.append(supertrend_values[-1])
                direction.append(direction[-1])
    
    return supertrend_values, direction

def money_flow_index(highs: List[float], lows: List[float], closes: List[float], volumes: List[float], period=14) -> List[float]:
    """Money Flow Index (volume-weighted RSI)"""
    if len(closes) < period + 1:
        return []
    
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    raw_money_flow = [tp * v for tp, v in zip(typical_prices, volumes)]
    
    positive_flow = []
    negative_flow = []
    for i in range(1, len(typical_prices)):
        if typical_prices[i] > typical_prices[i-1]:
            positive_flow.append(raw_money_flow[i])
            negative_flow.append(0)
        else:
            positive_flow.append(0)
            negative_flow.append(raw_money_flow[i])
    
    mfi_values = []
    for i in range(period - 1, len(positive_flow)):
        pos_sum = sum(positive_flow[i-period+1:i+1])
        neg_sum = sum(negative_flow[i-period+1:i+1])
        if neg_sum == 0:
            mfi_values.append(100.0)
        else:
            mfi_values.append(100 - (100 / (1 + pos_sum / neg_sum)))
    
    return mfi_values

def detect_w_structure(prices: List[float], window: int = 20) -> bool:
    """Detect W bottom pattern — double test of support"""
    if len(prices) < window * 2:
        return False
    
    recent = prices[-window*2:]
    mid = len(recent) // 2
    left = recent[:mid]
    right = recent[mid:]
    
    # Find local minima
    left_min = min(left)
    right_min = min(right)
    
    # W shape: two bottoms near same level, with peak in between
    if abs(left_min - right_min) / max(left_min, 0.01) < 0.15:  # Within 15%
        between = recent[recent.index(left_min):recent.index(right_min) + len(left)]
        if between and max(between) > left_min * 1.1:
            return True
    return False

def detect_m_structure(prices: List[float], window: int = 20) -> bool:
    """Detect M top pattern — double test of resistance"""
    if len(prices) < window * 2:
        return False
    
    recent = prices[-window*2:]
    mid = len(recent) // 2
    left = recent[:mid]
    right = recent[mid:]
    
    left_max = max(left)
    right_max = max(right)
    
    if abs(left_max - right_max) / max(left_max, 0.01) < 0.15:
        between = recent[recent.index(left_max):recent.index(right_max) + len(left)]
        if between and min(between) < left_max * 0.9:
            return True
    return False

def support_resistance_levels(prices: List[float], touches: int = 2) -> Tuple[List[float], List[float]]:
    """Find support and resistance levels by price clustering"""
    if len(prices) < 50:
        return [], []
    
    # Simple clustering approach
    price_counts = {}
    bucket_size = 0.01  # 1 cent buckets
    for p in prices:
        bucket = round(p / bucket_size) * bucket_size
        price_counts[bucket] = price_counts.get(bucket, 0) + 1
    
    # Find levels touched >= `touches` times
    levels = [(price, count) for price, count in price_counts.items() if count >= touches]
    levels.sort(key=lambda x: x[1], reverse=True)
    
    current = prices[-1]
    support = [p for p, c in levels if p < current][:3]  # Top 3 below current
    resistance = [p for p, c in levels if p > current][:3]  # Top 3 above current
    
    return support, resistance

# ============ SIGNAL GENERATOR ============

class TechnicalSignal:
    def __init__(self, condition_id: str, prices: List[float], volumes: List[float] = None):
        self.condition_id = condition_id
        self.prices = prices
        self.volumes = volumes or [1000] * len(prices)
        self.highs = [p * 1.005 for p in prices]  # Approximate from prices
        self.lows = [p * 0.995 for p in prices]
        self.signals = []
        self.confidence = 0.0
        self.direction = None  # 'LONG', 'SHORT', 'NEUTRAL'
    
    def analyze(self) -> dict:
        if len(self.prices) < 50:
            return {"error": "Insufficient data (need 50+ price points)"}
        
        current = self.prices[-1]
        
        # RSI
        rsi_vals = rsi(self.prices, 14)
        current_rsi = rsi_vals[-1] if rsi_vals else 50
        
        # EMA Cross
        ema_9 = ema(self.prices, 9)
        ema_21 = ema(self.prices, 21)
        ema_cross = None
        if len(ema_9) >= 2 and len(ema_21) >= 2:
            if ema_9[-2] <= ema_21[-2] and ema_9[-1] > ema_21[-1]:
                ema_cross = "BULLISH_CROSS"
            elif ema_9[-2] >= ema_21[-2] and ema_9[-1] < ema_21[-1]:
                ema_cross = "BEARISH_CROSS"
        
        # MACD
        macd_line, signal_line, histogram = macd(self.prices)
        macd_signal = None
        if histogram and len(histogram) >= 2:
            if histogram[-2] < 0 and histogram[-1] > 0:
                macd_signal = "BULLISH_DIVERGENCE"
            elif histogram[-2] > 0 and histogram[-1] < 0:
                macd_signal = "BEARISH_DIVERGENCE"
        
        # Bollinger
        bb_upper, bb_middle, bb_lower = bollinger_bands(self.prices)
        bb_position = None
        if bb_lower and current <= bb_lower[-1] * 1.02:
            bb_position = "OVERSOLD_BAND"
        elif bb_upper and current >= bb_upper[-1] * 0.98:
            bb_position = "OVERBOUGHT_BAND"
        
        # Supertrend
        st_values, st_dir = supertrend(self.prices, self.highs, self.lows)
        supertrend_signal = "BULLISH" if st_dir[-1] == 1 else "BEARISH" if st_dir else "NEUTRAL"
        
        # MFI
        mfi_vals = money_flow_index(self.highs, self.lows, self.prices, self.volumes)
        current_mfi = mfi_vals[-1] if mfi_vals else 50
        
        # W/M Patterns
        w_bottom = detect_w_structure(self.prices)
        m_top = detect_m_structure(self.prices)
        
        # Support/Resistance
        support, resistance = support_resistance_levels(self.prices)
        
        # ===== RATIONAL STRATEGY RULES =====
        long_signals = 0
        short_signals = 0
        
        # 1. NEVER short at daily bottom / NEVER long at daily top
        is_near_bottom = current < 0.10 or (bb_lower and current <= bb_lower[-1])
        is_near_top = current > 0.90 or (bb_upper and current >= bb_upper[-1])
        
        # 2. RSI oversold + W bottom + bullish EMA cross = STRONG LONG
        if current_rsi < 30 and w_bottom and ema_cross == "BULLISH_CROSS":
            long_signals += 3
        # 3. RSI overbought + M top + bearish EMA cross = STRONG SHORT
        elif current_rsi > 70 and m_top and ema_cross == "BEARISH_CROSS":
            short_signals += 3
        
        # 4. MACD bullish divergence + RSI < 50 = LONG
        if macd_signal == "BULLISH_DIVERGENCE" and current_rsi < 50:
            long_signals += 2
        # 5. MACD bearish divergence + RSI > 50 = SHORT
        elif macd_signal == "BEARISH_DIVERGENCE" and current_rsi > 50:
            short_signals += 2
        
        # 6. Supertrend bullish + price near support = LONG
        if supertrend_signal == "BULLISH" and support and current <= support[0] * 1.05:
            long_signals += 2
        # 7. Supertrend bearish + price near resistance = SHORT
        elif supertrend_signal == "BEARISH" and resistance and current >= resistance[0] * 0.95:
            short_signals += 2
        
        # 8. MFI extreme readings
        if current_mfi < 20:
            long_signals += 1
        elif current_mfi > 80:
            short_signals += 1
        
        # 9. Double test of support (W bottom already counted)
        # 10. Bollinger band extremes
        if bb_position == "OVERSOLD_BAND" and not is_near_bottom:
            long_signals += 1
        elif bb_position == "OVERBOUGHT_BAND" and not is_near_top:
            short_signals += 1
        
        # Apply safety rules
        if is_near_bottom and short_signals > 0:
            short_signals = 0  # NEVER short the bottom
        if is_near_top and long_signals > 0:
            long_signals = 0  # NEVER long the top
        
        # Determine direction
        if long_signals >= 4:
            self.direction = "LONG"
            self.confidence = min(long_signals * 0.15, 0.95)
        elif short_signals >= 4:
            self.direction = "SHORT"
            self.confidence = min(short_signals * 0.15, 0.95)
        else:
            self.direction = "NEUTRAL"
            self.confidence = 0.0
        
        return {
            "current_price": current,
            "rsi": current_rsi,
            "mfi": current_mfi,
            "ema_cross": ema_cross,
            "macd": macd_signal,
            "supertrend": supertrend_signal,
            "bollinger": bb_position,
            "w_bottom": w_bottom,
            "m_top": m_top,
            "support": support[:2] if support else [],
            "resistance": resistance[:2] if resistance else [],
            "near_bottom": is_near_bottom,
            "near_top": is_near_top,
            "long_signals": long_signals,
            "short_signals": short_signals,
            "direction": self.direction,
            "confidence": self.confidence
        }

def fetch_and_record(condition_id: str):
    """Fetch current price and record to DB"""
    url = f"https://gamma-api.polymarket.com/markets?conditionID={condition_id}"
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    
    if not data:
        return None
    
    market = data[0]
    prices = json.loads(market.get('outcomePrices', '["0","0"]'))
    yes = float(prices[0])
    no = float(prices[1])
    vol = float(market.get('volume', 0))
    
    record_price(condition_id, yes, no, vol)
    return {"yes": yes, "no": no, "volume": vol}

if __name__ == "__main__":
    init_db()
    print("Technical analysis engine initialized.")
    print("Use: record_price(condition_id, yes, no, volume)")
    print("Use: TechnicalSignal(condition_id, prices).analyze()")

# ============ MARKET CYPHER GREEN/RED DOT SIGNALS ============

def market_cypher_signal(prices: list, volumes: list = None, timeframe: str = "1h"):
    """
    Market Cypher-inspired Green/Red Dot signals for binary probability markets.
    
    GREEN DOT (Long signal):
    - RSI crosses above 30 from below (bullish reversal)
    - MACD histogram turns positive (momentum shift)
    - Price closes above EMA9 (short-term trend)
    - Volume above 80% of 20-period average (confirmation)
    
    RED DOT (Short signal):
    - RSI crosses below 70 from above (bearish reversal)
    - MACD histogram turns negative (momentum shift)
    - Price closes below EMA9 (short-term trend)
    - Volume above 80% of 20-period average (confirmation)
    
    Safety rules:
    - Never long at top (price > 0.90)
    - Never short at bottom (price < 0.10)
    
    Returns: dict with green_dot, red_dot, rsi, ema9, histogram, price, timeframe
    """
    if len(prices) < 30:
        return None
    
    volumes = volumes or [1000] * len(prices)
    
    # Calculate indicators
    rsi_vals = rsi(prices, 14)
    ema9 = ema(prices, 9)
    macd_line, signal_line, histogram = macd(prices)
    
    if not rsi_vals or len(rsi_vals) < 2:
        return None
    
    # Volume confirmation
    vol_avg = sum(volumes[-20:]) / 20
    current_vol = volumes[-1]
    vol_confirmed = current_vol >= vol_avg * 0.8
    
    current_price = prices[-1]
    current_rsi = rsi_vals[-1]
    prev_rsi = rsi_vals[-2]
    
    # GREEN DOT conditions
    green_dot = False
    
    # Primary: RSI crosses above 30 + MACD turns positive + above EMA9
    if prev_rsi <= 30 and current_rsi > 30:
        if histogram and len(histogram) >= 2 and histogram[-2] <= 0 and histogram[-1] > 0:
            if ema9 and current_price > ema9[-1] and vol_confirmed:
                green_dot = True
    
    # Alternative: RSI < 35 + MACD positive + above EMA9
    if not green_dot:
        if current_rsi < 35 and histogram and histogram[-1] > 0:
            if ema9 and current_price > ema9[-1] and vol_confirmed:
                green_dot = True
    
    # RED DOT conditions
    red_dot = False
    
    # Primary: RSI crosses below 70 + MACD turns negative + below EMA9
    if prev_rsi >= 70 and current_rsi < 70:
        if histogram and len(histogram) >= 2 and histogram[-2] >= 0 and histogram[-1] < 0:
            if ema9 and current_price < ema9[-1] and vol_confirmed:
                red_dot = True
    
    # Alternative: RSI > 65 + MACD negative + below EMA9
    if not red_dot:
        if current_rsi > 65 and histogram and histogram[-1] < 0:
            if ema9 and current_price < ema9[-1] and vol_confirmed:
                red_dot = True
    
    # Safety rules: never long at top, never short at bottom
    is_near_bottom = current_price < 0.10
    is_near_top = current_price > 0.90
    
    if green_dot and is_near_top:
        green_dot = False  # Don't long at top
    if red_dot and is_near_bottom:
        red_dot = False  # Don't short at bottom
    
    return {
        "green_dot": green_dot,
        "red_dot": red_dot,
        "rsi": current_rsi,
        "ema9": ema9[-1] if ema9 else None,
        "histogram": histogram[-1] if histogram else None,
        "price": current_price,
        "timeframe": timeframe,
        "vol_confirmed": vol_confirmed
    }

def run_full_analysis(condition_id: str, prices: list, volumes: list = None, 
                     entry_price: float = None, side: str = None) -> dict:
    """
    Complete technical + fundamental + Market Cypher analysis.
    
    Returns comprehensive signal with direction, confidence, and all indicators.
    """
    volumes = volumes or [1000] * len(prices)
    
    # Base technical analysis
    tech = TechnicalSignal(condition_id, prices, volumes)
    base_analysis = tech.analyze()
    
    # Market Cypher on 1h and 4h
    cypher_1h = market_cypher_signal(prices, volumes, "1h")
    
    # 4h aggregation
    prices_4h = prices[::4]
    volumes_4h = [sum(volumes[i:i+4]) for i in range(0, len(volumes), 4)]
    cypher_4h = market_cypher_signal(prices_4h, volumes_4h, "4h")
    
    # Override direction with Cypher if strong
    direction = base_analysis.get('direction', 'NEUTRAL')
    confidence = base_analysis.get('confidence', 0)
    
    if cypher_1h and cypher_1h['green_dot'] and cypher_4h and cypher_4h['green_dot']:
        direction = "LONG"
        confidence = max(confidence, 0.80)
    elif cypher_1h and cypher_1h['red_dot'] and cypher_4h and cypher_4h['red_dot']:
        direction = "SHORT"
        confidence = max(confidence, 0.80)
    elif cypher_1h and cypher_1h['green_dot']:
        direction = "LONG"
        confidence = max(confidence, 0.60)
    elif cypher_1h and cypher_1h['red_dot']:
        direction = "SHORT"
        confidence = max(confidence, 0.60)
    
    # Position PnL calculation
    pnl = None
    if entry_price and side:
        current = prices[-1] if side == 'YES' else 1 - prices[-1]
        pnl = current - entry_price
    
    return {
        "condition_id": condition_id,
        "current_price": prices[-1],
        "direction": direction,
        "confidence": confidence,
        "pnl_vs_entry": pnl,
        "indicators": {
            "rsi": base_analysis.get('rsi'),
            "mfi": base_analysis.get('mfi'),
            "ema_cross": base_analysis.get('ema_cross'),
            "macd": base_analysis.get('macd'),
            "supertrend": base_analysis.get('supertrend'),
            "bollinger": base_analysis.get('bollinger'),
            "w_bottom": base_analysis.get('w_bottom'),
            "m_top": base_analysis.get('m_top'),
            "support": base_analysis.get('support'),
            "resistance": base_analysis.get('resistance'),
            "near_bottom": base_analysis.get('near_bottom'),
            "near_top": base_analysis.get('near_top')
        },
        "cypher": {
            "1h": cypher_1h,
            "4h": cypher_4h
        },
        "signals": {
            "long": base_analysis.get('long_signals', 0),
            "short": base_analysis.get('short_signals', 0)
        },
        "safety_rules_applied": {
            "never_short_bottom": base_analysis.get('near_bottom', False),
            "never_long_top": base_analysis.get('near_top', False)
        }
    }

# ============ SIGNAL GENERATION HELPERS ============

def generate_position_recommendation(analysis: dict, current_side: str, position_size: float = 0) -> str:
    """Generate human-readable action recommendation."""
    direction = analysis.get('direction', 'NEUTRAL')
    confidence = analysis.get('confidence', 0)
    pnl = analysis.get('pnl_vs_entry')
    
    # Direction vs position alignment
    aligned = False
    if direction == 'LONG' and current_side == 'YES':
        aligned = True
    elif direction == 'SHORT' and current_side == 'NO':
        aligned = True
    elif direction == 'NEUTRAL':
        aligned = None
    
    if aligned is True and confidence >= 0.6:
        return f"✅ HOLD / ADD — Signal {direction} aligns with {current_side} (confidence: {confidence:.0%})"
    elif aligned is True:
        return f"✅ HOLD — Weak {direction} signal on {current_side} side"
    elif aligned is False and confidence >= 0.6:
        return f"🔄 FLIP — Strong {direction} signal contradicts {current_side} (confidence: {confidence:.0%})"
    elif aligned is False:
        return f"⚠️ MONITOR — Weak {direction} signal vs {current_side}, consider trimming"
    elif pnl and pnl < -0.05:  # >5% loss
        return f"⚠️ CONSIDER CLOSE — No signal but losing {abs(pnl)*100:.1f}%"
    else:
        return "⏸️ HOLD — No clear signal, no action needed"

if __name__ == "__main__":
    print("Technical analysis engine with Market Cypher signals loaded.")
    print("Use: run_full_analysis(condition_id, prices, volumes, entry_price, side)")

def generate_binary_price_path(entry: float, current: float, hours: int = 168):
    """Generate realistic binary market price path for backtesting."""
    import random, math
    prices = []
    price = entry
    drift_per_hour = (current - entry) / hours
    
    for i in range(hours):
        reversion = (current - price) * 0.05
        distance_from_bound = min(price, 1 - price)
        vol_scale = max(0.3, distance_from_bound * 2)
        noise = random.gauss(0, 0.005 * vol_scale)
        
        if random.random() < 0.1:
            noise *= 3
        
        price = price + drift_per_hour + reversion + noise
        price = max(0.01, min(0.99, price))
        prices.append(price)
    
    prices[-1] = current
    return prices
