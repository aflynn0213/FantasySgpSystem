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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException

from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import shutil
import pickle
from pathlib import Path

import subprocess

from google.cloud import storage
from utils.docker_running import is_running_in_docker
from utils.common_utils import (download_fangraphs_csv, 
                                download_from_bucket, 
                                debug_docker_selenium, 
                                upload_to_bucket)



# Constants
SELENIUM_GRID_URL = "http://selenium:4444/wd/hub"

BUCKET_NAME = "fantasysgpsystem-outputs"

# Load environment variables from a .env file
load_dotenv()

FANGRAPHS_USERNAME = os.getenv("FANGRAPHS_USERNAME")
FANGRAPHS_PASSWORD = os.getenv("FANGRAPHS_PASSWORD")

if not FANGRAPHS_USERNAME or not FANGRAPHS_PASSWORD:
    raise ValueError("FanGraphs credentials are missing! Set them in .env or environment variables.")

HOME_DIR = os.path.expanduser("~")


# URLs
LOGIN_URL = "https://blogs.fangraphs.com/wp-login.php"
PROJECTIONS_URLS = {
    "fangraphs_hitting_stats":      "https://www.fangraphs.com/leaders/major-league?pos=all&stats=bat&lg=all&type=c%2C4%2C5%2C6%2C19%2C11%2C12%2C13%2C21%2C-1%2C34%2C35%2C40%2C41%2C-1%2C23%2C37%2C38%2C50%2C317%2C61%2C-1%2C111%2C-1%2C203%2C199%2C58&month=0&ind=0&team=0&qual=100&v_cr=202301&startdate=&enddate=&season1=2025&season=2025&pagenum=1&pageitems=2000000000",
    #"fangraphs_hitting_atc_ros":    "https://www.fangraphs.com/projections?type=ratcdc&stats=bat&pos=all&team=0&players=0&lg=all&z=1749725837&sortcol=&sortdir=desc&pageitems=30&statgroup=dashboard&fantasypreset=dashboard",
    #"fangraphs_hitting_batx_ros":   "https://www.fangraphs.com/projections?type=rthebatx&stats=bat&pos=all&team=0&players=0&lg=all&z=1749725837&pageitems=30&statgroup=dashboard&fantasypreset=dashboard",
    #"auc_calc_hitting_atc_ros":     "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=bat&players=&proj=ratcdc&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    #"auc_calc_hitting_batx_ros":    "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=bat&players=&proj=rthebatx&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    "fangraphs_pitching_stats":     "https://www.fangraphs.com/leaders/major-league?pos=all&stats=pit&lg=all&type=0&ind=0&team=0&v_cr=202301&startdate=&enddate=&season1=2025&season=2025&pageitems=2000000000&month=0&qual=40",
    #"auc_calc_pitching_oopsy_ros":  "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=bat&players=&proj=roopsydc&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    #"fangraphs_pitching_oopsy_ros": "https://www.fangraphs.com/projections?type=roopsydc&stats=pit&pos=all&team=0&players=0&lg=all&z=1757070220&pageitems=30&statgroup=standard&fantasypreset=dashboard",
    "auc_calc_hitting_eoy":         "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=bat&players=&proj=2025&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0",
    "auc_calc_pitching_eoy":        "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=12&lg=MLB&dollars=260&mb=1&mp=20&msp=10&mrp=1&type=pit&players=&proj=2025&split=65&points=c%7C1%2C2%2C3%2C4%2C5%2C6%7C13%2C14%2C2%2C3%2C4%2C8&rep=0&drp=0&pp=C%2C2B%2COF%2CSS%2C3B%2C1B&pos=1%2C1%2C1%2C1%2C5%2C1%2C1%2C1%2C0%2C1%2C9%2C3%2C0%2C1%2C0&sort=&view=0"
}

BASE_DIR = os.path.abspath(os.getcwd())

# Where to save files
SAVE_FOLDER = os.path.join(BASE_DIR, "stats")
SAVE_FOLDER_AUC = os.path.join(BASE_DIR,"auction_calculator_exports")
SAVE_FOLDER_ROS = os.path.join(BASE_DIR, "ros")
SAVE_FOLDER_EOY = os.path.join(BASE_DIR, "eoy")

os.makedirs(SAVE_FOLDER, exist_ok=True)
os.makedirs(SAVE_FOLDER_AUC,exist_ok=True)
os.makedirs(SAVE_FOLDER_AUC, exist_ok=True)
os.makedirs(SAVE_FOLDER_ROS, exist_ok=True)
os.makedirs(SAVE_FOLDER_EOY, exist_ok=True)

