from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from Sgp.params.SgpParams import SgpParams
from Sgp.calc.ISgpCalculator import ISgpCalculator

NUM_TEAMS = 12
NUM_STARTERS = 9
NUM_RELIEVERS = 3

class SgpPitchers:
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
        
        # Extract data from injected dictionary
        self.stats = data["stats"].copy()
        self.proj_read = data["proj_read"].copy()
        self.auc_calc = data["auc_calc"].copy()
        self.weeks = data["weeks"]
        self.period = data.get("period", "pre")
        
        self.ip_adj = ip_adj
        self._sgp_calculator = sgp_calculator
        self._params = params
        
        if ip_adj:
            print("Adjusting pitcher playing time...")
            self.__adjust_playing_time(ip_adj)
        
        print("Processing pitchers SGP...")
        self._process_sgp()
        
        self.sgp_df['IP'] = self.stats['IP']
        self.sgp_df['GS'] = self.stats['GS']
        
        self.sgp_df[['Name', 'PlayerId']] = self.stats[['Name', 'PlayerId']]
        self.sgp_df.set_index(['Name','PlayerId'], inplace=True)
        
        print(f"***SgpPitchers initialized***")

    def _process_sgp(self):
        """Delegate SGP calculations to the injected calculator."""
        print("Calculating SGP for counting stats (SO, QS, SV_HLD)...")
        counting_stats = ['SO', 'QS', 'SV_HLD']
        self.sgp_df = self._sgp_calculator.cat_calc_sgp(counting_stats)
        
        print("Calculating SGP for rate stats (ERA, WHIP, K/BB)...")
        rate_stats = [('ERA','IP'), ('WHIP', 'IP'), ('K/BB', 'BB')]
        self.sgp_df = pd.concat([self.sgp_df, self._sgp_calculator.rate_calc_sgp(rate_stats)], axis=1)
        
        print("***Pitchers SGP calculation complete.***")
            
    def __adjust_playing_time(self, ip_adj):
        play_time_df = pd.read_excel(f'projections/fangraphs_pitching_{ip_adj}.xlsx', sheet_name=0)
        play_time_df = play_time_df.rename(columns={'IP': 'new_IP', 'TBF': 'new_TBF'})
        self.stats = self.stats.merge( play_time_df[['PlayerId', 'new_IP', 'new_TBF']],  
                                    on='PlayerId', 
                                    how='inner'
                                )
        
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
