# pip install requests pandas selenium webdriver-manager lxml
import time
import requests
import pandas as pd
from io import BytesIO
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

URL = "https://www.fangraphs.com/leaders/major-league?pos=all&stats=bat&lg=all&type=c%2C4%2C5%2C6%2C19%2C11%2C12%2C13%2C21%2C-1%2C34%2C35%2C40%2C41%2C-1%2C23%2C37%2C38%2C50%2C317%2C61%2C-1%2C111%2C-1%2C203%2C199%2C58&month=0&ind=0&team=0&qual=100&v_cr=202301&startdate=&enddate=&season1=2025&season=2025&pagenum=1&pageitems=2000000000"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.fangraphs.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

def try_csv(url: str) -> pd.DataFrame | None:
    u = urlparse(url)
    qs = dict(parse_qsl(u.query, keep_blank_values=True))
    qs["csv"] = "1"
    csv_url = urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(qs), u.fragment))
    r = requests.get(csv_url, headers=HEADERS, timeout=30)
    # heuristic: CSV should have commas and sane first line
    if r.ok and ("," in r.text.splitlines()[0] or "text/csv" in r.headers.get("content-type","")):
        try:
            return pd.read_csv(BytesIO(r.content))
        except Exception:
            return None
    return None

def scrape_with_selenium(url: str) -> pd.DataFrame:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--user-agent={HEADERS['User-Agent']}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.get(url)

        # Wait for both header and first rows to exist
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.table-fixed thead tr th"))
        )
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.table-scroll tbody tr"))
        )

        # Keep scrolling until row count stops increasing (virtualized table)
        prev = -1
        for _ in range(60):  # up to ~30s
            rows = driver.find_elements(By.CSS_SELECTOR, "div.table-scroll tbody tr")
            if len(rows) == prev:
                break
            prev = len(rows)
            driver.execute_script("""
                const sc=document.querySelector('div.table-scroll');
                if(sc){ sc.scrollTop = sc.scrollHeight; }
            """)
            time.sleep(0.5)

        # Headers from fixed header table
        header_cells = driver.find_elements(By.CSS_SELECTOR, "div.table-fixed thead tr th, div.table-fixed thead tr td")
        raw_headers = [h.text.strip().replace("\xa0"," ") for h in header_cells]
        keep_idx = [i for i,h in enumerate(raw_headers) if h and h != "-- Line Break --"]
        headers = [raw_headers[i] for i in keep_idx]

        # Body rows from scroll table
        data_rows = []
        for tr in driver.find_elements(By.CSS_SELECTOR, "div.table-scroll tbody tr"):
            tds = tr.find_elements(By.CSS_SELECTOR, "td")
            if not tds:
                continue
            values_all = [td.text.strip().replace("\xa0"," ") for td in tds]
            row = [values_all[i] if i < len(values_all) else "" for i in keep_idx]
            data_rows.append(row)

        if not data_rows:
            raise RuntimeError("No data rows found after render/scroll.")

        df = pd.DataFrame(data_rows, columns=headers)

        # Clean numerics
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].str.replace(",", "", regex=False).replace({"": None, "-": None})
                df[c] = pd.to_numeric(df[c], errors="ignore")
        return df
    finally:
        driver.quit()

def fetch_leaders_df(url: str) -> pd.DataFrame:
    df = try_csv(url)
    if df is not None and not df.empty:
        return df
    return scrape_with_selenium(url)

if __name__ == "__main__":
    df = fetch_leaders_df(URL)
    # Optional rank column
    df.insert(0, "SGP Rank", range(1, len(df) + 1))
    print(df.head(10))
    df.to_csv("fangraphs_leaders_2025_bat.csv", index=False)
    print("Saved fangraphs_leaders_2025_bat.csv")
