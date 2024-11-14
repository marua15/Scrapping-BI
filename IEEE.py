from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import json
import logging
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# chrome_options=Options()
# chrome_options.add_argument('--no-sandbox')
# chrome_options.add_argument('--headless')
# chrome_options.add_argument('--disable-dev-shm-usage')
# chrome_options.add_argument('--disable-gpu')
# chrome_options.add_argument('--window-size=1920,1080')


# Initialize the WebDriver service
service = Service(executable_path="chromedriver-win64/chromedriver.exe")
logging.info("Starting the WebDriver")
driver = webdriver.Chrome(service=service)
# driver= webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://ieeexplore.ieee.org")
logging.info(f"Page title: {driver.title}")

# Wait for the page to load fully
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Typeahead-input')))

# Search for the keyword "data"
search = driver.find_element(By.CLASS_NAME, 'Typeahead-input')
search.send_keys("llm")
search.send_keys(Keys.RETURN)

# Wait for search results to load
WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "List-results-items")))


try:
    filter_section = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "filter-box-header"))
    )
    filter_section.click()

    # Select the Early Access Articles checkbox directly
    early_access_filter = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[@for='refinement-ContentType:Early Access Articles']/input"))
    )
    early_access_filter.click()
    logging.info("Selected 'Early Access Articles' filter")

    # Click the apply button after selecting the filter
    apply_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Apply')]")
    apply_button.click()
    logging.info("Applied filters")
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "List-results-items")))  # Wait for results to update

except NoSuchElementException as e:
    logging.error(f"Error: {e}")
except TimeoutException:
    logging.error("Timed out while waiting for filter section")

# Data storage for articles
articles = []

def extract_issn(driver):
    """Extract ISSN information from the article's detail page."""
    issn_data = {}

    try:
        electronic_issn_element = driver.find_element(By.XPATH, "//strong[contains(text(), 'Electronic ISSN:')]/parent::div")
        issn_data['Electronic ISSN'] = electronic_issn_element.text.split(":")[-1].strip()
        logging.info(f"Electronic ISSN extracted: {issn_data['Electronic ISSN']}")
    except NoSuchElementException:
        logging.info("Direct Electronic ISSN not found, checking for collapsible ISSN section.")

    try:
        issn_toggle_button = driver.find_element(By.XPATH, "//h2[contains(text(), 'ISSN Information:')]")
        if "fa-angle-down" in issn_toggle_button.find_element(By.TAG_NAME, "i").get_attribute("class"):
            issn_toggle_button.click()
            time.sleep(2)
            logging.info("Clicked to expand the ISSN section.")

        issn_elements = driver.find_elements(By.CSS_SELECTOR, "div.abstract-metadata-indent div")
        for element in issn_elements:
            if "Electronic ISSN:" in element.text:
                issn_data['Electronic ISSN'] = element.text.split(":")[-1].strip()
            elif "Print ISSN:" in element.text:
                issn_data['Print ISSN'] = element.text.split(":")[-1].strip()

        logging.info(f"ISSN data extracted: {issn_data}")
    except NoSuchElementException:
        logging.error("ISSN information not found.")
    
    return issn_data

