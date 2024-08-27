from fastapi import FastAPI, BackgroundTasks
from app.helpers.urls_discover import discover_urls
from app.services.scraping_service import start_scraping_tasks

app = FastAPI()

@app.get("/discover_and_scrape")
async def discover_and_scrape(base_url: str, 
                              search_url: str,
                              background_tasks: BackgroundTasks,
                              extract: str = '/'):
    
    if not search_url:
        search_url = base_url

    num_discovered_pages = await discover_urls(base_url=base_url, search_url=search_url, extract=extract)
    background_tasks.add_task(start_scraping_tasks, extract=extract)
    return {"message": f"Started scraping {num_discovered_pages} pages."}

#mortality