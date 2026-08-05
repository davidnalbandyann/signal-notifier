"""Registry of C++ strategies compiled into the signal engine.

Each entry describes a strategy type the C++ factory (`strategy.cpp`)
can instantiate, plus the schema of its configurable parameters. The
schema drives the parameter form in the frontend and validates saves.

To add a new C++ strategy: implement it in trading-signal-engine/src,
register it in `createStrategy()`, rebuild, then add its entry here.
"""

CPP_STRATEGIES: dict[str, dict] = {
    "bollinger_squeeze": {
        "label": "Bollinger Squeeze Breakout",
        "description": (
            "Detects a volatility squeeze (narrow Bollinger Bands) followed by an "
            "upside breakout with a volume spike and optional RSI confirmation."
        ),
        "params": {
            "period": {"type": "int", "default": 20, "min": 5, "max": 200, "hint": "Bollinger Band SMA period"},
            "stddev_mult": {"type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1, "hint": "Standard deviation multiplier"},
            "bandwidth_threshold": {"type": "float", "default": 0.03, "min": 0.001, "max": 0.5, "step": 0.005, "hint": "Bandwidth below which is a squeeze"},
            "volume_mult": {"type": "float", "default": 1.5, "min": 1.0, "max": 5.0, "step": 0.1, "hint": "Min volume ratio vs SMA"},
            "squeeze_candles": {"type": "int", "default": 3, "min": 1, "max": 20, "hint": "Consecutive candles in squeeze"},
            "use_rsi": {"type": "bool", "default": True, "hint": "Require RSI above threshold"},
            "rsi_period": {"type": "int", "default": 14, "min": 2, "max": 50, "hint": "RSI lookback period"},
            "rsi_threshold": {"type": "float", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "hint": "Min RSI to confirm breakout"},
            "cooldown_candles": {"type": "int", "default": 4, "min": 0, "max": 50, "hint": "Candles between signals"},
        },
    },
    "volume_profile_sr": {
        "label": "Volume Profile S/R",
        "description": (
            "Builds a volume profile over the lookback window, finds high-volume "
            "support/resistance zones, and signals bounces off them with volume confirmation."
        ),
        "params": {
            "lookback_candles": {"type": "int", "default": 300, "min": 50, "max": 1000, "hint": "Candles used for the volume profile"},
            "bucket_size": {"type": "float", "default": 100.0, "min": 0.01, "hint": "Price bucket width"},
            "zone_window": {"type": "int", "default": 3, "min": 1, "max": 50, "hint": "Smoothing window around peaks"},
            "min_zone_volume": {"type": "float", "default": 5000.0, "min": 0.0, "hint": "Min volume for a zone to count (absolute or % of peak)"},
            "min_zone_volume_mode": {"type": "str", "default": "absolute", "options": ["absolute", "relative"], "hint": "absolute = raw volume, relative = % of peak"},
            "touch_threshold_pct": {"type": "float", "default": 0.5, "min": 0.0, "max": 10.0, "step": 0.1, "hint": "Max wick distance from level (in %)"},
            "volume_mult": {"type": "float", "default": 1.5, "min": 1.0, "max": 5.0, "step": 0.1, "hint": "Min volume ratio vs SMA"},
            "cooldown_candles": {"type": "int", "default": 6, "min": 0, "max": 50, "hint": "Candles between same-direction signals"},
            "recalc_interval": {"type": "int", "default": 50, "min": 5, "max": 500, "hint": "Candles between zone recalculations"},
            "volume_period": {"type": "int", "default": 20, "min": 5, "max": 200, "hint": "Avg volume lookback"},
            "stop_loss_pct": {"type": "float", "default": 2.0, "min": 0.0, "max": 10.0, "step": 0.1, "hint": "Stop loss distance (in %)"},
            "take_profit_pct": {"type": "float", "default": 4.0, "min": 0.0, "max": 20.0, "step": 0.1, "hint": "Take profit distance (in %)"},
            "wick_threshold_pct": {"type": "float", "default": 0.5, "min": 0.0, "max": 5.0, "step": 0.1, "hint": "Max wick touch distance (in %)"},
            "body_weight_pct": {"type": "int", "default": 70, "min": 0, "max": 100, "hint": "Volume weight given to candle bodies"},
            "trend_filter_enabled": {"type": "bool", "default": False, "hint": "Only long above SMA / short below SMA"},
            "trend_period": {"type": "int", "default": 50, "min": 5, "max": 300, "hint": "Trend SMA period"},
            "confirmation_candles": {"type": "int", "default": 0, "min": 0, "max": 10, "hint": "Candles required to confirm a touch (0 = instant)"},
            "max_zone_window": {"type": "int", "default": 50, "min": 1, "max": 200, "hint": "Cap on zone_window"},
        },
    },
}


def get_cpp_catalog() -> list[dict]:
    return [
        {"key": key, "label": meta["label"], "description": meta["description"], "params": meta["params"]}
        for key, meta in CPP_STRATEGIES.items()
    ]


def normalize_cpp_params(engine_type: str, raw_params: dict | None) -> dict:
    """Cast/validate raw params against the registry schema. Unknown keys are dropped."""
    meta = CPP_STRATEGIES.get(engine_type)
    if meta is None:
        raise ValueError(f"unknown C++ strategy type: {engine_type}")
    raw = raw_params or {}
    schema = meta["params"]
    out: dict = {}
    for key, spec in schema.items():
        if key not in raw:
            out[key] = spec["default"]
            continue
        ptype = spec["type"]
        val = raw[key]
        if ptype == "bool":
            if isinstance(val, str):
                val = val.lower() in ("true", "1", "yes")
            out[key] = bool(val)
        elif ptype == "int":
            try:
                out[key] = int(round(float(val)))
            except (ValueError, TypeError):
                out[key] = spec["default"]
        elif ptype == "float":
            try:
                out[key] = float(val)
            except (ValueError, TypeError):
                out[key] = spec["default"]
        else:
            out[key] = str(val)
    return out


def validate_strategy_type(engine_type: str) -> bool:
    return engine_type in CPP_STRATEGIES
