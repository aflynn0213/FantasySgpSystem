from typing import List, Dict
import pandas as pd
import numpy as np
from Sgp.SgpBase import SgpBase
from Sgp.params.SgpParams import SgpParams
from Sgp.calc.ISgpCalculator import ISgpCalculator
from utils.common_utils import parse_hitter_config_categories

class SgpHitters(SgpBase):
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
        super().__init__(data, params, sgp_calculator)

        self.sb_included = sb_included

        print("Processing hitters SGP...")
        self.stats["PA_SH"] = self.stats['PA'] - self.stats['SH']
        self._process_sgp()

        self.sgp_df['PA'] = self.stats['PA'] - self.stats['SH']
        self._finalize_sgp_df()

        print(f"***SgpHitters initialized***")

    def _process_sgp(self):
        """Delegate SGP calculations to the injected calculator."""
        counting_stats, rate_stats = parse_hitter_config_categories()
        print(f"Calculating SGP for counting stats {counting_stats}...")
        self.sgp_df = self._sgp_calculator.cat_calc_sgp(counting_stats)
        
        print(f"Calculating SGP for rate stats {rate_stats}...")
        self.sgp_df = pd.concat([self.sgp_df, self._sgp_calculator.rate_calc_sgp(rate_stats)], axis=1)
        
        print("***Hitters SGP calculation complete.***")
