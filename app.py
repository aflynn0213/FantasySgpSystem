from flask import Flask, render_template
import pandas as pd
from processor.SgpProcessor import SgpProcessor  # Import your SGPProcessor class
from SGP import SgpHitters, SgpPitchers  # Import your hitter & pitcher classes

app = Flask(__name__)

# 🔹 Global variable to store SGP results
sgp_results = None  # Stores {'hitters': df, 'pitchers': df, 'combined': df}

def generate_sgp():
    """Runs the SGP processing and stores results globally."""
    global sgp_results
    print("[*] Running SGP Processor...")

    # Initialize hitter & pitcher objects
    sgp_hit = SgpHitters(proj="ATC HIT '25", player_sheet="SGP ATC HIT '25")
    sgp_pit = SgpPitchers(proj="ATC PIT '25", player_sheet="SGP ATC PIT '25")

    # Process SGP rankings
    processor = SgpProcessor(sgp_hit, sgp_pit)

    # Store results in global variable
    sgp_results = {
        'hitters': processor.hitters_df,
        'pitchers': processor.pitchers_df,
        'combined': processor.combined_df
    }
    
    print("[✔] SGP Processing Completed!")

@app.route('/')
def home():
    """Main page displaying SGP results."""
    if sgp_results is None:
        generate_sgp()  # Run if not already processed

    return render_template('index.html',
                           hitters_html=sgp_results['hitters'].to_html(classes="table table-striped", index=False),
                           pitchers_html=sgp_results['pitchers'].to_html(classes="table table-striped", index=False),
                           combined_html=sgp_results['combined'].to_html(classes="table table-striped", index=False))

@app.route('/refresh')
def refresh():
    """Refresh SGP rankings and reload the page."""
    generate_sgp()
    return home()

if __name__ == '__main__':
    app.run(debug=True)