def scrape_authors(driver):
    """Extract authors' names from the article's detail page."""
    authors = []  # Change to a list instead of a dict

    try:
        # Wait for the authors section to be clickable
        authors_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'authors-header'))
        )
        authors_button.click()  # Click to expand the authors section
        logging.info("Clicked to expand the authors section.")

        # Wait for the authors to load
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'authors-accordion-container'))
        )

        # Extract authors' names
        author_cards = driver.find_elements(By.CLASS_NAME, 'authors-accordion-container')
        for card in author_cards:
            name_element = card.find_element(By.TAG_NAME, 'a')  # Author's name link
            name = name_element.text
            authors.append(name)  # Append directly to the list
            logging.info(f"Author extracted: {name}")

    except NoSuchElementException:
        logging.error("Authors section not found or could not be expanded.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    logging.info(f"Authors data extracted: {authors}")
    return authors  # Return the list of authors

# Function to extract keywords

def scrape_keywords(driver):
    """Extract Author and IEEE keywords from the page."""
    keywords = {
        "IEEE Keywords": [],
        "Author Keywords": []
    }

    try:
        # Click the toggle button to expand the keywords section if it is collapsed
        toggle_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.accordion-link#keywords"))
    )
        toggle_button.click()  # Simulate the click to expand

        # # Wait for the keywords section to be visible
        # keywords_section = WebDriverWait(driver, 10).until(
        #     EC.visibility_of_element_located((By.XPATH, "//section[contains(@class, 'keywords-tab')]"))
        # )

        # Locate the container with the keywords
        keyword_section = driver.find_elements(By.CSS_SELECTOR, "li.doc-keywords-list-item")
        
        # Extract Author Keywords
        for section in keyword_section:
            header = section.find_element(By.TAG_NAME, 'strong').text
            if header == "Author Keywords":
                author_keywords = section.find_elements(By.CSS_SELECTOR, "ul.List--inline li a")
                for keyword in author_keywords:
                    keywords["Author Keywords"].append(keyword.text.strip())

            # Extract IEEE Keywords
            elif header == "IEEE Keywords":
                ieee_keywords = section.find_elements(By.CSS_SELECTOR, "ul.List--inline li a")
                for keyword in ieee_keywords:
                    keywords["IEEE Keywords"].append(keyword.text.strip())
        
        logging.info(f"Extracted IEEE Keywords: {keywords['IEEE Keywords']}")
        logging.info(f"Extracted Author Keywords: {keywords['Author Keywords']}")
        return keywords

    except NoSuchElementException:
        logging.error("Keywords not found.")
        return keywords
    except Exception as e:
        logging.error(f"Error extracting keywords: {e}")
        return keywords

def get_locations(driver):
    time.sleep(0.5)
    all_countries = set()
    all_locations = set()
    try:
        authors_div = driver.find_element(By.ID, "authors")
        ActionChains(driver).move_to_element(authors_div).perform()
        authors_div.click()
        authors = driver.find_elements(By.CLASS_NAME, "authors-accordion-container")
        
        for auth in authors:
            split_text = auth.text.split('\n')
            if len(split_text) > 1:  # Ensure there's at least two elements
                location = split_text[1]
                # Clean up and add to sets
                location_clean = location.replace('View Profile', '').split(',')
                all_locations.add(','.join(location_clean[:2]))  
                all_countries.add(location_clean[-1].strip())    
        
        driver.back()
    except NoSuchElementException:
        logging.error("Elements not found")

    # Return as lists for consistency
    return list(all_countries), list(all_locations)
def get_locations(driver):
    time.sleep(0.5)  # Brief pause to ensure elements are loaded
    all_univ = set()
    all_countries = set()
    all_locations = list()

    try:
        # Access the authors section
        authors_div = driver.find_element(By.ID, "authors")
        ActionChains(driver).move_to_element(authors_div).perform()
        authors_div.click()

        # Collect author location information
        authors = driver.find_elements(By.CLASS_NAME, "authors-accordion-container")
        for auth in authors:
            location = auth.text.split('\n')[1]  # Extract location line
            cleaned_location = location.replace("View Profile", "").strip()

            # Split location by commas to extract university and country info
            location_parts = cleaned_location.split(',')
            if len(location_parts) >= 2:
                university = location_parts[0].strip()
                country = location_parts[-1].strip()

                all_univ.add(university)
                all_countries.add(country)
                all_locations.append(cleaned_location)  # Append entire cleaned location

        # Convert sets to semicolon-separated strings for consistent output
        universities = "; ".join(all_univ)
        countries = "; ".join(all_countries)
        
        # Logging the results
        logging.info(f"Extracted Universities: {universities}")
        logging.info(f"Extracted Countries: {countries}")
        logging.info(f"Extracted Locations: {all_locations}")
        
        return {"Universities": universities, "Countries": countries, "Locations": all_locations}

    except Exception as e:
        logging.error(f"Error extracting locations: {e}")
        return {"Universities": "", "Countries": "", "Locations": []}


# Function to print scraped data
def print_data(article):
    print(f"Title: {article['title']}")
    print(f"Authors: {', '.join(article['authors'])}")  # Access authors directly as a list
    print(f"Published in: {article['published_in']}")
    print(f"Date of Publication: {article['date_of_publication']}")
    print(f"DOI: {article['doi']}")
    print(f"Publisher: {article['publisher']}")
    print(f"Abstract: {article['abstract']}")
    print("ISSN:")
    for key, value in article['issn'].items():
        print(f"  {key}: {value}")
    print("Keywords:")
    print("  IEEE Keywords: ", ', '.join(article['keywords']['IEEE Keywords']))
    print("  Author Keywords: ", ', '.join(article['keywords']['Author Keywords']))
    print(f"Locations: {article['locations']}") 
    print("-------------------------------")


