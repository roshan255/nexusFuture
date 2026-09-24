from __future__ import annotations

from datetime import date
import time


class TradeLimitService:
    """In-process cooldown and daily-entry guard; exchange reconciliation remains authoritative for positions."""

    def __init__(self, settings) -> None:
        self.settings = settings
        self.day = date.today()
        self.entries = 0
        self.last_entry_at = 0.0

    def allow_entry(self) -> tuple[bool, str]:
        if date.today() != self.day:
            self.day, self.entries, self.last_entry_at = date.today(), 0, 0.0
        if self.entries >= self.settings.max_trades_per_day:
            return False, "max_trades_per_day"
        remaining = self.settings.cooldown_seconds - (time.monotonic() - self.last_entry_at)
        if remaining > 0:
            return False, f"cooldown_{int(remaining)}s"
        return True, ""

    def record_entry(self) -> None:
        self.entries += 1
        self.last_entry_at = time.monotonic()
