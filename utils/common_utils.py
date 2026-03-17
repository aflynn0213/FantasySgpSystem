from pathlib import Path
from typing import Any
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

def is_gcs_enabled() -> bool:
    """Return True only when use_gcs is explicitly set to true in config.yml."""
    return bool(load_config().get("use_gcs", False))


def download_from_bucket(bucket_name, blob_path, local_path):
    if not is_gcs_enabled():
        print(f"[GCS disabled] Skipping download of {blob_path}")
        return
    from google.cloud import storage  # lazy import — only needed when GCS is on
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
            return download_fangraphs_csv(DOWNLOAD_FOLDER, driver, url, save_path, retries=retries-1)
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
    if not is_gcs_enabled():
        print(f"[GCS disabled] Skipping debug upload of {local_path}")
        return
    try:
        from google.cloud import storage  # lazy import
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        print(f"Uploaded {local_path} to gs://{bucket_name}/{gcs_path}")
    except Exception as e:
        print(f"Failed to upload to GCS: {e}")


def upload_to_bucket(local_file_path, gcs_blob_name, bucket_name="fantasysgpsystem-outputs"):
    if not is_gcs_enabled():
        print(f"[GCS disabled] Skipping upload of {local_file_path}")
        return
    try:
        from google.cloud import storage  # lazy import
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)
        blob.upload_from_filename(local_file_path)
        print(f"Uploaded to GCS: gs://{bucket_name}/{gcs_blob_name}")
    except Exception as e:
        print(f"Failed to upload {local_file_path} to GCS: {e}")

def get_repo_root() -> str:
    if os.environ.get("RUNNING_IN_DOCKER"):
        return "/FantasySgpSystem"
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True
    ).strip()

_config_cache = None

def load_config(path: str = None):
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    if path is None:
        path = os.path.join(get_repo_root(), "config.yml")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    _config_cache = yaml.safe_load(p.read_text())
    return _config_cache

def parse_hitter_config_categories():
    cfg = load_config()
    temp = cfg.get("categories", {}).get("hitters", {})
    counting = temp.get("counting", [])
    rate_entries = temp.get("rate", [])
    if not isinstance(rate_entries, list):
        raise ValueError(f"'rate' for Hitters should be a list, got {type(rate_entries)}")

    cat_opps = []
    for entry in rate_entries:
        rate_metric, opp_metric = entry[0], entry[1]
        if not isinstance(rate_metric, str) or not isinstance(opp_metric, str):
            raise ValueError(f"Rate and opportunity metrics must be strings, got: {entry}")
        cat_opps.append((rate_metric, opp_metric))

    return counting, cat_opps

def parse_pitcher_config_categories():
    cfg = load_config()
    temp = cfg.get("categories", {}).get("pitchers", {})
    counting = temp.get("counting", [])
    rate_entries = temp.get("rate", [])
    if not isinstance(rate_entries, list):
        raise ValueError(f"'rate' for Pitchers should be a list, got {type(rate_entries)}")

    cat_opps = []
    for entry in rate_entries:
        rate_metric, opp_metric = entry[0], entry[1]
        if not isinstance(rate_metric, str) or not isinstance(opp_metric, str):
            raise ValueError(f"Rate and opportunity metrics must be strings, got: {entry}")
        cat_opps.append((rate_metric, opp_metric))

    return counting, cat_opps


def parse_hitter_points_config() -> dict:
    """Return the hitter points-scoring weights dict from config.yml.
    Keys are stat names, values are numeric point values (may be negative/zero).
    """
    cfg = load_config()
    raw = cfg.get("points", {}).get("hitters", {})
    return {k: float(v) for k, v in raw.items()}


def parse_pitcher_points_config() -> dict:
    """Return the pitcher points-scoring weights dict from config.yml.
    Keys are stat names, values are numeric point values (may be negative/zero).
    """
    cfg = load_config()
    raw = cfg.get("points", {}).get("pitchers", {})
    return {k: float(v) for k, v in raw.items()}

def build_config_hitter_counts():
    """Single config read that returns everything both processors need for rostering.

    Returns:
        sufficient_pos_counts  – group totals × num_teams  e.g. {C:12, CI:36, MI:36, OF:60, UTIL:12}
        position_mapping       – individual pos → group     e.g. {'2B':'MI', '1B':'CI', …}
        ind_slot_limits        – per-position slot totals   e.g. {C:12, 1B:12, 2B:12, OF:60, …}
        comp_slot_limits       – flex-only slot totals      e.g. {MI:12, CI:12}
    """
    cfg = load_config()
    num_teams  = cfg["defaults"]["num_teams"]
    pos_counts = cfg.get("hitter_position_counts", {})

    position_mapping = {
        'C':  'C',
        '1B': 'CI',
        '2B': 'MI',
        '3B': 'CI',
        'SS': 'MI',
        'OF': 'OF',
        'DH': 'UTIL',
    }

    for pos, count in pos_counts.items():
        if not isinstance(pos, str) or not isinstance(count, int):
            raise ValueError(f"Invalid roster position entry: {pos}: {count}")

    # Individual dedicated slot limits (one entry per position × num_teams)
    ind_slot_limits = {pos: pos_counts.get(pos, 0) * num_teams for pos in position_mapping}

    # Composite flex slot limits — MI and CI only (the grp values that aren't C / OF / UTIL)
    comp_groups    = dict.fromkeys(grp for grp in position_mapping.values() if grp not in ('C', 'OF', 'UTIL'))
    comp_slot_limits = {grp: pos_counts.get(grp, 0) * num_teams for grp in comp_groups}

    # Group totals (sufficient_pos_counts) — sum individual + composite + UTIL
    position_mapping_ext = {**position_mapping, 'CI': 'CI', 'MI': 'MI', 'UTIL': 'UTIL'}
    raw_totals = {}
    for pos, count in pos_counts.items():
        grp = position_mapping_ext.get(pos, pos)
        raw_totals[grp] = raw_totals.get(grp, 0) + count
    sufficient_pos_counts = {k: v * num_teams for k, v in raw_totals.items()}

    print(f"League position counts: {sufficient_pos_counts}")
    print(f"Total League Rostered Hitters: {sum(sufficient_pos_counts.values())}")
    print(f"Position mapping: {position_mapping}")

    return sufficient_pos_counts, position_mapping, ind_slot_limits, comp_slot_limits


def get_position_priority() -> list:
    """Return the ordered position priority list from config (e.g. ['C','2B','OF','SS',…])."""
    return load_config().get("position_priority", ['C', '2B', 'OF', 'SS', '3B', '1B', 'DH'])


def validate_export_columns(df: "pd.DataFrame", required_cols: list, label: str = "") -> None:
    """Raise ValueError if any required_cols are absent from df.

    Args:
        df:            DataFrame to inspect.
        required_cols: Column names that must be present.
        label:         Human-readable context string (e.g. 'Hitters SGP') shown in the error.
    """
    import pandas as pd  # local import keeps top-level imports unchanged
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        where = f" ({label})" if label else ""
        raise ValueError(f"Export column(s) missing{where}: {missing}")

