"""
Zerodha authentication module
"""

import logging
import time
import urllib.parse as urlparse
import os

import pyotp
from dotenv import load_dotenv, find_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from kiteconnect import KiteConnect

from options_analysis.config.settings import get_chrome_options

# Load .env (if present) into environment variables
load_dotenv(find_dotenv())


class ZerodhaAuthenticator:
    def __init__(self):
        # Read credentials at runtime from environment variables
        self.ZERODHA_KEY = os.getenv("ZERODHA_KEY")
        self.ZERODHA_SECRET = os.getenv("ZERODHA_SECRET")
        self.ZERODHA_USER = os.getenv("ZERODHA_USER")
        self.ZERODHA_PASSWORD = os.getenv("ZERODHA_PASSWORD")
        self.ZERODHA_TOTP_SECRET = os.getenv("ZERODHA_TOTP_SECRET")

        logging.info("Loading credentials from environment variables...")
        logging.info(f"ZERODHA_KEY: {'SET' if self.ZERODHA_KEY else 'NOT SET'}")
        logging.info(f"ZERODHA_SECRET: {'SET' if self.ZERODHA_SECRET else 'NOT SET'}")
        logging.info(f"ZERODHA_USER: {'SET' if self.ZERODHA_USER else 'NOT SET'}")
        logging.info(f"ZERODHA_PASSWORD: {'SET' if self.ZERODHA_PASSWORD else   'NOT SET'}")
        logging.info(f"ZERODHA_TOTP_SECRET: {'SET' if self.ZERODHA_TOTP_SECRET else 'NOT SET'}")

        missing = [n for n, v in {
            "ZERODHA_KEY": self.ZERODHA_KEY,
            "ZERODHA_SECRET": self.ZERODHA_SECRET,
            "ZERODHA_USER": self.ZERODHA_USER,
            "ZERODHA_PASSWORD": self.ZERODHA_PASSWORD,
            "ZERODHA_TOTP_SECRET": self.ZERODHA_TOTP_SECRET,
        }.items() if not v]
        if missing:
            raise RuntimeError(f"Missing environment variables for credentials: {', '.join(missing)}")

        logging.info("✅ Credentials loaded successfully")

        self.kite = KiteConnect(api_key=self.ZERODHA_KEY)
        self.access_token = None

    def authenticate(self):
        """Complete authentication flow and return kite object"""
        try:
            driver = self._initialize_webdriver()
            request_token = self._perform_login(driver)
            self._generate_session(request_token)
            profile = self.kite.profile()
            logging.info(f"Logged in as: {profile['user_name']}")
            return self.kite
            
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            raise
    
    def _initialize_webdriver(self):
        """Initialize and return Chrome WebDriver"""
        logging.info("Initializing Chrome WebDriver...")
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=get_chrome_options(headless=True)
            )
            logging.info("✅ WebDriver initialized successfully!")
            return driver
        except Exception as e:
            logging.error(f"❌ WebDriver initialization failed: {e}")
            raise
    
    def _perform_login(self, driver):
        """Perform login and return request token"""
        try:
            logging.info(self.kite.login_url())
            driver.get(self.kite.login_url())
            wait = WebDriverWait(driver, 15)


            logging.info(f"✅ credential {self.ZERODHA_USER}, {self.ZERODHA_PASSWORD}", )

            # Enter user ID and password
            wait.until(EC.presence_of_element_located((By.ID, "userid"))).send_keys(self.ZERODHA_USER)
            driver.find_element(By.ID, "password").send_keys(self.ZERODHA_PASSWORD)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            logging.info("✅ Login successful.. going to sleep for 3 secs")
            time.sleep(3)
            
            # Enter TOTP
            totp = pyotp.TOTP(self.ZERODHA_TOTP_SECRET).now()
            logging.info(f"OTP generated: {totp}.. going to sleep for 3 secs")
            time.sleep(3)
            driver.find_element(By.ID, "userid").send_keys(totp)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            logging.info("OTP Validated.. going to sleep for 3 secs")
            time.sleep(3)
            
            # Extract request token
            current_url = driver.current_url
            driver.quit()
            
            parsed = urlparse.urlparse(current_url)
            request_token = urlparse.parse_qs(parsed.query)["request_token"][0]
            logging.info(f"Request Token: {request_token}")
            
            return request_token
            
        except Exception as e:
            logging.error(f"Login process failed: {e}")
            if 'driver' in locals():
                driver.quit()
            raise
    
    def _generate_session(self, request_token):
        """Generate session using request token"""
        data = self.kite.generate_session(request_token, api_secret=self.ZERODHA_SECRET)
        self.access_token = data["access_token"]
        self.kite.set_access_token(self.access_token)
        logging.info(f"Access Token: {self.access_token}")