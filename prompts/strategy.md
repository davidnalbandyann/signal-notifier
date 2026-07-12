Strategy: Support & Resistance Mean Reversion
1. Level Identification

Identify clear, horizontal support and resistance levels formed by at least two touches (swing highs/lows).

Support: a price floor where the market has previously reversed upward.

Resistance: a price ceiling where the market has previously reversed downward.

Only use visible, well-defined levels. Ignore minor wicks unless they create a clear reaction.

2. Near-Level Condition

The current price is considered “near” a level if it is within a distance equal to the average true range (ATR, 14) of the chart’s timeframe (or visually within the last 3–5 candles’ body/wick range of the level).

If price is near support → prepare for a LONG (opposite direction to the prior move into support).

If price is near resistance → prepare for a SHORT.

If price is mid-range (not near any level), direction is NEUTRAL and score is 0.

3. Entry Confirmation (Mandatory)

A trade is only valid when price touches or closely approaches the level AND a reversal candlestick signal forms:

Bullish pin bar / hammer / engulfing at support for LONG.

Bearish pin bar / shooting star / engulfing at resistance for SHORT.

No entry without a confirmation candle closing at the level.

4. Risk Management

Stop loss: placed just beyond the level (below the support’s lowest wick for longs; above the resistance’s highest wick for shorts), plus a small buffer (e.g., a few pips/ticks).

Take profit: first target is the nearest opposing level. If none is visible, set a minimum 2R target (twice the stop loss distance).

If the stop loss distance is too wide relative to the potential reward (less than 1.5R), discard the setup (score 0).

5. Scoring

Score from 0 to 10 based on:

Level clarity (multiple touches, strong historical reactions).

Perfect touch of the level with a clear reversal candle.

Favorable risk-to-reward ratio (≥2R).

Score 0 if no level is near, no confirmation, or risk/reward is inadequate. Direction must be NEUTRAL when score is 0.

Output Format (Strict JSON)
{
"score": <float 0-10>,
"direction": "LONG" | "SHORT" | "NEUTRAL",
"reason": "<concise reasoning covering the level, price nearness, confirmation candle, and R:R>",
"entry": "<entry price or null>",
"stop_loss": "<stop loss price or null>",
"take_profit": "<take profit price or null>"
}

All price fields must be exact numbers visible on the chart, or null if no trade.

