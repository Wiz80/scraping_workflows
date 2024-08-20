from fastapi import FastAPI, BackgroundTasks
from app.scrapers.playwright_scraper import run_playwright_scraper
from app.scrapers.urls_discovery import discover_urls
from app.services.scraping_service import start_scraping_tasks

app = FastAPI()

# @app.get("/scrape_playwright")
# def scrape_playwright(url: str):
#     html_content = run_playwright_scraper(base_url=url)
#     return {"content": html_content}

@app.get("/discover_and_scrape")
async def discover_and_scrape(url: str, background_tasks: BackgroundTasks):
    num_discovered_pages = await discover_urls(base_url=url)
    background_tasks.add_task(start_scraping_tasks)
    return {"message": f"Started scraping {num_discovered_pages} pages."}