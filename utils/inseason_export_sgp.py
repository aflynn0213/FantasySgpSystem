#utils/export_sgp.py
from google.cloud import storage
import os
import pandas as pd

from utils.common_utils import upload_to_bucket

export_cols = ['PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP']
index_cols = ['Name','PlayerId']

    
def export_sgp(df,sb,dir):
    if 'td' == dir :
        save_loc = "stats"
    elif 'ros' == dir:
        save_loc = "ros"
    SAVE_FOLDER = os.path.join(os.getcwd(), save_loc)

    column_missing = [col for col in export_cols if col not in df.columns]
    index_missing = [index for index in index_cols if index not in list(df.index.names)]
    
    if column_missing:
        raise ValueError(f"{column_missing} Missing From DataFrame")
    elif index_missing:
        raise ValueError(f"{index_missing} Missing From DataFrame")            

    os.makedirs(SAVE_FOLDER,exist_ok=True)
    
    sb_string = "_sb_included" if sb else ""
    file_name = f"SGP_Results_{dir}_{sb_string}.xlsx"
    full_path = os.path.join(SAVE_FOLDER, file_name)
    
    print(full_path)
    print(SAVE_FOLDER)
    
    df.reset_index(inplace=True)
    with pd.ExcelWriter(full_path) as writer:
        df[['Name', 'PlayerId', 'PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP']].to_excel(writer, sheet_name='Hitters', index=False)
    
    gcs_blob_path = f"{save_loc}/{file_name}"
    upload_to_bucket(full_path, gcs_blob_path)

        
    return file_name
        
        