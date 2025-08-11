from typing import List
import pandas as pd
import numpy as np
import string
from Sgp.SgpBase import SgpBase

NUM_TEAMS = 12
NUM_BATS = 13

class SgpHitters(SgpBase):
    def __init__(self,proj,sb_included=False,weeks=26) -> None:
        super().__init__(proj,"hitting",weeks)
        
        self.sb_included = sb_included
        
        print("Loading replacement levels and category standard deviations...")
        self.replacement_levels = self._load_replacement_levels()
        self.cat_stds = self._load_category_stds()
        
        self.team_opportunities = {}
        self.team_value = {}
 
        self._team_rate_values_processing()
        
        print("Processing hitters SGP...")
        self.stats["PA_SH"] = self.stats['PA'] - self.stats['SH']
        self._process_sgp()
        
        self.sgp_df['PA'] = self.stats['PA'] - self.stats['SH']
        self.sgp_df[['Name', 'PlayerId']] = self.stats[['Name', 'PlayerId']]
        self.sgp_df.set_index(['Name','PlayerId'], inplace=True)
        
        print(f"***SgpHitters initialized***")

    def _process_sgp(self):
        print("Calculating SGP for counting stats (R, HR, RBI, SB)...")
        counting_stats = ['R', 'HR', 'RBI', 'SB']
        self.sgp_df = self._cat_calc_sgp(counting_stats)
        
        print("Calculating SGP for rate stats (OBP, SLUG)...")
        rate_stats = [('OBP', 'PA_SH'), ('SLG', 'AB')]
        self.sgp_df = pd.concat([self.sgp_df, self._rate_calc_sgp(rate_stats)],axis=1)
        
        print("***Hitters SGP calculation complete.***")
        
    def _team_rate_values_processing(self,ip_adj=None):
        self.auc_calc = self.auc_calc.merge(self.proj_read[['PlayerId','SH','AB']],
                                            on='PlayerId',
                                            how='left')
        
        self.auc_calc['PA_SH'] = self.auc_calc['PA'] - self.auc_calc['SH'] 
                
        for cat,val in [('OBP','PA_SH'), ('SLG','AB')]:
            avg_opps = self.auc_calc[val].head(NUM_BATS*NUM_TEAMS).mean()                
            avg_team_opps_wo_replacement = avg_opps*(NUM_BATS-1)
            avg_team_value_wo_replacement = avg_team_opps_wo_replacement*self.replacement_levels[cat]

            self.team_opportunities[val] = avg_team_opps_wo_replacement
            self.team_value[f'{cat}_{val}'] = avg_team_value_wo_replacement
            
    def _load_replacement_levels(self):
        return {
            'R': self.sheet['Q26'].value, 'HR': self.sheet['R26'].value, 'RBI': self.sheet['S26'].value, 
            'SB': self.sheet['T26'].value, 'OBP': self.sheet['U26'].value, 'SLG': self.sheet['V26'].value
        }
        
    def _load_category_stds(self):
        return {
            'R': self.sheet['Q27'].value, 'HR': self.sheet['R27'].value, 'RBI': self.sheet['S27'].value, 'SB': self.sheet['T27'].value,
            'OBP': self.sheet['U27'].value, 'SLG': self.sheet['V27'].value
        }