# Function to save data to a JSON file
def save_to_json(articles, filename="data/LLM_articles.json"):
    with open(filename, 'w', encoding='utf-8') as json_file:  # Ensure utf-8 encoding
        json.dump(articles, json_file, indent=4, ensure_ascii=False)  # Set ensure_ascii to False
    logging.info(f"Data saved to {filename}")


# Function to scrape article data
def scrape_article_data():
    article = {}
    try:
        article['authors'] = scrape_authors(driver)  # Directly get the list of authors
    except Exception as e:
        article['authors'] = []  # Ensure authors is always a list

    try:
        article['published_in'] = driver.find_element(By.CLASS_NAME, "stats-document-abstract-publishedIn").text
    except NoSuchElementException:
        article['published_in'] = "Published in not found"

    # try:
    #     article['date_of_publication'] = driver.find_element(By.XPATH, "//div[contains(@class, 'doc-abstract-pubdate')]").text.split(":")[1].strip()
    # except NoSuchElementException:
    #     article['date_of_publication'] = "Publication date not found"
    try:
        article['date_of_publication'] = driver.find_element(By.XPATH, "//div[contains(@class, 'doc-abstract-pubdate')]").text.split(":")[1].strip()
        date_str = article["date_of_publication"]
        date_obj = datetime.strptime(date_str, "%d %B %Y")
        # Add month and year to JSON
        article["publication_month"] = date_obj.strftime("%B")
        article["publication_year"] = date_obj.year
    except (ValueError, KeyError):
        print("Date format is incorrect or missing")

    try:
        article['doi'] = driver.find_element(By.XPATH, "//a[contains(@href, 'doi.org')]").text
    except NoSuchElementException:
        article['doi'] = "DOI not found"

    try:
        article['publisher'] = driver.find_element(By.XPATH, "//div[@class='u-pb-1 doc-abstract-publisher']//span[@class='title' and text()='Publisher: ']/following-sibling::span").text
    except NoSuchElementException:
        article['publisher'] = "Publisher not found"

    try:
        article['abstract'] = driver.find_element(By.XPATH, "//div[@xplmathjax]").text
    except NoSuchElementException:
        article['abstract'] = "Abstract not found"

    # Extract ISSN information
    article['issn'] = extract_issn(driver)

    # Extract keywords
    article['keywords'] = scrape_keywords(driver)

    location_data = get_locations(driver)
    article['universities'] = location_data.get("Universities", "")
    article['countries'] = location_data.get("Countries", "")
    article['locations'] = location_data.get("Locations", [])

    return article



# Function to go to the next page using the "Next" button
def go_to_next_page():
    """Click on the 'Next' button to go to the next page."""
    try:
        # Wait for the 'Next' button to be clickable
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "next-btn"))
        )
        next_button.click()
        logging.info("Navigated to the next page.")
        return True  # Return True if next page is clicked
    except (NoSuchElementException, TimeoutException):
        logging.info("No more pages available or 'Next' button not found.")
        return False  # Return False if there is no next page button

# Main loop to scrape articles from multiple pages
page_number = 1
while True:
    logging.info(f"Scraping page {page_number}...")
    
    # Find all articles on the current page
    results = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "List-results-items"))
    )

    # Loop through the articles on the current page and scrape data
    for result in results:
        try:
            title_element = result.find_element(By.CSS_SELECTOR, "h3.text-md-md-lh a.fw-bold")
            link = title_element.get_attribute('href')
            title = title_element.text

            logging.info(f"Scraping article: {title}")

            # Open the article in a new tab and switch to that tab
            driver.execute_script("window.open(arguments[0], '_blank');", link)
            driver.switch_to.window(driver.window_handles[-1])

            # Scrape article data
            article = scrape_article_data()
            article['title'] = title
            print_data(article)
            articles.append(article)

            # Close the current article tab and switch back to the original tab
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        except (NoSuchElementException, TimeoutException) as e:
            logging.error(f"Error scraping article: {e}")
            if driver.window_handles:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

    # Check if there is a next page and go to the next page if available
    if not go_to_next_page():
        break  # Exit the loop if no more pages are available

    page_number += 1

# Save articles to JSON
save_to_json(articles)

# Close the driver
driver.quit()
