import pandas as pd

class SgpProcessor:
    def __init__(self, sgp_hitters, sgp_pitchers):
        self.sgp_hitters = sgp_hitters.sgp_df.copy()
        self.sgp_pitchers = sgp_pitchers.sgp_df.copy()
        
        self.export_sgp()
    
    def prepare_data(self, df, player_type):
        df = df.reset_index()
        if (player_type=='Hitter'):
            df['Total_SGP'] = df.iloc[:, [2,3,4,6,7]].sum(axis=1)
            df['Total_SGP_wSB'] = df.iloc[:, 2:8].sum(axis=1)
        else:
            df['Total_SGP'] = df.iloc[:, 2:8].sum(axis=1)
        df.insert(0, 'Type', player_type)  # Mark if hitter or pitcher
        return df
    
    def export_sgp(self):
        # Prepare hitter data
        hitters_df = self.prepare_data(self.sgp_hitters, 'Hitter')
        pitchers_df = self.prepare_data(self.sgp_pitchers, 'Pitcher')
        
        # Select relevant columns
        hitters_export = hitters_df[['Name', 'PlayerId', 'SGP_R', 'SGP_HR', 'SGP_RBI', 'SGP_SB', 'SGP_OBP', 'SGP_SLG', 'Total_SGP']]
        pitchers_export = pitchers_df[['Name', 'PlayerId', 'SGP_SO', 'SGP_QS', 'SGP_SV_HLD', 'SGP_ERA', 'SGP_WHIP', 'SGP_K/BB', 'Total_SGP']]
        
        # Create combined data for ATC pitchers and all hitters
        combined_export = pd.concat([hitters_export[['Name', 'PlayerId', 'Total_SGP']],
                                     pitchers_export[['Name', 'PlayerId', 'Total_SGP']]])
        
        # Export to Excel
        with pd.ExcelWriter('SGP_Results.xlsx') as writer:
            hitters_export.to_excel(writer, sheet_name='Hitters', index=False)
            pitchers_export.to_excel(writer, sheet_name='Pitchers', index=False)
            combined_export.to_excel(writer, sheet_name='Combined', index=False)