from abc import ABC,abstractmethod
from typing import Dict
import pandas as pd

class IProjectionLoader(ABC):
    @abstractmethod
    def load(self, proj: str, player_type: str, weeks: int) -> Dict[str, pd.DataFrame]:
        """
        Load projection-related DataFrames and metadata.
        Return a dict with keys:
          - 'proj_read': DataFrame
          - 'stats': DataFrame
          - 'auc_calc': DataFrame
          - 'period': str  (e.g., 'pre','td','ros')
        """