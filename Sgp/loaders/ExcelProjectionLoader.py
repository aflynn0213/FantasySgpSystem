from typing import Dict, Any
import pandas as pd
import os
from utils.common_utils import get_repo_root

from .IProjectionLoader import IProjectionLoader

class ExcelProjectionLoader(IProjectionLoader):
    """
    Loader class that reads local Excel files using pandas.read_excel.
    """
    def __init__(self, base_dir: str = None, weeks: int = 26):
        self.base_dir = base_dir if base_dir is not None else get_repo_root()
        self.weeks = weeks

    def load(self, proj: str, player_type: str, ip_adj: str = None) -> Dict[str, Any]:
        proj_base , period = proj.split('_')
        period = period.lower()

        data = {}
        data["projection"] = proj_base
        data['player_type'] = player_type
        data['ip_adj'] = ip_adj

        print("Loading projection data...")
        if period == 'pre':
            data["weeks"] = 26
            data["proj_read"] = pd.read_excel(f'projections/fangraphs_{player_type}_{proj_base}.xlsx', sheet_name=0)
            data["stats"] = data["proj_read"].drop_duplicates(subset=['Name', 'PlayerId'])

            print("Loading auction calculator data...")
            data["auc_calc"] = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{proj_base}.xlsx", sheet_name=0)

        elif period == 'td':
            data["weeks"] = self.weeks
            data["proj_read"] = pd.read_excel(f'projections/fangraphs_{player_type}_{proj_base}.xlsx', sheet_name=0)
            data["stats"] = pd.read_excel(f"stats/fangraphs_{player_type}_stats.xlsx",sheet_name=0)

            print("Loading auction calculator data...")
            data["auc_calc"] = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{proj_base}.xlsx", sheet_name=0)

        elif period == 'ros':
            data["weeks"] = 26 - self.weeks
            data["stats"] = pd.read_excel(f"ros/fangraphs_{player_type}_{proj_base}_ros.xlsx",sheet_name=0)
            data["proj_read"] = data["stats"].copy()

            print("Loading auction calculator data...")
            #Unique auc_calc since this one uses proj ({proj_base}_ros)
            #Use this for playing time consideration averages for the rest of the season expectations
            data["auc_calc"] = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{proj}.xlsx", sheet_name=0)
            
        elif period == 'eoy':
            data["weeks"] = 26
            data["stats"] = pd.read_excel(f"stats/fangraphs_{player_type}_stats.xlsx",sheet_name=0)
            data["proj_read"] = data["stats"].copy()

            print("Loading auction calculator data...")
            data["auc_calc"] = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{period}.xlsx", sheet_name=0)

        else:
            valid_periods = ['pre', 'td', 'ros', 'eoy']
            raise KeyError(
                f"Unrecognized period '{period}' parsed from projection '{proj}'. "
                f"Expected format is '{{proj_base}}_{{period}}' where period is one of {valid_periods}. "
                f"e.g. 'atc_pre', 'oopsy_pre', 'atc_td'"
            )

        for key in ['proj_read','stats','auc_calc']:
            if key in data and 'PlayerId' in data[key].columns:
                data[key]['PlayerId'] = data[key]['PlayerId'].astype(str)

        print(f"[FINISHED] SgpBase initialized for {player_type}.")

        data['period'] = period
        return data
