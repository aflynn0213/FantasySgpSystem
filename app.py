from SGP import SgpHitters, SgpPitchers

from flask import Flask, render_template
import pandas as pd
from openpyxl import load_workbook

app = Flask(__name__)

@app.route('/')
def home():
    # Initialize your objects
    sgp_hit = SgpHitters(proj="ATC HIT '25", player_sheet="SGP HIT ATC '25")
    sgp_pit = SgpPitchers(proj="ATC PIT '25", player_sheet="SGP PIT ATC '25")
    sgp_pit_oopsy = SgpPitchers(proj="SGP PIT OOPSY '25", player_sheet="SGP PIT OOPSY '25")

    # Convert pandas DataFrames to HTML
    stats_html = sgp_hit.stats.to_html(classes="table table-striped", index=False)  # For self.stats
    sgp_df_html = sgp_hit.sgp_df.to_html(classes="table table-striped", index=True)  # For self.sgp_df

    # Pass the HTML to the template
    return render_template('index.html', 
                           stats_html=stats_html,
                           sgp_df_html=sgp_df_html)

if __name__ == '__main__':
    app.run(debug=True)
