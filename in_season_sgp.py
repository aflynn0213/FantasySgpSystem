import argparse
import pandas as pd
import numpy as np
import os

from openpyxl import load_workbook
from openpyxl.styles import Font

from Sgp.SgpHitters import SgpHitters
from utils.inseason_export_sgp import export_sgp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGP Processing Script")
    parser.add_argument("-b", "--hitter_proj", type=str, required=True, help="Projection system for hitters (e.g., atc)")
    parser.add_argument("-sb", "--sb_included", type=bool, default=False, help="(Optional) Whether or not to include stolen bases")
    parser.add_argument("-wk", "--weeks_completed", type=int, default=26, help="Number of weeks completed in the season")
    args = parser.parse_args()
    
    sgp_hit = SgpHitters(proj=args.hitter_proj,sb_included=args.sb_included,weeks=args.weeks_completed) 
    df = sgp_hit.sgp_df.copy()
    
    cols_included = list(range(0,6))
    if (not args.sb_included):
        cols_included.remove(3)
        df['Total_SGP_wSB'] = df.iloc[:,0:6].sum(axis=1)
    else: 
        df['Total_SGP_wSB'] = np.nan
        
    df['Total_SGP'] = df.iloc[:, cols_included].sum(axis=1)
    df = df.sort_values(by="Total_SGP", ascending=False)
    
    print("[*] Exporting SGP Results...")
    file_name = export_sgp(df,args.sb_included)
    
    print(f"[✔] Exported SGP Results to {file_name}")
    
