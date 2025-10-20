from abc import ABC
from typing import List, Dict, Optional, Any
import pandas as pd

from google.cloud import storage

from utils.common_utils import download_from_bucket, get_repo_root
from utils.docker_running import is_running_in_docker

import os

from loaders import IProjectionLoader, ILeagueDataLoader
from params.SgpParams import SgpParams
from calc import ISgpCalculator

NUM_TEAMS = 12
NUM_BATS = 13
NUM_STARTERS = 9
NUM_RELIEVERS = 3

class SgpBase(ABC):
    def __init__(self,
                 data: IProjectionLoader = None,
                 workbook_loader: ILeagueDataLoader = None,
                 league_params: SgpParams = None,
                 sgp_calculator: ISgpCalculator = None):

        self.proj_data = data
        self.player_type = player_type
        self.weeks = weeks
        self._projection_loader = projection_loader
        self._workbook_loader = workbook_loader
        self._league_params = league_params
        self._sgp_calculator = sgp_calculator

        self.proj_read: pd.DataFrame = pd.DataFrame()
        self.stats: pd.DataFrame = pd.DataFrame()
        self.auc_calc: pd.DataFrame = pd.DataFrame()
        self.replacement_levels: Dict[str,float] = {}
        self.cat_stds: Dict[str,float] = {}
        self.team_value: Dict[str,float] = {}
        self.team_opportunities: Dict[str,float] = {}
        self.sgp_df: pd.DataFrame = pd.DataFrame()

        self._load_data()
        self._load_league_params()
        
        print(f"Initializing Sgp {player_type} for projections: {proj}")
        self.proj,self.period = proj.split('_')
        
        # === Download from GCS if running in Docker ===
        if is_running_in_docker():
            print("Downloading data from GCS...")
            download_from_bucket("fantasysgpsystem-outputs", 
                                 f"projections/fangraphs_{player_type}_{self.proj}.xlsx", 
                                 f"projections/fangraphs_{player_type}_{self.proj}.xlsx")
            download_from_bucket("fantasysgpsystem-outputs", 
                                 f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}.xlsx", 
                                 f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}.xlsx")
            if self.period == 'td':
                download_from_bucket("fantasysgpsystem-outputs", 
                                     f"stats/fangraphs_{player_type}_stats.xlsx", 
                                     f"stats/fangraphs_{player_type}_stats.xlsx")
            elif self.period == 'ros':
                download_from_bucket("fantasysgpsystem-outputs", 
                                     f"ros/fangraphs_{player_type}_{self.proj}_ros.xlsx", 
                                     f"ros/fangraphs_{player_type}_{self.proj}_ros.xlsx")    
    
        print("Loading projection data...")
        if self.period == 'pre':
            self.weeks = 26
            self.proj_read = pd.read_excel(f'projections/fangraphs_{player_type}_{self.proj}.xlsx', sheet_name=0)
            self.stats = self.proj_read.drop_duplicates(subset=['Name', 'PlayerId'])

            print("Loading auction calculator data...")
            self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}.xlsx", sheet_name=0)

        elif self.period == 'td':
            self.weeks = weeks
            self.proj_read = pd.read_excel(f'projections/fangraphs_{player_type}_{self.proj}.xlsx', sheet_name=0)
            self.stats = pd.read_excel(f"stats/fangraphs_{player_type}_stats.xlsx",sheet_name=0)

            print("Loading auction calculator data...")
            self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}.xlsx", sheet_name=0)

        elif self.period == 'ros':
            self.weeks = 26 - weeks
            self.stats = pd.read_excel(f"ros/fangraphs_{player_type}_{self.proj}_ros.xlsx",sheet_name=0)
            self.proj_read = self.stats.copy()

            print("Loading auction calculator data...")
            self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}_ros.xlsx", sheet_name=0)

        self.stats["PlayerId"] = self.stats["PlayerId"].astype(str) 
        self.proj_read['PlayerId'] = self.proj_read['PlayerId'].astype(str)
        self.auc_calc["PlayerId"] = self.auc_calc["PlayerId"].astype(str)

        # Load league-wide replacement levels & category standard deviations
        self.wb = load_workbook(os.path.join(get_repo_root(), "included", "leaguehistory.xlsx"), data_only=True)
        self.sheet = self.wb["Sheet1"]

        print(f"[FINISHED] SgpBase initialized for {player_type}.")
    
    def _process_sgp(self):
        """Processes SGP for counting and rate stats (to be overridden in subclasses)."""
        raise NotImplementedError("Subclasses must implement process_sgp()")

    def _team_rate_values_processing(self, ip_adj=None):
        """Processes team rate values for advanced SGP calculations (to be overridden in subclasses)."""
        raise NotImplementedError("Subclasses must implement team_rate_values_processing()")

    def _load_replacement_levels(self):
        """Loads replacement level values from the Excel sheet."""
        return {}

    def _load_category_stds(self):
        """Loads category standard deviations from the Excel sheet."""
        return {}

