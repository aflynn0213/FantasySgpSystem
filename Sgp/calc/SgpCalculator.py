from typing import List, Tuple, Dict, Optional
import pandas as pd
from Sgp.loaders import IProjectionLoader
from Sgp.params.SgpParams import SgpParams
from Sgp.processor.TeamProcessor import TeamProcessor
import numpy as np
from .ISgpCalculator import ISgpCalculator


class SgpCalculator(ISgpCalculator):

    def __init__(self,
                 data: IProjectionLoader,
                 params: SgpParams,
                 teamProcessor: TeamProcessor,
                 role: str):

        self.weeks = data["weeks"]
        self.stats = data["stats"].copy()
        self.replacement_levels: Dict[str, float] = params.replacement_levels
        self.cat_stds: Dict[str, float] = params.cat_stds
        self.team_value: Dict[Tuple(str,str), float] = teamProcessor.team_value
        self.team_opportunities: Dict[str, float] = teamProcessor.team_opportunities
        self.role = role

    def cat_calc_sgp(self,categories: List[str]):
        factor = self.weeks / 26
        replacement = pd.Series(self.replacement_levels).reindex(categories)
        print(replacement)
        stds = pd.Series(self.cat_stds).reindex(categories)
        
        # Calculate SGP for counting stats
        print(self.stats.columns)
        if ("pitching" == self.role):
            self.stats['SV_HLD'] = self.stats['SV'] + self.stats['HLD']
        sgp = self.stats[categories].sub(factor*replacement,axis=1).div(factor*stds,axis=1)
        sgp.columns = [f'SGP_{cat}' for cat in categories] 
        return sgp

    def rate_calc_sgp(self,categories: List[tuple]):
        factor = self.weeks / 26
        
        result = {}        
        
        if ("hitting" == self.role):
            self.stats["PA_SH"] = self.stats["PA"] - self.stats["SH"]
            #factor is point in season normalizer
            result = { f'SGP_{cat}': (  (factor*self.team_value[(cat,opp)] + self.stats[cat]*self.stats[opp] ) 
                                     / (factor*self.team_opportunities[opp]+self.stats[opp]) - self.replacement_levels[cat]  ) 
                                    / self.cat_stds[f'{cat}'] for cat,opp in categories }
        
        elif("pitching" == self.role):
            # ERA,IP WHIP,IP K/BB,BB
            multiple = 1
            for cat,opps in categories:
                if(cat=='ERA'):
                    val = 9*self.stats['ER']
                    multiple = 9
                elif(cat=='WHIP'):
                    val = self.stats['H']+self.stats['BB']
                    multiple = 1
                elif(cat=="K/BB"):
                    multiple = 1
                    val = self.stats['SO']
                else:
                    raise NotImplementedError("Category outside of the league's pitching categories used as input to rate_calc_sgp")
            
                #self.team_value => ERs, H+BBs, Ks team totals minus average player
                #factor is point in season normalizer (i.e. halfway through season we want to
                # take half of the replacement teams expected output for the season)
                #multiple is 9 exclusively for ERA => ER = ERA*IP/9
                #team_val_wo_average_player = ER*9
                team_val_wo_average_player = factor*multiple*self.team_value.get((cat, opps), 0)

                #self.team_opportunities => IP, IP, BB team totals minus average
                #factor is point in season normalizer
                #total_opps adds in player in questions total to team average to get player influence on team
                total_opps = factor*self.team_opportunities[opps] + self.stats[opps]
                
                #ERA CALCULATION: factor*9*(REPLACEMENT TEAM - 1 REPLACEMENT PLAYER EXPECTED ERS) + 9*Pitcher's ERs /
                # (factor*(REPLACEMENT TEAM - 1 REPLACEMENT PLAYER EXPECTED IPs)+Pitcher's IPs) - Replacement ERA
                #(ER*9 + ER*9) / IP = ERA for the first quotient which is then subtracted by an ERA # 
                result[f'SGP_{cat}'] = ((team_val_wo_average_player+val)/(total_opps) - self.replacement_levels[cat])/self.cat_stds[cat]
        
        return pd.DataFrame(result)