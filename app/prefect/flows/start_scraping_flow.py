from prefect import flow, task
from app.prefect.tasks.scraping_task import start_scraping_tasks
from app.prefect.tasks.urls_discover import discover_urls

@task
async def discover_urls_task(base_url: str, search_url: str, extract: str):
    if not search_url:
        search_url = base_url
    return await discover_urls(base_url=base_url, search_url=search_url, extract=extract)

@task
def start_scraping_tasks_task(extract: str):
    start_scraping_tasks(extract=extract)

@flow
def discover_and_scrape_flow(base_url: str, search_url: str, extract: str = '/'):
    # Ejecutar la tarea para descubrir URLs
    num_discovered_pages = discover_urls_task(base_url=base_url, search_url=search_url, extract=extract)
    
    # Ejecutar la tarea de scraping
    start_scraping_tasks_task(extract=extract)
    
    return {"message": f"Started scraping {num_discovered_pages} pages."}

if __name__ == "__main__":
    discover_and_scrape_flow("http://example.com", "/search", "/")
