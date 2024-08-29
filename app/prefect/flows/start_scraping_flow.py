from prefect import flow, task
from app.prefect.tasks.scraping_task import start_scraping_tasks
from app.prefect.tasks.urls_discover import discover_urls


@flow(
    retries=2,
    retry_delay_seconds=10,
    log_prints=True,
    persist_result=False
)
def scraping_arxiv(query: str):
    search_url = f'https://arxiv.org/search/?searchtype=all&query={query}&abstracts=show&size=200&order=-announced_date_first'
    subsites = {"query": query}
    return discover_and_scrape_flow(base_url='https://arxiv.org/', search_url=search_url, extract='pdf', subsites=subsites, pagination = True)

@flow(
    retries=2,
    retry_delay_seconds=10,
    log_prints=True,
    persist_result=False
)
def discover_and_scrape_flow(base_url: str, search_url: str, subsites: dict = {}, extract: str = '/', pagination: bool=False):
    # Ejecutar la tarea para descubrir URLs
    num_discovered_pages = discover_urls(base_url=base_url, search_url=search_url, extract=extract, subsites=subsites, pagination=pagination)
    
    # Ejecutar la tarea de scraping
    start_scraping_tasks(base_url=base_url, extract=extract, subsites=subsites)
    
    return {"message": f"Started scraping {num_discovered_pages} pages."}

if __name__ == "__main__":
    # Cambia los parámetros por los valores de prueba que desees usar
    query = 'human mortality'
    result = scraping_arxiv(query=query)
    print(result)
