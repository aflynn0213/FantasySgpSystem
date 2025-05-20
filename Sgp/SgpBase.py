import pandas as pd
from openpyxl import load_workbook
import string


NUM_TEAMS = 12
NUM_BATS = 13
NUM_STARTERS = 9
NUM_RELIEVERS = 3

class SgpBase:
    def __init__(self, proj, file_prefix):
        """
        Base class for SGP processing.
        :param proj: Projection system (e.g., "atc", "zips").
        :param file_prefix: "hitting" or "pitching" (determines file names).
        :param sheet_name: Sheet name in the Excel file ("3YR RUNNING AVG SGP").
        """
        print(f"[*] Initializing Sgp {file_prefix} for projections: {proj}")

        self.proj = proj.split()[0].lower()
        print("[*] Loading projection data...")
        self.stats = pd.read_excel(f'projections/fangraphs_{file_prefix}_{self.proj}.xlsx', sheet_name=0)
        self.stats = self.stats.drop_duplicates(subset=['Name', 'PlayerId'])
        
        print("[*] Loading auction calculator data...")
        self.auc_calc = pd.read_excel(f"auction_calculator_exports/auc_calc_{file_prefix}_{self.proj}.xlsx", sheet_name=0)

        # Load league-wide replacement levels & category standard deviations
        self.wb = load_workbook("leaguehistory.xlsx", data_only=True)
        self.sheet = self.wb["Sheet1"]

        print(f"[✔] SgpBase initialized for {file_prefix}.")

    def cat_calc_sgp(self,projection:string):
        return (self.stats[projection] - self.replacement_levels[projection]) / self.cat_stds[projection]
    
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

