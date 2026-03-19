from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd

from Sgp.params.SgpParams import SgpParams
from Sgp.calc.ISgpCalculator import ISgpCalculator


class SgpBase(ABC):
    """Abstract base class for SgpHitters and SgpPitchers.

    Handles common data extraction from the data dictionary and exposes
    shared helpers. Subclasses must implement _process_sgp().
    """

    def __init__(self,
                 data: Dict[str, pd.DataFrame],
                 params: SgpParams,
                 sgp_calculator: ISgpCalculator) -> None:
        """
        Args:
            data: Dictionary with keys 'stats', 'proj_read', 'auc_calc',
                  'weeks', and optionally 'period' / 'projection'.
            params: SgpParams carrying replacement_levels and cat_stds.
            sgp_calculator: Calculator implementing ISgpCalculator.
        """
        self.stats: pd.DataFrame = data["stats"].copy()
        self.proj_read: pd.DataFrame = data["proj_read"].copy()
        self.auc_calc: pd.DataFrame = data["auc_calc"].copy()
        self.weeks: int = data["weeks"]
        self.period: str = data.get("period", "pre")
        self.proj: str = data.get("projection", "unknown")

        self._sgp_calculator: ISgpCalculator = sgp_calculator
        self._params: SgpParams = params

        self.sgp_df: pd.DataFrame = pd.DataFrame()

    def _finalize_sgp_df(self) -> None:
        """Attach Name/PlayerId (and ADP when available) to sgp_df, then index."""
        self.sgp_df[['Name', 'PlayerId']] = self.stats[['Name', 'PlayerId']]
        if 'ADP' in self.proj_read.columns:
            adp_map = self.proj_read.drop_duplicates('PlayerId').set_index('PlayerId')['ADP']
            self.sgp_df['ADP'] = self.stats['PlayerId'].map(adp_map).values
        self.sgp_df.set_index(['Name', 'PlayerId'], inplace=True)

    @abstractmethod
    def _process_sgp(self) -> None:
        """Calculate SGP z-scores and populate self.sgp_df."""
        pass

