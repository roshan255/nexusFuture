from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Sequence
from bot.models import Candidate

class Strategy(ABC):
    """Add a strategy by implementing analyse(); execution code remains untouched."""
    name: str
    @abstractmethod
    def analyse(self) -> Sequence[Candidate]: ...
