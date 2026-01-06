from abc import ABC, abstractmethod
from typing import Any

class ILeagueDataLoader(ABC):
    @abstractmethod
    def load(self, path: str) -> Any:
        """Return any format containing league historical data (openpyxl workbook or similar)."""
