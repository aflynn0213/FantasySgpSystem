from typing import List
import pandas as pd
import numpy as np
import string
from Sgp.SgpBase import SgpBase

NUM_TEAMS = 12
NUM_STARTERS = 9
NUM_RELIEVERS = 3

class SgpPitchers(SgpBase):
    def __init__(self, proj, ip_adj=None):
        self.ip_adj = ip_adj
        super().__init__(proj, "pitching")
        
        if (ip_adj):
            print("Adjusting pitcher playing time...")
            self.__adjust_playing_time(ip_adj)
            
        print("Loading replacement levels and category standard deviations...")
        self.replacement_levels = self._load_replacement_levels()
        self.cat_stds = self._load_category_stds()
        
        self.team_opportunities = {}
        self.team_value = {}
        
        print("Loading auction calculator data for pitchers...")
        self._team_rate_values_processing(ip_adj)
        
        print("Processing pitchers SGP...")
        self._process_sgp()
        
        self.sgp_df['IP'] = self.stats['IP']
        self.sgp_df['GS'] = self.stats['GS']
        
        self.sgp_df[['Name', 'PlayerId']] = self.stats[['Name', 'PlayerId']]
        self.sgp_df.set_index(['Name','PlayerId'], inplace=True)
        
        print(f"***SgpPitchers initialized***")

    def _rate_calc_sgp(self,categories: List[tuple]):
        result = {}
        for cat,opps in categories:
            if(cat=='ERA'):
                val = 9*self.stats['ER']
            elif(cat=='WHIP'):
                val = self.stats['H']+self.stats['BB']
            elif(cat=="K/BB"):
                val = self.stats['SO']
            else:
                raise NotImplementedError("Category outside of the league's pitching categories used as input to rate_calc_sgp")
            
            multiplier = 1
            if (cat == 'ERA'):
                multiplier = 9
                
            team_val_wo_average_player = multiplier*self.team_value[cat]
            total_opps = self.team_opportunities[opps] + self.stats[opps]
            
            result[f'SGP_{cat}'] = ((team_val_wo_average_player+val)/(total_opps) - self.replacement_levels[cat])/self.cat_stds[cat]

        return pd.DataFrame(result)

    def _process_sgp(self):
        print("Calculating SGP for counting stats (SO, QS, SV_HLD)...")
        counting_stats = ['SO', 'QS', 'SV_HLD']
        self.stats['SV_HLD'] = self.stats['SV'] + self.stats['HLD']
        self.sgp_df = self.cat_calc_sgp(counting_stats)
            
        print("Calculating SGP for rate stats (ERA, WHIP, K/BB)...")
        rate_stats = [('ERA','IP'), ('WHIP', 'IP'), ('K/BB', 'BB')]
        self.sgp_df = pd.concat([self.sgp_df,self.rate_calc_sgp(rate_stats)])
 
        print("***Pitchers SGP calculation complete.***")
        
    def _team_rate_values_processing(self,ip_adj):
        auc_sheet = self.proj if ip_adj == None else ip_adj
        temp_df = pd.read_excel(f"auction_calculator_exports/auc_calc_pitching_{auc_sheet}.xlsx",sheet_name=0)
        
        multiplier = 1
        
        for cat,val in [('ERA','IP'), ('WHIP','IP'), ('K/BB', 'BB')]: 
            if val == 'IP':
                avg_opps = temp_df['IP'].head((NUM_STARTERS+NUM_RELIEVERS)*NUM_TEAMS).mean()
                multiplier = 9 if cat == 'ERA' else 1       
            elif val == 'BB':
                avg_opps = self.replacement_levels['SO']/self.replacement_levels['K/BB']
                
            avg_team_opps_wo_replacement = avg_opps*(NUM_STARTERS+NUM_RELIEVERS-1)
            avg_team_value_wo_replacement = avg_team_opps_wo_replacement*self.replacement_levels[cat]/multiplier

            self.team_opportunities[val] = avg_team_opps_wo_replacement
            self.team_value[cat] = avg_team_value_wo_replacement
            
    def _load_replacement_levels(self):
        return {
            'SO': self.sheet['W26'].value,'QS': self.sheet['X26'].value, 'SV_HLD': self.sheet['AB26'].value, 
            'ERA': self.sheet['Y26'].value,'WHIP': self.sheet['Z26'].value, 'K/BB': self.sheet['AA26'].value
        }
        
    def _load_category_stds(self):
        return {
            'SO': self.sheet['W27'].value,'QS': self.sheet['X27'].value, 'SV_HLD': self.sheet['AB27'].value, 
            'ERA': self.sheet['Y27'].value, 'WHIP': self.sheet['Z27'].value, 'K/BB': self.sheet['AA27'].value
        }
            
    def __adjust_playing_time(self,ip_adj):
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
