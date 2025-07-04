import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

from google.cloud import storage

SELENIUM_GRID_URL = "http://selenium:4444/wd/hub"

# Load environment variables from a .env file
load_dotenv()

FANGRAPHS_USERNAME = os.getenv("FANGRAPHS_USERNAME")
FANGRAPHS_PASSWORD = os.getenv("FANGRAPHS_PASSWORD")

if not FANGRAPHS_USERNAME or not FANGRAPHS_PASSWORD:
    raise ValueError("FanGraphs credentials are missing! Set them in .env or environment variables.")

HOME_DIR = os.path.expanduser("~")

# Set the downloads folder
DOWNLOAD_FOLDER = os.path.join(HOME_DIR, "Downloads")

# URLs
LOGIN_URL = "https://blogs.fangraphs.com/wp-login.php"
PROJECTIONS_URLS = {
    "fangraphs_hitting_atc":    "https://www.fangraphs.com/projections?type=atc&stats=bat&pos=all",
    "fangraphs_hitting_batx":   "https://www.fangraphs.com/projections?pos=all&stats=bat&type=thebatx",
    "fangraphs_pitching_atc":   "https://www.fangraphs.com/projections?type=atc&stats=pit&pos=all",
    "fangraphs_pitching_oopsy": "https://www.fangraphs.com/projections?type=oopsy&stats=pit&pos=all",
    "auc_calc_hitting_atc":     "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=bat&players=&proj=atc&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    "auc_calc_hitting_batx":    "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=bat&players=&proj=thebatx&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    "auc_calc_pitching_atc":    "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=pit&players=&proj=atc&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    "auc_calc_pitching_oopsy":  "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=pit&players=&proj=oopsy&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0"
}

BASE_DIR = os.path.abspath(os.getcwd())

# Where to save files
SAVE_FOLDER = os.path.join(BASE_DIR, "projections")
SAVE_FOLDER_AUC = os.path.join(BASE_DIR,"auction_calculator_exports")

os.makedirs(SAVE_FOLDER, exist_ok=True)
os.makedirs(SAVE_FOLDER_AUC,exist_ok=True)

def login_to_fangraphs(driver):
        
    """Logs into FanGraphs."""
    print("[*] Navigating to FanGraphs login page...")
    driver.get(LOGIN_URL)
    time.sleep(3)

    # username
    print("[*] Entering username...")
    username_field = driver.find_element(By.ID, "user_login")
    username_field.send_keys(FANGRAPHS_USERNAME)

    # password
    print("[*] Entering password...")
    password_field = driver.find_element(By.ID, "user_pass")
    password_field.send_keys(FANGRAPHS_PASSWORD)
    password_field.send_keys(Keys.RETURN)  # Press Enter to log in

    time.sleep(5)  # Wait for login to process
    print("[✔] Successfully logged in!")

def download_fangraphs_csv(driver, url, save_path):
    """Navigates to FanGraphs projections page, clicks 'Export Data', and downloads CSV."""
    print(f"[*] Navigating to: {url}")
    driver.get(url)
    time.sleep(5)

    try:
        # Find and click the "Export Data" button
        print("[*] Searching for 'Export Data' button...")
        export_button = driver.find_element(By.LINK_TEXT, "Export Data")
        
        # Scroll to the button (optional)
        driver.execute_script("arguments[0].scrollIntoView();", export_button)
        time.sleep(1)

        # Click using JavaScript to bypass UI blocking issues
        print("[✔] Clicking 'Export Data' button via JavaScript...")
        driver.execute_script("arguments[0].click();", export_button)
    except Exception as e:
        print(f"[ERROR] Could not find or click the 'Export Data' button: {e}")
        return

    # Wait for the file to download
    time.sleep(10)  

    # Find the latest downloaded file
    files = sorted(
        os.listdir(DOWNLOAD_FOLDER), 
        key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_FOLDER, x)), 
        reverse=True
    )
    
    csv_file = next((f for f in files if f.endswith(".csv")), None)

    if not csv_file:
        print("[ERROR] No CSV file found after download.")
        return

    csv_path = os.path.join(DOWNLOAD_FOLDER, csv_file)
    print(f"[✔] Downloaded file: {csv_path}")

    # Convert CSV to Excel
    df = pd.read_csv(csv_path)
    df.to_excel(save_path, index=False)
    os.remove(csv_path)
    print(f"[✔] File saved: {save_path}")

def wait_for_selenium(timeout=1500):
    """Wait for Selenium Grid to be available."""
    print("[*] Waiting for Selenium Grid to be ready...")
    for i in range(timeout):
        try:
            response = requests.get(SELENIUM_GRID_URL)
            if response.status_code == 200 and response.json().get("value", {}).get("ready", False):
                print("[✔] Selenium Grid is ready!")
                return
        except requests.exceptions.RequestException:
            pass  # Keep trying
        
        print(f"[*] Selenium not ready, retrying... ({i+1}/{timeout})")
        time.sleep(1)  # Wait 1 second before retrying

    print("[ERROR] Selenium did not start in time. Exiting...")
    exit(1)

def upload_to_bucket(local_file_path, gcs_blob_name, bucket_name="fantasysgpsystem-outputs"):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)
        blob.upload_from_filename(local_file_path)
        print(f"[⬆] Uploaded to GCS: gs://{bucket_name}/{gcs_blob_name}")
    except Exception as e:
        print(f"[!] Failed to upload {local_file_path} to GCS: {e}")
        
            
def main():
    # **Detect if running inside Docker**
    running_in_docker = os.path.exists("/.dockerenv")
    options = Options()
    
    if running_in_docker:
        wait_for_selenium()
        
        options = Options()
        options.add_argument("--headless=new")  
        options.add_argument("--no-sandbox")  # Required inside Docker
        options.add_argument("--disable-dev-shm-usage")  
        options.add_argument("--disable-gpu")  # Disable GPU acceleration

        print("[*] Running inside Docker, using pre-installed ChromeDriver...")
        driver = webdriver.Remote(command_executor=SELENIUM_GRID_URL, options=options)
        
    else:
        options.add_argument("--start-maximized")

        # Set up WebDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Log in to FanGraphs
    login_to_fangraphs(driver)

    # Download each dataset
    for filename, url in PROJECTIONS_URLS.items():
        print(f"\n[⚡] Processing: {filename}")
        save_path = os.path.join(SAVE_FOLDER, f"{filename}.xlsx") if "fangraphs" in filename else os.path.join(SAVE_FOLDER_AUC, f"{filename}.xlsx")
        gcs_blob_name = f"projections/{filename}.xlsx" if "fangraphs" in filename else f"auction_calculator_exports/{filename}.xlsx"
        download_fangraphs_csv(driver, url, save_path)
        upload_to_bucket(save_path, gcs_blob_name)
        
    print("\n[✔] Done!")
    driver.quit()

if __name__ == "__main__":
    main()
