import argparse
import pandas as pd
import numpy as np
import os

from openpyxl import load_workbook
from openpyxl.styles import Font

from Sgp.SgpHitters import SgpHitters
from Sgp.SgpPitchers import SgpPitchers
from utils.inseason_export_sgp import export_sgp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGP Processing Script")
    parser.add_argument("-b", "--hitter_proj", 
                        type=str, 
                        required=True, 
                        help="Projection system for hitters (e.g., atc), and time period Ex: atc_pre, atc_td (to date), atc_ros")
    parser.add_argument("-p", "--pitcher_proj", type=str, required=True, help="Projection system for pitchers (e.g., atc)")
    parser.add_argument("-sb", "--sb_included", type=bool, default=False, help="(Optional) Whether or not to include stolen bases")
    parser.add_argument("-wk", "--weeks_completed", type=int, default=26, help="Number of weeks completed in the season")
    
    args = parser.parse_args()
    
    # PUT CODE INTO SET WEEKS TO 26 IF '_pre' is the suffix of hitter_proj
    #----------------------------------------------------------------------
    
    #----------------------------------------------------------------------
    
    sgp_hit = SgpHitters(proj=args.hitter_proj,sb_included=args.sb_included,weeks=args.weeks_completed) 
    df_hit = sgp_hit.sgp_df.copy()
    
    sgp_pit = SgpPitchers(proj=args.pitcher_proj,weeks=args.weeks_completed) 
    df_pit = sgp_pit.sgp_df.copy()
    
    print(f'{args.weeks_completed} weeks completed' )
    cols_included = list(range(0,6))
    if (not args.sb_included):
        cols_included.remove(3)
        df_hit['Total_SGP_wSB'] = df_hit.iloc[:,0:6].sum(axis=1)
    else: 
        df_hit['Total_SGP_wSB'] = np.nan
        
    df_hit['Total_SGP'] = df_hit.iloc[:, cols_included].sum(axis=1)
    df_hit = df_hit.sort_values(by="Total_SGP", ascending=False)
    
    df_pit['Total_SGP'] = df_pit.iloc[:, 0:6].sum(axis=1)
    df_pit = df_pit.sort_values(by="Total_SGP", ascending=False)
    
    print("Exporting SGP Results...")
    file_name_hit = export_sgp(df_hit,args.sb_included,args.hitter_proj.split('_')[1],"hitting")
    file_name_pit = export_sgp(df_pit,False,args.pitcher_proj.split('_')[1],"pitching")
    
    print(f"[FINISHED] Exported SGP Hitter Results to {file_name_hit}")
    print(f"[FINISHED] Exported SGP Pitcher Results to {file_name_pit}")
    
