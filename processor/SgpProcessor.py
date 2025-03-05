import pandas as pd
import numpy as np
import os

class SgpProcessor:
    def __init__(self, sgp_hitters, sgp_pitchers):

        print("[*] Initializing SGP Processor...")
        
        temp_hitters = sgp_hitters.sgp_df.copy()
        temp_pitchers = sgp_pitchers.sgp_df.copy()
        self.suffix = f"{sgp_hitters.proj}_{sgp_pitchers.proj}"

        # Prepare data immediately and store results
        self.hitters_df = self.prepare_data(temp_hitters, 'Hitter')
        self.pitchers_df = self.prepare_data(temp_pitchers, 'Pitcher')

        # Combine for final rankings
        self.combined_df = pd.concat([
            self.hitters_df[['Name', 'PlayerId', 'Total_SGP', 'RL', 'VAR']],
            self.pitchers_df[['Name', 'PlayerId', 'Total_SGP', 'RL', 'VAR']]
        ]).sort_values(by='VAR', ascending=False)
        
        print("[✔] SGP Data Prepared!")
    
    def prepare_data(self, df, player_type):
        df = df.reset_index()
        if (player_type=='Hitter'):
            df['Total_SGP'] = df.iloc[:, [2,3,4,6,7]].sum(axis=1)
            df['Total_SGP_wSB'] = df.iloc[:, 2:8].sum(axis=1)
            
            df = df.sort_values(by="Total_SGP", ascending=False).reset_index()
            
            hitter_rl = df.loc[156, "Total_SGP"]
            
            df["RL"] = hitter_rl
            df["VAR"] = df["Total_SGP"] - hitter_rl
            
        else:
            df['Total_SGP'] = df.iloc[:, 2:8].sum(axis=1)
            df['Starter'] = np.where(df['GS'] > 5, 1, 0)
            
            df = df.sort_values(by="Total_SGP", ascending=False).reset_index()

            starter_rl = df[df["Starter"] == 1]["Total_SGP"].iloc[108]
            reliever_rl = df[df["Starter"] == 0]["Total_SGP"].iloc[36]
            
            df["RL"] = df.apply(lambda row: starter_rl if row["Starter"] == 1 else reliever_rl, axis=1)
            df["VAR"] = df["Total_SGP"] - df["RL"]
            
        return df
    
    def export_sgp(self):
        print("[*] Exporting SGP Results...")
        
        SAVE_FOLDER = os.path.join(os.getcwd(), "results")
        os.makedirs(SAVE_FOLDER,exist_ok=True)
        
        file_name = f"results/SGP_Results_{self.suffix}.xlsx"
        
        with pd.ExcelWriter(file_name) as writer:
            self.hitters_df[['Name', 'PlayerId', 'PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP_wSB', 'Total_SGP', 'RL', 'VAR']].to_excel(writer, sheet_name='Hitters', index=False)
            self.pitchers_df[['Name', 'PlayerId', 'IP', 'SGP_SO', 'SGP_QS', 'SGP_SV_HLD', 'SGP_ERA', 'SGP_WHIP', 'SGP_K/BB', 'Total_SGP', 'RL', 'VAR']].to_excel(writer, sheet_name='Pitchers', index=False)
            self.combined_df.to_excel(writer, sheet_name='Combined', index=False)
        
        print(f"[✔] Exported SGP Results to {file_name}")
