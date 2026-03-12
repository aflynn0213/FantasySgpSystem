from abc import ABC, abstractmethod
from typing import List, Tuple
import pandas as pd

class ISgpCalculator(ABC):
    """SGP Calculation Interface"""

    @abstractmethod
    def update_stats(self, stats: pd.DataFrame) -> None:
        """Replace the internal stats DataFrame used for SGP calculations."""

    @abstractmethod
    def cat_calc_sgp(self, categories: List[str]) -> pd.DataFrame:
        """Compute counting-stat SGPs and return a DataFrame of SGP_<cat> for cat in categories columns."""

    @abstractmethod
    def rate_calc_sgp(self, categories: List[Tuple[str, str]]) -> pd.DataFrame:
        """Compute rate-based SGPs and return a DataFrame of SGP_<cat> for cat in categories columns."""
