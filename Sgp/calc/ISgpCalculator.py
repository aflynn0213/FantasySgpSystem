from abc import ABC, abstractmethod
from typing import List, Tuple
import pandas as pd

class ISgpCalculator(ABC):
    """SGP Calculation Interface"""

    @abstractmethod
    def counting_stat_sgp(self, stats: pd.DataFrame, categories: List[str]) -> pd.DataFrame:
        """Compute counting-stat SGPs and return a DataFrame of SGP_<cat> for cat in categories columns."""

    @abstractmethod
    def rate_stat_sgp(self, stats: pd.DataFrame, categories: List[Tuple[str, str]]) -> pd.DataFrame:
        """Computer rate-based SGPs and return a DataFrame of SGP_<cat> for cat in categories columns """