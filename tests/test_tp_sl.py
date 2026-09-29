import pytest

from bot.risk_manager import protective_prices


def test_long_and_short_protection():
    long_prot = protective_prices(100.0, "LONG", 0.5, 0.3, 0.01)
    assert long_prot.take_profit == 100.5
    assert long_prot.stop_loss == 99.7

    short_prot = protective_prices(100.0, "SHORT", 0.5, 0.3, 0.01)
    assert short_prot.take_profit == 99.5
    assert short_prot.stop_loss == 100.3


def test_invalid_direction_raises():
    with pytest.raises(ValueError, match="direction must be LONG or SHORT"):
        protective_prices(100.0, "WAIT", 1.5, 1.0, 0.01)
