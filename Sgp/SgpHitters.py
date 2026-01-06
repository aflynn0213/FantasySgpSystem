from typing import List, Dict
import pandas as pd
import numpy as np
from Sgp.params.SgpParams import SgpParams
from Sgp.calc.ISgpCalculator import ISgpCalculator

NUM_TEAMS = 12
NUM_BATS = 13

class SgpHitters:
    def __init__(self,
                 data: Dict[str, pd.DataFrame],
                 params: SgpParams,
                 sgp_calculator: ISgpCalculator,
                 sb_included: bool = False) -> None:
        """
        Initialize SgpHitters with injected dependencies.
        
        Args:
            data: Dictionary with 'proj_read', 'stats', 'auc_calc', 'weeks', 'period'
            params: SgpParams with replacement_levels and cat_stds
            sgp_calculator: ISgpCalculator for SGP computations
            sb_included: Whether to include stolen bases
        """
        print("Initializing SgpHitters...")
        
        # Extract data from injected dictionary
        self.stats = data["stats"].copy()
        self.proj_read = data["proj_read"].copy()
        self.auc_calc = data["auc_calc"].copy()
        self.weeks = data["weeks"]
        self.period = data.get("period", "pre")
        
        self.sb_included = sb_included
        self._sgp_calculator = sgp_calculator
        self._params = params
        
        print("Processing hitters SGP...")
        self.stats["PA_SH"] = self.stats['PA'] - self.stats['SH']
        self._process_sgp()
        
        self.sgp_df['PA'] = self.stats['PA'] - self.stats['SH']
        self.sgp_df[['Name', 'PlayerId']] = self.stats[['Name', 'PlayerId']]
        self.sgp_df.set_index(['Name','PlayerId'], inplace=True)
        
        print(f"***SgpHitters initialized***")

    def _process_sgp(self):
        """Delegate SGP calculations to the injected calculator."""
        print("Calculating SGP for counting stats (R, HR, RBI, SB)...")
        counting_stats = ['R', 'HR', 'RBI', 'SB']
        self.sgp_df = self._sgp_calculator.cat_calc_sgp(counting_stats)
        
        print("Calculating SGP for rate stats (OBP, SLUG)...")
        rate_stats = [('OBP', 'PA_SH'), ('SLG', 'AB')]
        self.sgp_df = pd.concat([self.sgp_df, self._sgp_calculator.rate_calc_sgp(rate_stats)], axis=1)
        
        print("***Hitters SGP calculation complete.***")
