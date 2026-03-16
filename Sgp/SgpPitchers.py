from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from Sgp.SgpBase import SgpBase
from Sgp.params.SgpParams import SgpParams
from Sgp.calc.ISgpCalculator import ISgpCalculator
from utils.common_utils import parse_pitcher_config_categories

class SgpPitchers(SgpBase):
    def __init__(self,
                 data: Dict[str, pd.DataFrame],
                 params: SgpParams,
                 sgp_calculator: ISgpCalculator,
                 ip_adj: Optional[str] = None) -> None:
        """
        Initialize SgpPitchers with injected dependencies.
        
        Args:
            data: Dictionary with 'proj_read', 'stats', 'auc_calc', 'weeks', 'period'
            params: SgpParams with replacement_levels and cat_stds
            sgp_calculator: ISgpCalculator for SGP computations
            ip_adj: Optional IP adjustment projection system name
        """
        print("Initializing SgpPitchers...")
        super().__init__(data, params, sgp_calculator)

        self.ip_adj = ip_adj
        self.__counting_stats, self.__rate_stats = parse_pitcher_config_categories()

        if ip_adj:
            print("Adjusting pitcher playing time...")
            self.__adjust_playing_time(ip_adj)
            # Push adjusted stats into the calculator so SGP math uses correct IP/TBF
            self._sgp_calculator.update_stats(self.stats)
        
        print("Processing pitchers SGP...")
        self._process_sgp()
        
        self.sgp_df['IP'] = self.stats['IP']
        self.sgp_df['GS'] = self.stats['GS']
        self._finalize_sgp_df()

        print(f"***SgpPitchers initialized***")

    def _process_sgp(self):
        """Delegate SGP calculations to the injected calculator."""
        print(f"Calculating SGP for counting stats {self.__counting_stats}...")
        self.sgp_df = self._sgp_calculator.cat_calc_sgp(self.__counting_stats)
        
        print(f"Calculating SGP for rate stats {self.__rate_stats}...")
        self.sgp_df = pd.concat([self.sgp_df, self._sgp_calculator.rate_calc_sgp(self.__rate_stats)], axis=1)
        
        print("***Pitchers SGP calculation complete.***")
            
    def __adjust_playing_time(self, ip_adj):
        play_time_df = pd.read_excel(f'projections/pitching/fangraphs_pitching_{ip_adj}.xlsx', sheet_name=0)
        play_time_df['PlayerId'] = play_time_df['PlayerId'].astype(str)
        play_time_df = play_time_df.rename(columns={'IP': 'new_IP', 'TBF': 'new_TBF'})
        self.stats = self.stats.merge( play_time_df[['PlayerId', 'new_IP', 'new_TBF']],  
                                    on='PlayerId', 
                                    how='left'
                                )
        # Pitchers not in ip_adj projection keep their original IP/TBF
        self.stats['new_IP'] = self.stats['new_IP'].fillna(self.stats['IP'])
        self.stats['new_TBF'] = self.stats['new_TBF'].fillna(self.stats['TBF'])

        new_ip_multiple = self.stats['new_IP']/self.stats["IP"]
        new_tbf_multiple = self.stats['new_TBF']/self.stats["TBF"]
        
        new_ip = self.stats['new_IP']
        new_tbf = self.stats['new_TBF']
        
        for cat in ['QS', 'SO', 'H', 'BB', 'ER', 'SV', 'HLD']:
            if cat in ['QS', 'SV', 'HLD']:
                self.stats[cat] = new_ip_multiple*self.stats[cat]
            elif cat == 'SO':
                self.stats[cat] = new_tbf*self.stats['K%']
            elif cat == 'H':
                self.stats[cat] = self.stats['WHIP']*new_ip - self.stats['BB%']*new_tbf
            elif cat == 'BB':
                self.stats[cat] = new_tbf*self.stats['BB%']
            elif cat == 'ER':
                self.stats[cat] = new_ip*self.stats['ERA'] / 9
        
        self.stats['IP'] = new_ip
        self.stats['TBF'] = new_tbf
