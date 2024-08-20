from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def run_playwright_scraper(base_url: str):
    pages_to_scrape = ["/"]
    visited_pages = set()
    scraped_content = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        while pages_to_scrape:
            current_page = pages_to_scrape.pop(0)
            if current_page in visited_pages:
                continue
            
            url = base_url + current_page
            page.goto(url)
            html_content = page.content()

            # Extract just visible text
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator="\n", strip=True)
            scraped_content[url] = text_content
            visited_pages.add(current_page)

            # Find all internal links to add to pages_to_scrape
            links = page.query_selector_all("a[href^='/']")
            for link in links:
                href = link.get_attribute("href")
                if href and href not in visited_pages:
                    pages_to_scrape.append(href)

        browser.close()
    return scraped_content
