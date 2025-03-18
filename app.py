from flask import Flask, render_template, request
import pandas as pd
from processor.SgpProcessor import SgpProcessor  # Import your SGPProcessor class
from Sgp.SgpHitters import SgpHitters # Import your hitter & pitcher classes
from Sgp.SgpPitchers import SgpPitchers

app = Flask(__name__)

# Global variable to store SGP results
sgp_results = None  # Stores {'hitters': df, 'pitchers': df, 'combined': df}
sgp_results_oops = None
sgp_results_batx_oops = None

def generate_sgp():
    """Runs the SGP processing and stores results globally."""
    global sgp_results, sgp_results_oops, sgp_results_batx_oops
    print("[*] Running SGP Processor...")

    # Initialize hitter & pitcher objects
    sgp_hit = SgpHitters(proj='atc')
    sgp_hit_batx = SgpHitters(proj='batx')
    sgp_pit = SgpPitchers(proj='atc')
    sgp_pit_oops = SgpPitchers(proj='oopsy',ip_adj='atc')
    
    # Process SGP rankings
    processor = SgpProcessor(sgp_hit, sgp_pit)
    processor_oops = SgpProcessor(sgp_hit,sgp_pit_oops)
    processor_batx_oops = SgpProcessor(sgp_hit_batx,sgp_pit_oops)
    
    # Store results in global variable
    sgp_results = {
        'hitters':  processor.hitters_df,
        'pitchers': processor.pitchers_df,
        'combined': processor.combined_df
    }
    
    sgp_results_oops = {
        'hitters':  processor_oops.hitters_df,
        'pitchers': processor_oops.pitchers_df,
        'combined': processor_oops.combined_df
    }   
    
    sgp_results_batx_oops = {
        'hitters':  processor_batx_oops.hitters_df,
        'pitchers': processor_batx_oops.pitchers_df,
        'combined': processor_batx_oops.combined_df,
    }
    
    print("[✔] SGP Processing Completed!")

@app.route('/')
def home():
    global sgp_results, sgp_results_oops, sgp_results_batx_oops
    
    """Main page displaying SGP results."""
    if sgp_results is None or sgp_results_oops is None or sgp_results_batx_oops is None:
        generate_sgp()  # Run if not already processed

    valid_projections = ['atc', 'oopsy']
    selected_proj = request.args.get('projection', 'atc')  # Defaults to 'atc'

    if selected_proj not in valid_projections:
        selected_proj = 'atc'  # Fallback to 'atc' if invalid

    # Choose correct dataset based on user selection
    results = sgp_results if selected_proj == 'atc' else sgp_results_oops

    return render_template('index.html',
                           selected_proj=selected_proj,
                           hitters_html=results['hitters'].to_html(classes="table table-striped", index=False),
                           pitchers_html=results['pitchers'].to_html(classes="table table-striped", index=False),
                           combined_html=results['combined'].to_html(classes="table table-striped", index=False))

@app.route('/refresh')
def refresh():
    """Refresh SGP rankings and reload the page."""
    generate_sgp()
    return home()

if __name__ == '__main__':
    app.run(debug=True)
