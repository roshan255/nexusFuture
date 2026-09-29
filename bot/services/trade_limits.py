from __future__ import annotations

from datetime import date
import json
import logging
from pathlib import Path
import time


class TradeLimitService:
    """Persistent daily-entry and cooldown guard; exchange reconciliation remains authoritative for positions."""

    def __init__(self, settings, state_path: str | Path = ".trade_limits.json") -> None:
        self.settings = settings
        self.state_path = Path(state_path)
        self.day = date.today()
        self.entries = 0
        self.last_entry_at = 0.0
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            saved_day = date.fromisoformat(data.get("day", ""))
            if saved_day == date.today():
                self.day = saved_day
                self.entries = int(data.get("entries", 0))
                last_time = float(data.get("last_entry_time", 0.0))
                if last_time > 0:
                    elapsed = time.time() - last_time
                    if elapsed >= 0:
                        self.last_entry_at = time.monotonic() - elapsed
        except Exception as exc:
            logging.getLogger("futures_bot").debug("trade_limit_state_load_failed detail=%s", exc)

    def _save_state(self) -> None:
        try:
            elapsed_since_last = time.monotonic() - self.last_entry_at if self.last_entry_at > 0 else 0
            last_epoch = time.time() - elapsed_since_last if self.last_entry_at > 0 else 0.0
            data = {
                "day": self.day.isoformat(),
                "entries": self.entries,
                "last_entry_time": last_epoch,
            }
            self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logging.getLogger("futures_bot").debug("trade_limit_state_save_failed detail=%s", exc)

    def allow_entry(self) -> tuple[bool, str]:
        if date.today() != self.day:
            self.day, self.entries, self.last_entry_at = date.today(), 0, 0.0
            self._save_state()
        if self.entries >= self.settings.max_trades_per_day:
            return False, "max_trades_per_day"
        remaining = self.settings.cooldown_seconds - (time.monotonic() - self.last_entry_at)
        if remaining > 0:
            return False, f"cooldown_{int(remaining)}s"
        return True, ""

    def record_entry(self) -> None:
        self.entries += 1
        self.last_entry_at = time.monotonic()
        self._save_state()
