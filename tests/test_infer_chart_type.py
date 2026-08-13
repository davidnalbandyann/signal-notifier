from app.database import infer_chart_type


def test_empty_inputs_fall_back_to_other():
    assert infer_chart_type("", "") == "other"


def test_whitespace_inputs_fall_back_to_other():
    assert infer_chart_type("   ", "  ") == "other"


def test_forex_url_detected():
    assert infer_chart_type("", "https://tradingview.com/chart/?symbol=FX:EURUSD") == "forex"


def test_forex_name_detected():
    assert infer_chart_type("EUR/USD 1h", "") == "forex"


def test_stocks_url_detected():
    assert infer_chart_type("", "https://tradingview.com/chart/?symbol=NASDAQ:NVDA") == "stocks"


def test_crypto_url_detected():
    assert infer_chart_type("", "https://tradingview.com/chart/?symbol=BINANCE:BTCUSDT") == "crypto"


def test_unknown_inputs_fall_back_to_other():
    assert infer_chart_type("My Random Chart", "https://example.com/no-symbol") == "other"