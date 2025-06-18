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
        
        print("[*] Loading replacement levels and category standard deviations...")
        self.replacement_levels = self.load_replacement_levels()
        self.cat_stds = self.load_category_stds()
        
        self.team_opportunities = {}
        self.team_value = {}
 
        self.team_rate_values_processing()
        
        print("[*] Processing hitters SGP...")
        self.process_sgp()
        
        self.sgp_df['PA'] = self.stats['PA'] - self.stats['SH']
        self.sgp_df[['Name', 'PlayerId']] = self.stats[['Name', 'PlayerId']]
        self.sgp_df.set_index(['Name','PlayerId'], inplace=True)
        
        print(f"[✔] SgpHitters initialized")

    def rate_calc_sgp(self,cat:string,opportunities:string):
        if opportunities == 'AB':
            team_cat = 'SLG_AB'
            player_opps = self.stats[opportunities]
        elif opportunities == 'PA':
            team_cat = 'OBP_PA'
            player_opps = self.stats[opportunities] - self.stats['SH']

        player_val = self.stats[cat]*player_opps
        team_val_wo_average_player = self.team_value[team_cat]
        total_opps = (self.weeks/26)*self.team_opportunities[opportunities] + player_opps

        return (((self.weeks/26)*team_val_wo_average_player+player_val)/(total_opps) - self.replacement_levels[cat])/self.cat_stds[cat]

    def process_sgp(self):
        print("[*] Calculating SGP for counting stats (R, HR, RBI, SB)...")
        self.sgp_df = pd.DataFrame()
        for cat in ['R', 'HR', 'RBI', 'SB']:
            self.sgp_df[f'SGP_{cat}'] = self.cat_calc_sgp(cat)
        
        print("[*] Calculating SGP for rate stats (OBP, SLUG)...")
        for cat, opps in [('OBP', 'PA'), ('SLG', 'AB')]:
            self.sgp_df[f'SGP_{cat}'] = self.rate_calc_sgp(cat,opps)
        
        print("[✔] Hitters SGP calculation complete.")
        
    def team_rate_values_processing(self,ip_adj=None):
        temp_df = self.auc_calc.copy()
        temp_df = temp_df.merge(self.proj_read[['PlayerId','SH','AB']],
                                on='PlayerId',
                                how='left')
        
        for cat,val,cat_val in [('OBP','PA','OBP_PA'), ('SLG','AB','SLG_AB')]: 
            if val == 'PA':
                temp_df['PA_SH'] = temp_df['PA'] - temp_df['SH'] 
                avg_opps = temp_df['PA_SH'].head(NUM_BATS*NUM_TEAMS).mean()
            elif val == 'AB':
                avg_opps = temp_df['AB'].head(NUM_BATS*NUM_TEAMS).mean()
                
            avg_team_opps_wo_replacement = avg_opps*(NUM_BATS-1)
            avg_team_value_wo_replacement = avg_team_opps_wo_replacement*self.replacement_levels[cat]

            self.team_opportunities[val] = avg_team_opps_wo_replacement
            self.team_value[cat_val] = avg_team_value_wo_replacement
            
    def load_replacement_levels(self):
        return {
            'R': self.sheet['Q26'].value, 'HR': self.sheet['R26'].value, 'RBI': self.sheet['S26'].value, 
            'SB': self.sheet['T26'].value, 'OBP': self.sheet['U26'].value, 'SLG': self.sheet['V26'].value
        }
        
    def load_category_stds(self):
        return {
            'R': self.sheet['Q27'].value, 'HR': self.sheet['R27'].value, 'RBI': self.sheet['S27'].value, 'SB': self.sheet['T27'].value,
            'OBP': self.sheet['U27'].value, 'SLG': self.sheet['V27'].value
        }