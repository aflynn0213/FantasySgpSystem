#utils/export_sgp.py
import pandas as pd
import os

export_cols = ['PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP']
index_cols = ['Name','PlayerId']

SAVE_FOLDER = os.path.join(os.getcwd(), "../stats")
    
def export_sgp(df,sb):
    column_missing = [col for col in export_cols if col not in df.columns]
    index_missing = [index for index in index_cols if index not in list(df.index.names)]
    if column_missing:
        raise ValueError(f"{column_missing} Missing From DataFrame")
    elif index_missing:
        raise ValueError(f"{index_missing} Missing From DataFrame")            

    os.makedirs(SAVE_FOLDER,exist_ok=True)
    
    sb_string = "_sb_included" if sb else ""
    file_name = f"stats/SGP_Results_{sb_string}.xlsx"
    df.reset_index(inplace=True)
    
    with pd.ExcelWriter(file_name) as writer:
        df[['Name', 'PlayerId', 'PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP']].to_excel(writer, sheet_name='Hitters', index=False)
    
    return file_name
        
        