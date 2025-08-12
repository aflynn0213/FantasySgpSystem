import pickle
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "https://www.fangraphs.com/"
COOKIE_PATH = "cookies.pkl"

options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

print("[*] Opening Chrome. Please log into FanGraphs manually.")
driver.get(LOGIN_URL)

input("[⏳] Press Enter after logging in and verifying you're on the home page...")

cookies = driver.get_cookies()
with open(COOKIE_PATH, "wb") as f:
    pickle.dump(cookies, f)

print(f"[✔] Cookies saved to {COOKIE_PATH}")
driver.quit()
