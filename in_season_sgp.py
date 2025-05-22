import argparse
import pandas as pd
import numpy as np
import os

from openpyxl import load_workbook
from openpyxl.styles import Font

from Sgp.SgpHitters import SgpHitters

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGP Processing Script")
    parser.add_argument("-b", "--hitter_proj", type=str, required=True, help="Projection system for hitters (e.g., atc)")
    parser.add_argument("-sb", "--sb_included", type=bool, default=False, help="(Optional) Whether or not to include stolen bases")
    parser.add_argument("-wk", "--weeks_completed", type=int, default=26, help="Number of weeks completed in the season")
    args = parser.parse_args()
    
    sgp_hit = SgpHitters(proj=args.hitter_proj,sb_included=args.sb_included,weeks=args.weeks_completed) 
    df = sgp_hit.sgp_df.copy()
    
    cols_included = list(range(0,6))
    if (args.sb_included):
        cols_included.remove(3)
        df['Total_SGP_wSB'] = df.iloc[:,0:6].sum(axis=1)
    df['Total_SGP'] = df.iloc[:, cols_included].sum(axis=1)
    df = df.sort_values(by="Total_SGP", ascending=False)
    print("[*] Exporting SGP Results...")
        
    SAVE_FOLDER = os.path.join(os.getcwd(), "stats")
    os.makedirs(SAVE_FOLDER,exist_ok=True)
    
    sb_string = "_sb_included" if args.sb_included else ""
    file_name = f"stats/SGP_Results_{sb_string}.xlsx"
    df.reset_index(inplace=True)
    with pd.ExcelWriter(file_name) as writer:
        df[['Name', 'PlayerId', 'PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP']].to_excel(writer, sheet_name='Hitters', index=False)
    
    print(f"[✔] Exported SGP Results to {file_name}")
    
