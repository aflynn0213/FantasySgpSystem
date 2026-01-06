from dataclasses import replace
from distutils.command.config import config
from multiprocessing import process
import os
from sqlite3 import DataError
from typing import Dict
import yaml
import pandas as pd

from utils.common_utils import (get_repo_root, 
                                load_config,
                                parse_hitter_config_categories, 
                                parse_pitcher_config_categories)

class TeamProcessor():
    def __init__(self, data, params):
        self.__data = data
        self.__params = params
        self.team_opportunities:Dict[str,float] = {}
        self.team_value:Dict[str,float] = {}
        self.__buildProcessor()

    def __buildProcessor(self)->Dict:
        config = load_config(os.path.join(get_repo_root(), "config.yml"))
        if(self.__data["player_type"]=="hitting"):
            self.__categories, self.__rate_opps = parse_hitter_config_categories(config) 
        elif(self.__data["player_type"]=="pitching"):
            self.__categories, self.__rate_opps = parse_pitcher_config_categories(config)
        else:
            raise DataError("Projection Data Loader contains invalid Player Type")
        
        self.__num_teams = config["defaults"]["num_teams"]

        self.__handle_hitting(config) if self.__data["player_type"] == "hitting" else self.__handle_pitching(config) 
        
    def __handle_pitching(self,config):
        num_starters = config["defaults"]["num_starters"]
        num_relievers = config["defaults"]["num_relievers"]
        team_pitchers_num = num_starters+num_relievers
        league_pitchers_num = self.__num_teams*(team_pitchers_num)

        if (self.__data["ip_adj"] == None or self.__data["period"] != "pre" ):
            temp_df = self.__data["auc_calc"].copy()
        else:
            temp_sheet = self.__data["ip_adj"]
            temp_df = pd.read_excel(f"auction_calculator_exports/auc_calc_pitching_{temp_sheet}.xlsx",sheet_name=0)
        
        multiplier = 1
        
        for cat,val in self.__rate_opps: 
            if val == 'IP':
                avg_opps = temp_df['IP'].head(league_pitchers_num).mean()
                multiplier = 9 if cat == 'ERA' else 1       
            elif val == 'BB':
                avg_opps = self.__params.replacement_levels['SO']/self.__params.replacement_levels['K/BB']
                
            avg_team_opps_wo_replacement = avg_opps*(team_pitchers_num-1)
            avg_team_value_wo_replacement = avg_team_opps_wo_replacement*self.__params.replacement_levels[cat]/multiplier

            self.team_opportunities[val] = avg_team_opps_wo_replacement
            self.team_value[(cat,val)] = avg_team_value_wo_replacement

    def __handle_hitting(self,config):
        num_bats = config["defaults"]["num_bats"]
        num_players = self.__num_teams*num_bats
        
        temp_auc_calc = self.__data["auc_calc"].copy()
        temp_proj_read = self.__data["proj_read"].copy()
        temp_auc_calc = temp_auc_calc.merge(temp_proj_read[['PlayerId','SH','AB']],
                                            on='PlayerId',
                                            how='left')
        
        temp_auc_calc['PA_SH'] = temp_auc_calc['PA'] - temp_auc_calc['SH']

        for cat,val in self.__rate_opps:
            avg_opps = temp_auc_calc[val].head(num_players).mean()                
            avg_team_opps_wo_replacement = avg_opps*(num_bats-1)
            avg_team_value_wo_replacement = avg_team_opps_wo_replacement*self.__params.replacement_levels[cat]

            self.team_opportunities[val] = avg_team_opps_wo_replacement
            self.team_value[(cat,val)] = avg_team_value_wo_replacement
