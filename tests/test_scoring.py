from types import SimpleNamespace
from bot.scorer import score


def test_scoring():
    x = SimpleNamespace(
        ema9=2, ema21=1, return_5=0.02, volume_ratio=2, rsi=55, atr=1
    )
    weights = {
        "trend": 20, "momentum": 15, "volume": 15, "open_interest": 15,
        "taker": 15, "orderbook": 10, "funding": 10
    }
    c = score("X", 1, 1, 1, x, 0.01, 0, 1.2, 0.1, 0.001, weights)
    assert c.direction == "LONG"
    assert c.breakdown["long_score"] > c.breakdown["short_score"]


def test_directional_open_interest():
    weights = {"open_interest": 100}
    # Rising price + rising OI = Long accumulation (bullish)
    up_bar = SimpleNamespace(return_5=0.01)
    cand_long = score("X", 100, 1, 1000, up_bar, 0.03, 0, 1, 0, 0.001, weights)
    assert cand_long.direction == "LONG"
    assert cand_long.score > 50

    # Falling price + rising OI = Short accumulation (bearish)
    down_bar = SimpleNamespace(return_5=-0.01)
    cand_short = score("X", 100, -1, 1000, down_bar, 0.03, 0, 1, 0, 0.001, weights)
    assert cand_short.direction == "SHORT"
    assert cand_short.score > 50


def test_directional_adx():
    weights = {"adx": 100}
    # Strong bullish DI difference (+DI > -DI)
    bull_bar = SimpleNamespace(adx=30, plus_di=35, minus_di=15)
    cand_bull = score("X", 100, 0, 1000, bull_bar, 0, 0, 1, 0, 0.001, weights)
    assert cand_bull.direction == "LONG"
    assert cand_bull.score > 50

    # Strong bearish DI difference (-DI > +DI)
    bear_bar = SimpleNamespace(adx=30, plus_di=15, minus_di=35)
    cand_bear = score("X", 100, 0, 1000, bear_bar, 0, 0, 1, 0, 0.001, weights)
    assert cand_bear.direction == "SHORT"
    assert cand_bear.score > 50
