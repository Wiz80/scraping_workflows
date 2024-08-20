from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def run_selenium_scraper(base_url:str):
    pages_to_scrape = ["/"]
    visited_pages = set()
    scraped_content = {}

    options = Options()
    options.headless = True
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    while pages_to_scrape:
        current_page = pages_to_scrape.pop(0)
        if current_page in visited_pages:
            continue

        url = base_url + current_page
        driver.get(url)
        html_content = driver.page_source

        # Extraer solo el texto visible
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text(separator="\n", strip=True)
        scraped_content[url] = text_content
        visited_pages.add(current_page)

        # Find all internal links to add to pages_to_scrape
        links = driver.find_elements(By.CSS_SELECTOR, "a[href^='/']")
        for link in links:
            href = link.get_attribute("href")
            if href and href not in visited_pages:
                pages_to_scrape.append(href)

    driver.quit()
    return scraped_content
