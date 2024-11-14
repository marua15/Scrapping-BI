from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import logging
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Chrome options
chrome_options = uc.ChromeOptions()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-webgl")
chrome_options.add_argument("--disable-application-cache")

# Initialize the WebDriver service
service = Service(executable_path="chromedriver-win64/chromedriver.exe")
# logging.info("Starting the WebDriver")

try:
    driver = uc.Chrome(options=chrome_options)
except Exception as e:
    logging.error(f"Failed to initialize the Chrome driver: {e}")
    sys.exit(1)

try:
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    keyword = "llm"

    # Go directly to the search results page with "llm" as the query
    search_url = "https://www.sciencedirect.com/search?qs=llm"
    driver.get(search_url)
    logging.info(f"Page title: {driver.title}")

    # Optional: wait for search results to load, or add more interaction if needed
    driver.implicitly_wait(10)
    time.sleep(3)

    # Wait for search results to load
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.ID, "srp-results-list")))

except NoSuchWindowException:
    logging.error("The target window was closed prematurely.")
except TimeoutException:
    logging.error("Timed out waiting for search results to load.")
finally:
    # Ensure the driver quits even if an exception occurs
    if driver:
        driver.quit()