if is_running_in_docker():
    DOWNLOAD_FOLDER = "/downloads"
else:
    DOWNLOAD_FOLDER = os.path.join(HOME_DIR, "Downloads")

cookie_path = "/tmp/cookies.pkl" if is_running_in_docker() else  "./cookies.pkl"



def get_chrome_major_version():
    try:
        result = subprocess.run(["google-chrome", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        version_str = result.stdout.strip()
        if version_str.startswith("Google Chrome"):
            major_version = int(version_str.split()[2].split('.')[0])
            return major_version
    except Exception as e:
        print(f"[!] Failed to detect Chrome version: {e}")
    return None


def login_to_fangraphs(driver, max_attempts: int = 6, backoff: int = 3):
    """Attempt to log into FanGraphs, retrying on transient failures.

    Returns True when login succeeds. Raises RuntimeError after max_attempts.
    """
    driver.get(LOGIN_URL)
    time.sleep(2)

    wait = WebDriverWait(driver, 20)

    # Wait for username and password fields, then submit
    username = wait.until(EC.presence_of_element_located((By.ID, "user_login")))
    username.clear()
    username.send_keys(FANGRAPHS_USERNAME)

    password = wait.until(EC.presence_of_element_located((By.ID, "user_pass")))
    password.clear()
    password.send_keys(FANGRAPHS_PASSWORD)
    password.send_keys(Keys.RETURN)

    # Wait for a clear post-login signal: either logout link or URL change
    try:
        wait.until(lambda d: ("wp-login.php" not in d.current_url) or d.find_elements(By.LINK_TEXT, "Log Out"))
    except Exception:
        pass
    
    print("Logged in")
    return True
            
        
def main():
    
    print("[DEBUG] Chrome:", shutil.which("google-chrome"))
    print("[DEBUG] Chromedriver:", shutil.which("chromedriver"))
    
    if is_running_in_docker():
        print("[DEBUG] ******Inside of docker container*******")
        options = Options()
        prefs = {
            "download.default_directory": DOWNLOAD_FOLDER,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.binary_location = "/usr/bin/google-chrome"
        options.add_argument("--user-data-dir=/chrome_profile")
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-quic")

        driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=options)

        # Check profile login
        driver.get("https://www.fangraphs.com/")
        time.sleep(3)
        if "Sign In" not in driver.page_source:
            print("Chrome profile login successful")
        else:
            print("Chrome profile login failed, falling back to manual login")
            login_to_fangraphs(driver)

    else:
        print("[DEBUG] ******Outside of docker container*******")
        profile_path = Path("./chrome_profile").resolve()
        os.makedirs(profile_path, exist_ok=True)
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-quic")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Log in to FanGraphs
        login_to_fangraphs(driver)

    # Download each dataset
    for filename, url in PROJECTIONS_URLS.items():
        print(f"\n Processing: {filename}")
        
        if "auc_calc" in filename:
            save_path = os.path.join(SAVE_FOLDER_AUC, f"{filename}.xlsx") 
            gcs_blob_name = f"auction_calculator_exports/{filename}.xlsx"
        elif "ros" in filename:
            save_path = os.path.join(SAVE_FOLDER_ROS, f"{filename}.xlsx") 
            gcs_blob_name = f"ros/{filename}.xlsx"
        elif "stats" in filename:
            save_path = os.path.join(SAVE_FOLDER, f"{filename}.xlsx") 
            gcs_blob_name = f"stats/{filename}.xlsx"
        elif "eoy" in filename:
            save_path = os.path.join(SAVE_FOLDER, f"{filename}.xlsx") 
            gcs_blob_name = f"eoy/{filename}.xlsx"
        else:
            continue  # Skip unknown file types
        
        print("Downloading Fangraphs Data...")
        download_fangraphs_csv(DOWNLOAD_FOLDER, driver, url, save_path)

        # Upload to GCS
        upload_to_bucket(save_path, gcs_blob_name)
        
    if not is_running_in_docker():
        time.sleep(15)  # Ensure all downloads are complete
        driver.quit()

        if os.path.exists(profile_path):
            print(f"[FOUND] Profile folder found: {profile_path}")
        else:
            print("[FAILED] chrome_profile directory NOT FOUND")
    else:
        driver.quit()

    print("\n Done!")
    
    
if __name__ == "__main__":
    main()
