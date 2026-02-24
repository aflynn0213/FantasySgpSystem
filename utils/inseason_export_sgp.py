#utils/export_sgp.py
from google.cloud import storage
import os
import pandas as pd

from utils.common_utils import upload_to_bucket, get_repo_root

hitter_export_cols = ['PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP']
pitcher_export_cols = ['IP', 'GS', 'SGP_SO', 'SGP_QS', 'SGP_SV_HLD', 'SGP_ERA', 'SGP_WHIP', 'SGP_K/BB', 'Total_SGP']
combined_export_cols = ['Total_SGP', 'RL', 'VAR']
index_cols = ['Name','PlayerId']

    
def export_sgp(df,sb,dir,player_type):

    SAVE_FOLDER = os.path.join(get_repo_root(), "results")
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    if player_type == "hitting":
        export_cols = hitter_export_cols
    elif player_type == "pitching":
        export_cols = pitcher_export_cols
    elif player_type == "combined":
        export_cols = combined_export_cols
    else:
        export_cols = []
    
    column_missing = [col for col in export_cols if col not in df.columns]
    index_missing = [index for index in index_cols if index not in df.columns]

    if column_missing:
        raise ValueError(f"{column_missing} Missing From DataFrame")
    elif index_missing:
        raise ValueError(f"{index_missing} Missing From DataFrame")            

    os.makedirs(SAVE_FOLDER,exist_ok=True)
    
    sb_string = "_sb_included" if sb else ""
    file_name = f"SGP_Results_{dir}_{player_type}{sb_string}.xlsx"
    full_path = os.path.join(SAVE_FOLDER, file_name)
    
    print(full_path)
    print(SAVE_FOLDER)
    
    df.reset_index(inplace=True)
    export_cols = index_cols + export_cols
    with pd.ExcelWriter(full_path) as writer:
        df[export_cols].to_excel(writer, sheet_name=player_type, index=False)
    
    gcs_blob_path = f"results/{file_name}"
    upload_to_bucket(full_path, gcs_blob_path)

        
    return file_name
        
        
