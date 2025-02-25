import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

def get_fangraphs_csv(url, save_path):
    """Scrape the Export button URL and download the CSV file."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }

    # Step 1: Get the HTML of the page
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to load page: {url}")
        return

    # Step 2: Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, "lxml")

    # Step 3: Look for the "Export Data" link
    export_link = None
    for link in soup.find_all("a", href=True):
        if "csv" in link["href"].lower():
            export_link = link["href"]
            break

    if not export_link:
        print("Could not find CSV export link on the page.")
        return

    # Convert relative URL to absolute URL if necessary
    if export_link.startswith("/"):
        base_url = "https://www.fangraphs.com"
        export_link = base_url + export_link

    print(f"Downloading CSV from: {export_link}")

    # Step 4: Download the CSV file
    csv_response = requests.get(export_link, headers=headers)
    if csv_response.status_code != 200:
        print("Failed to download CSV file.")
        return

    # Step 5: Save the CSV file
    csv_path = save_path.replace(".xlsx", ".csv")
    with open(csv_path, "wb") as f:
        f.write(csv_response.content)

    # Step 6: Convert CSV to Excel
    df = pd.read_csv(csv_path)
    df.to_excel(save_path, index=False)
    os.remove(csv_path)  # Remove original CSV

    print(f"File saved: {save_path}")


# URLs for FanGraphs projections
urls = {
    "fangraphs_hitting_atc": "https://www.fangraphs.com/projections?type=atc&stats=bat&pos=all&team=0&players=0&lg=all&z=1738576938&pageitems=30&statgroup=fantasy&fantasypreset=dashboard",
    "fangraphs_pitching_atc": "https://www.fangraphs.com/projections?type=atc&stats=pit&pos=&team=0&players=0&lg=all&z=1738576938&sortcol=&sortdir=desc&pageitems=30&statgroup=fantasy&fantasypreset=dashboard",
}

# Save directory
save_folder = os.path.expanduser("~/repos/FantasyPlayerEvaluation/SGPFantasyWorking")
os.makedirs(save_folder, exist_ok=True)

# Download each dataset
for filename, url in urls.items():
    save_path = os.path.join(save_folder, f"{filename}.xlsx")
    get_fangraphs_csv(url, save_path)
