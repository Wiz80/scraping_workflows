import os
import pika
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from app.helpers.tree_scraped import TreeScraped
from app.helpers.get_content import check_and_click_pagination
from prefect import task


load_dotenv()
rabbitmq_host = os.getenv('RABBITMQ_HOST')
rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')

JSON_FILE_PATH = "app/cache/scraped_sites.json"

@task(
    name="Discover urls of web site",
    tags=["getting urls"],
    description="From a base url of site scrape all the urls and put them on a RabbitMQ Queue"
)
async def discover_urls(base_url: str, search_url: str, subsites: dict, extract: str, pagination: bool = False, rabbitmq_queue: str = 'url_queue'):
    
    tree_scraped = TreeScraped()
    # Cargar el archivo JSON de sitios scrapeados
    scraped_sites = tree_scraped.load_json_file(JSON_FILE_PATH, default_value=[])
    
    # Extraer el valor del subsite si existe una palabra reservada en el diccionario subsites
    subsite_key, subsite_value = next(iter(subsites.items()), (None, None))
    
    # Verificar si ya existe el sitio y el subsite correspondiente al valor extraído
    site_entry = next((entry for entry in scraped_sites if entry["site"] == base_url), None)
    
    subsite_entry = None
    if site_entry and "subsites" in site_entry:
        subsite_entry = next((sub for sub in site_entry["subsites"] if sub.get(subsite_key) == subsite_value), None)
    
    # Si existe, obtenemos las URLs previas
    existing_urls = set(subsite_entry["urls"]) if subsite_entry else set()

    # Configurar la conexión a RabbitMQ
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials))
    channel = connection.channel()

    # Crear la cola si no existe
    channel.queue_declare(queue=rabbitmq_queue, durable=True)

    visited_pages = set()
    new_urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navegar a la URL de búsqueda
        await page.goto(search_url, wait_until='networkidle')

        while True:
            # Espera a que se cargue el cuerpo de la página
            await page.wait_for_selector("body")

            # Buscar todos los links que coincidan con el valor de 'extract'
            links = await page.query_selector_all(f"a[href*='{extract}']")

            for link in links:
                href = await link.get_attribute("href")
                if href and href not in visited_pages:
                    full_url = base_url + href if href.startswith("/") else href
                    
                    # Verificar si la URL ya existe
                    if full_url not in existing_urls:
                        visited_pages.add(full_url)
                        new_urls.append(full_url)  # Agregar a las nuevas URLs
                        channel.basic_publish(
                            exchange='',
                            routing_key=rabbitmq_queue,
                            body=full_url,
                            properties=pika.BasicProperties(
                                delivery_mode=2,  # Hacer que el mensaje sea persistente
                            )
                        )

            # Si la paginación está habilitada, verificar y hacer clic en el botón de "Next"
            if pagination:
                if base_url == "https://arxiv.org/":
                    has_next_page = await check_and_click_pagination(page, next_selector="a.pagination-next")
                if not has_next_page:
                    break  # Si no hay más páginas, salimos del bucle
            else:
                break  # Si no hay paginación o no es el caso específico de arxiv.org, salimos del bucle

        await browser.close()

    # Cerrar la conexión con RabbitMQ
    connection.close()

    # Si hay nuevas URLs, actualizar el archivo JSON
    if new_urls:
        if subsite_entry:
            # Si ya existe el subsite, actualizamos las URLs
            subsite_entry["urls"].extend(new_urls)
        else:
            # Si no existe el subsite, lo creamos
            new_subsite = {
                subsite_key: subsite_value,
                "urls": new_urls
            }

            if site_entry:
                # Añadimos el nuevo subsite al sitio existente
                if "subsites" not in site_entry:
                    site_entry["subsites"] = []
                site_entry["subsites"].append(new_subsite)
            else:
                # Si no existe el sitio, lo creamos con el nuevo subsite
                new_site_entry = {
                    "site": base_url,
                    "subsites": [new_subsite]
                }
                scraped_sites.append(new_site_entry)
        
        # Guardar el archivo JSON actualizado
        tree_scraped.save_json_file(JSON_FILE_PATH, scraped_sites)

    return len(new_urls)
