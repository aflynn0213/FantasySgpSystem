import pandas as pd
from openpyxl import load_workbook
import string
from google.cloud import storage

from utils.common_utils import download_from_bucket
from utils.docker_running import is_running_in_docker

NUM_TEAMS = 12
NUM_BATS = 13
NUM_STARTERS = 9
NUM_RELIEVERS = 3

class SgpBase:
    def __init__(self, proj, player_type, weeks=26):
        """
        Base class for SGP processing.
        :param proj: Projection system (e.g., "atc", "zips").
        :param player_type: "hitting" or "pitching" (also determines file names).
        :param weeks: Weeks into the season to determine SGP proportion (26 default for full season projections).
        """
        
        print(f"[*] Initializing Sgp {player_type} for projections: {proj}")
        self.proj,self.period = proj.split('_')
        
        # === Download from GCS if running in Docker ===
        if is_running_in_docker():
            print("[*] Downloading data from GCS...")
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
    
        print("[*] Loading projection data...")
        if self.period == 'pre':
            self.weeks = 26
            self.proj_read = pd.read_excel(f'projections/fangraphs_{player_type}_{self.proj}.xlsx', sheet_name=0)
            self.stats = self.proj_read.drop_duplicates(subset=['Name', 'PlayerId'])

            print("[*] Loading auction calculator data...")
            self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}.xlsx", sheet_name=0)

        elif self.period == 'td':
            self.weeks = weeks
            self.proj_read = pd.read_excel(f'projections/fangraphs_{player_type}_{self.proj}.xlsx', sheet_name=0)
            self.stats = pd.read_excel(f"stats/fangraphs_{player_type}_stats.xlsx",sheet_name=0)

            print("[*] Loading auction calculator data...")
            self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}.xlsx", sheet_name=0)

        elif self.period == 'ros':
            self.weeks = 26 - weeks
            self.stats = pd.read_excel(f"ros/fangraphs_{player_type}_{self.proj}_ros.xlsx",sheet_name=0)
            self.proj_read = self.stats.copy()

            print("[*] Loading auction calculator data...")
            self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{player_type}_{self.proj}_ros.xlsx", sheet_name=0)

        self.stats["PlayerId"] = self.stats["PlayerId"].astype(str) 
        self.proj_read['PlayerId'] = self.proj_read['PlayerId'].astype(str)
        self.auc_calc["PlayerId"] = self.auc_calc["PlayerId"].astype(str)

        # Load league-wide replacement levels & category standard deviations
        self.wb = load_workbook("included/leaguehistory.xlsx", data_only=True)
        self.sheet = self.wb["Sheet1"]

        print(f"[✔] SgpBase initialized for {player_type}.")
    
    def cat_calc_sgp(self,category:string):
        return (self.stats[category] - (self.weeks/26)*self.replacement_levels[category]) / ((self.weeks/26)*self.cat_stds[category])
    
    def rate_calc_sgp(self,cat:string,opportunities:string):
        """Processes rate stats to determine SGPs""" 
        raise NotImplementedError("Subclasses must implement rate_calc_sgp()")
    
    def process_sgp(self):
        """Processes SGP for counting and rate stats (to be overridden in subclasses)."""
        raise NotImplementedError("Subclasses must implement process_sgp()")

    def team_rate_values_processing(self, ip_adj=None):
        """Processes team rate values for advanced SGP calculations (to be overridden in subclasses)."""
        raise NotImplementedError("Subclasses must implement team_rate_values_processing()")

    def load_replacement_levels(self):
        """Loads replacement level values from the Excel sheet."""
        return {}

    def load_category_stds(self):
        """Loads category standard deviations from the Excel sheet."""
        return {}

