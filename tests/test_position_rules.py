import pytest
from bot.services.positions import PositionService, PositionStateUnknown


class MockPositionsClient:
    def __init__(self, rows):
        self.rows = rows

    def positions(self):
        return self.rows


def test_multiple_positions_are_unknown():
    client = MockPositionsClient([{"positionAmt": "1"}, {"positionAmt": "-1"}])
    with pytest.raises(PositionStateUnknown, match="one-position rule"):
        PositionService(client).current_position()


def test_one_position_is_known():
    client = MockPositionsClient([{"symbol": "BTCUSDT", "positionAmt": "1", "entryPrice": "50000"}])
    position = PositionService(client).current_position()
    assert position is not None
    assert position.symbol == "BTCUSDT"
    assert position.quantity == 1.0
    assert position.entry_price == 50000.0


def test_no_open_position_returns_none():
    client = MockPositionsClient([{"symbol": "BTCUSDT", "positionAmt": "0", "entryPrice": "0"}])
    assert PositionService(client).current_position() is None
