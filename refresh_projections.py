import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine, inspect
import pandas as pd

# Function to download the CSV using Selenium
def download_fangraphs_csv(url, download_folder, export_button_xpath, output_path):
    # Set up Chrome options to automatically save the file
    options = Options()
    options.add_argument('--headless')  # Run in headless mode (no GUI)
    options.add_argument('--disable-gpu')
    options.add_argument(f'--window-size=1920x1080')

    # Set the download folder to automatically save files there
    prefs = {
        "download.default_directory": download_folder,
        "download.prompt_for_download": False,
    }
    options.add_experimental_option("prefs", prefs)

    # Initialize the WebDriver (adjust the path to your chromedriver)
    driver = webdriver.Chrome(executable_path='/path/to/chromedriver', options=options)

    # Open the FanGraphs page
    driver.get(url)

    # Find and click the "Export" button using the provided XPath
    export_button = driver.find_element(By.XPATH, export_button_xpath)
    export_button.click()

    # Wait for the download to complete (adjust the time as needed)
    time.sleep(5)  # Ensure the file is downloaded before closing the browser

    # Close the browser
    driver.quit()
    print(f"Download complete for {url}. File saved at {output_path}.")

# Function to create the tables if they don't exist and load the CSV into PostgreSQL
def create_and_load_table(csv_path, db_url, table_name):
    # Create a SQLAlchemy engine
    engine = create_engine(db_url)

    # Check if the table already exists
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        print(f"Table {table_name} does not exist. Creating the table...")
        df = pd.read_csv(csv_path)
        # Create the table and insert the data
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"Table {table_name} created and data inserted.")
    else:
        print(f"Table {table_name} exists. Overwriting the table...")
        # If the table exists, overwrite it
        df = pd.read_csv(csv_path)
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"Table {table_name} overwritten with new data.")

# Example FanGraphs URLs (replace these with the actual URLs of the pages containing the export button)
url_hitting = 'https://www.fangraphs.com/projections?type=atc&stats=bat&pos=all&team=0&players=0&lg=all&z=1738576938&pageitems=30&statgroup=fantasy&fantasypreset=dashboard'
url_pitching_atc = 'https://www.fangraphs.com/projections?type=atc&stats=pit&pos=&team=0&players=0&lg=all&z=1738576938&sortcol=&sortdir=desc&pageitems=30&statgroup=fantasy&fantasypreset=dashboard'
url_pitching_oopsy = 'https://www.fangraphs.com/projections?type=oopsy&stats=pit&pos=all&team=0&players=0&lg=all&z=1738576938&pageitems=30&statgroup=fantasy&fantasypreset=dashboard'

# Folder where the files will be saved
download_folder = '/path/to/download/folder'  # Specify the folder where you want to save the downloaded file

# XPath for the "Export" button (same for all pages)
export_button_xpath = '//*[@id="root-projections"]/div[2]/div/a'  # Same XPath for all 3 projection pages

# PostgreSQL connection string (replace with your actual credentials and database info)
db_url = 'postgresql://username:password@localhost:5432/your_database'

# File paths for saving the downloaded CSVs
output_path_hitting = os.path.join(download_folder, 'fangraphs_hitting_atc.csv')
output_path_pitching_atc = os.path.join(download_folder, 'fangraphs_pitching_atc.csv')
output_path_pitching_oopsy = os.path.join(download_folder, 'fangraphs_pitching_oopsy.csv')

# Table names in PostgreSQL
table_name_hitting = 'hitting_atc'
table_name_pitching_atc = 'pitching_atc'
table_name_pitching_oopsy = 'pitching_oopsy'

# Automate downloading the CSVs for all three URLs
download_fangraphs_csv(url_hitting, download_folder, export_button_xpath, output_path_hitting)
download_fangraphs_csv(url_pitching_atc, download_folder, export_button_xpath, output_path_pitching_atc)
download_fangraphs_csv(url_pitching_oopsy, download_folder, export_button_xpath, output_path_pitching_oopsy)

# Automate creating/loading the tables into PostgreSQL
create_and_load_table(output_path_hitting, db_url, table_name_hitting)
create_and_load_table(output_path_pitching_atc, db_url, table_name_pitching_atc)
create_and_load_table(output_path_pitching_oopsy, db_url, table_name_pitching_oopsy)
