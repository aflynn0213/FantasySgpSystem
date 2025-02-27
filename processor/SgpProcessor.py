import pandas as pd
import numpy as np
class SgpProcessor:
    def __init__(self, sgp_hitters, sgp_pitchers):
        self.sgp_hitters = sgp_hitters.sgp_df.copy()
        self.sgp_pitchers = sgp_pitchers.sgp_df.copy()
        self.suffix = f"{sgp_hitters.proj}_{sgp_pitchers.proj}"
        self.export_sgp()
    
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
        # Prepare hitter data
        hitters_df = self.prepare_data(self.sgp_hitters, 'Hitter')
        pitchers_df = self.prepare_data(self.sgp_pitchers, 'Pitcher')
        
        # Select relevant columns
        hitters_export = hitters_df[['Name', 'PlayerId', 'PA', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG','Total_SGP_wSB', 'Total_SGP', 'RL', 'VAR']]
        pitchers_export = pitchers_df[['Name', 'PlayerId', 'IP', 'SGP_SO', 'SGP_QS', 'SGP_SV_HLD', 'SGP_ERA', 'SGP_WHIP', 'SGP_K/BB', 'Total_SGP', 'RL', 'VAR']]
        
        # Create combined data for ATC pitchers and all hitters
        combined_export = pd.concat([hitters_export[['Name', 'PlayerId', 'Total_SGP', 'RL', 'VAR']],
                                     pitchers_export[['Name', 'PlayerId', 'Total_SGP', 'RL', 'VAR']]])
        
        combined_export = combined_export.sort_values(by='VAR', ascending=False)
        
        file_name = f"results/SGP_Results_{self.suffix}.xlsx"
        
        # Export to Excel
        with pd.ExcelWriter(file_name) as writer:
            hitters_export.to_excel(writer, sheet_name='Hitters', index=False)
            pitchers_export.to_excel(writer, sheet_name='Pitchers', index=False)
            combined_export.to_excel(writer, sheet_name='Combined', index=False)