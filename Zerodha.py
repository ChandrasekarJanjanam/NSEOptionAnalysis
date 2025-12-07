#!python
import json
import logging

import pandas as pd
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from kiteconnect import KiteConnect
from selenium import webdriver
import urllib.parse as urlparse
from selenium.webdriver.common.by import By
import time, pyotp

logging.basicConfig(level=logging.INFO)


def autologin_selenium(zerodha_key, zerodha_secret, zerodha_totp_secret, zerodha_user, zerodha_password):


    kite = KiteConnect(api_key=zerodha_key)

    # 1. Open login URL in Selenium
    # Auto-download and use correct ChromeDriver version
    # Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # comment this if you want to see browser
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Start Selenium with webdriver-manager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=chrome_options)

    driver.get(kite.login_url())
    wait = WebDriverWait(driver, 15)

    # 2. Enter user_id + password
    wait.until(EC.presence_of_element_located((By.ID, "userid"))).send_keys(zerodha_user)
    driver.find_element(By.ID, "password").send_keys(zerodha_password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    print("Login successful.. going to sleep for 3 secs")
    time.sleep(3)


    # 3. Enter TOTP
    totp = pyotp.TOTP(zerodha_totp_secret).now()
    print("OTP generated :", totp)
    # wait.until(EC.presence_of_element_located((By.ID, "totp"))).send_keys(totp)
    # driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/input").send_keys(totp)
    driver.find_element(By.ID, "userid").send_keys(totp)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    print("OTP Validated.. going to sleep for 2 secs")
    time.sleep(2)

    # 4. Extract request_token from redirected URL
    current_url = driver.current_url
    driver.quit()

    # URL looks like: https://your-redirect-url/?status=success&request_token=xxxx
    parsed = urlparse.urlparse(current_url)
    request_token = urlparse.parse_qs(parsed.query)["request_token"][0]
    print("Request Token:", request_token)

    # 5. Exchange request_token for access_token
    data = kite.generate_session(request_token, api_secret=zerodha_secret)
    access_token = data["access_token"]
    kite.set_access_token(access_token)
    print("Access Token:", access_token)

    # Example API call
    profile = kite.profile()
    print("Logged in as:", profile["user_name"])

    return kite

if __name__ == "__main__":

    with open("config.json", "r") as f:
        config = json.load(f)
        zerodha_TOTP_secret = config["zerodha_TOTP_secret"]
        print(zerodha_TOTP_secret)

        ## temporary only
        totp = pyotp.TOTP(zerodha_TOTP_secret).now()
        print(totp)

        f.close()
    #
    #
    # kite = autologin_selenium(config["zerodha_key"], config["zerodha_secret"], config["zerodha_TOTP_secret"],
    #                          config["zerodha_user"], config["zerodha_password"])
    #
    # # autologin_http(config["zerodha_key"], config["zerodha_secret"], config["zerodha_TOTP_secret"],
    # #                  config["zerodha_user"], config["zerodha_password"])
    #
    #
    # instrument_dump = kite.instruments("NSE")
    # instrument_df = pd.DataFrame(instrument_dump)
    # print(instrument_df.head(5))
    # instrument_df.to_csv("zerodha_instruments.csv")