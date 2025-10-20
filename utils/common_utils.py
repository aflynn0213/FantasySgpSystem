from pathlib import Path
from typing import Any
from google.cloud import storage
import os
import time
import pandas as pd 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.docker_running import is_running_in_docker
import subprocess
import yaml

def download_from_bucket(bucket_name, blob_path, local_path):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)
    print(f"[⬇] Downloaded {blob_path} from GCS to {local_path}")

def download_fangraphs_csv(DOWNLOAD_FOLDER, driver, url, save_path, retries=3):
    """Navigates to FanGraphs projections page, clicks 'Export Data', and downloads CSV."""
    print(f"Navigating to: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 30)

    try:
        # Find and click the "Export Data" button
        print("Searching for 'Export Data' button...")
        export_button = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Export Data")))

        # Scroll to the button (optional)
        driver.execute_script("arguments[0].scrollIntoView();", export_button)
        time.sleep(1)

        # Click using JavaScript to bypass UI blocking issues
        print("Clicking 'Export Data' button via JavaScript...")
        driver.execute_script("arguments[0].click();", export_button)
    
    except TimeoutException as e:
        print(f"[ERROR] Could not find or click the 'Export Data' button: {e}")
        debug_docker_selenium(driver, label="login_error", bucket="fantasysgpsystem-outputs")
        print("Debugging information uploaded to GCS.")
        if retries > 0:
            print("Retrying download...")
            return download_fangraphs_csv(driver, url, save_path, retries=retries-1)
        else:
            print("[!] Max retries reached. Skipping this file.")
            return
        
    # Wait for the file to download
    time.sleep(10)
    if is_running_in_docker():  
        print(f"[DEBUG] Checking for files in {DOWNLOAD_FOLDER}")
        print(os.listdir(DOWNLOAD_FOLDER))
    
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
    print(f"Downloaded file: {csv_path}")

    # Convert CSV to Excel
    df = pd.read_csv(csv_path)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    df.to_excel(save_path, index=False)
    os.remove(csv_path)
    print(f"File saved: {save_path}")
    
def debug_docker_selenium(driver, label="debug", bucket="fantasysgpsystem-outputs"):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"/tmp/{label}_{timestamp}.png"
    html_path = f"/tmp/{label}_{timestamp}.html"

    try:
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        upload_debug_file(screenshot_path, f"{label}_{timestamp}.png", bucket)
    except Exception as e:
        print(f"Failed to save/upload screenshot: {e}")

    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"HTML source saved to: {html_path}")
        upload_debug_file(html_path, f"{label}_{timestamp}.html", bucket)
    except Exception as e:
        print(f"Failed to save/upload HTML: {e}")

def upload_debug_file(local_path, gcs_path, bucket_name="your-debug-bucket-name"):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        print(f"Uploaded {local_path} to gs://{bucket_name}/{gcs_path}")
    except Exception as e:
        print(f"Failed to upload to GCS: {e}")
        
def upload_to_bucket(local_file_path, gcs_blob_name, bucket_name="fantasysgpsystem-outputs"):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)
        blob.upload_from_filename(local_file_path)
        print(f"Uploaded to GCS: gs://{bucket_name}/{gcs_blob_name}")
    except Exception as e:
        print(f"Failed to upload {local_file_path} to GCS: {e}")

def get_repo_root() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True
    ).strip()

def load_config(path: str = "config.yml"):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return yaml.safe_load(p.read_text())

def parse_hitter_config_categories(cfg: Any):
    categories = []
    opportunities = []
    temp = cfg["categories"].get("hitters", {}).items()
    rate_entries = temp.get("rate", [])
    if not isinstance(rate_entries, list):
        raise ValueError(f"'rate' for Hitters should be a list, got {type(rate_entries)}")

    for entry in rate_entries:
        rate_metric = entry[0]
        opp_metric = entry[1]

        if not isinstance(rate_metric, str) or not isinstance(opp_metric, str):
            raise ValueError(f"Rate and opportunity metrics must be strings, got: {entry}")

        categories.append(rate_metric)
        opportunities.append(opp_metric)

    if len(categories) != len(opportunities):
        raise ValueError(f"Length mismatch: {len(categories)} rate metrics vs {len(opportunities)} opportunities")

    cat_opps = list(zip(categories,opportunities))
    return categories, cat_opps

def parse_pitcher_config_categories(cfg: Any):
    categories = []
    opportunities = []
    temp = cfg["categories"].get("pitchers", {}).items()
    rate_entries = temp.get("rate", [])
    if not isinstance(rate_entries, list):
        raise ValueError(f"'rate' for Pitchers should be a list, got {type(rate_entries)}")

    for entry in rate_entries:
        rate_metric = entry[0]
        opp_metric = entry[1]

        if not isinstance(rate_metric, str) or not isinstance(opp_metric, str):
            raise ValueError(f"Rate and opportunity metrics must be strings, got: {entry}")

        categories.append(rate_metric)
        opportunities.append(opp_metric)

    if len(categories) != len(opportunities):
        raise ValueError(f"Length mismatch: {len(categories)} rate metrics vs {len(opportunities)} opportunities")

    cat_opps = list(zip(categories,opportunities))
    return categories, cat_opps

    

    
    