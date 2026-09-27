from bot.strategies.rule_based import RuleBasedStrategy


def test_small_entry_gate_rejects_long_into_resistance_and_short_into_support():
    assert RuleBasedStrategy._is_opposing_level_chase("LONG", "near_resistance")
    assert RuleBasedStrategy._is_opposing_level_chase("LONG", "breakout_above_resistance")
    assert RuleBasedStrategy._is_opposing_level_chase("SHORT", "near_support")
    assert RuleBasedStrategy._is_opposing_level_chase("SHORT", "breakdown_below_support")


def test_small_entry_gate_keeps_rebounds_and_range_entries():
    assert not RuleBasedStrategy._is_opposing_level_chase("LONG", "near_support")
    assert not RuleBasedStrategy._is_opposing_level_chase("SHORT", "near_resistance")
    assert not RuleBasedStrategy._is_opposing_level_chase("LONG", "between_levels")
