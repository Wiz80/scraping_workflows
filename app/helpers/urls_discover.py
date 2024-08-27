import os
import pika
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from app.helpers.tree_scraped import TreeScraped

load_dotenv()
rabbitmq_host = os.getenv('RABBITMQ_HOST')
rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')

JSON_FILE_PATH = "app/cache/scraped_sites.json"
CONFIG_FILE_PATH = "app/cache/site_config.json"

async def discover_urls(base_url: str, search_url: str, extract: str, rabbitmq_queue: str = 'url_queue'):
    
    tree_scraped = TreeScraped()
    # Cargar el archivo JSON de sitios scrapeados
    scraped_sites = tree_scraped.load_json_file(JSON_FILE_PATH, default_value=[])
    
    # Cargar el archivo de configuración de sitios
    site_config = tree_scraped.load_json_file(CONFIG_FILE_PATH, default_value={})

    # Verificar si el sitio tiene una configuración específica de subsite
    site_config_entry = site_config.get(base_url, {})
    subsite_key = site_config_entry.get("subsite_key")  # Puede ser "query", "category", etc.

    # Extraer el valor del subsite si existe una palabra reservada en la configuración
    subsite_value = None
    if subsite_key:
        # Extraer el valor de la palabra reservada en la URL (ej. query, category)
        subsite_value = search_url.split(f"?{subsite_key}=")[-1].split("&")[0] if f"{subsite_key}=" in search_url else search_url
    
    # Verificar si ya existe el sitio y el subsite correspondiente al valor extraído
    subsite_entry = tree_scraped.find_subsite(scraped_sites, base_url, subsite_value) if subsite_value else None
    
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

        # Espera a que se cargue el cuerpo de la página
        await page.wait_for_selector("body")

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

        await browser.close()

    # Cerrar la conexión con RabbitMQ
    connection.close()

    # Si hay nuevas URLs, actualizar el archivo JSON
    if new_urls:
        if subsite_entry:
            # Si ya existe el subsite, actualizamos las URLs
            subsite_entry["urls"].extend(new_urls)
        else:
            # Si no existe el subsite y hay una palabra reservada, lo creamos
            if subsite_value:
                new_subsite = {
                    subsite_key: subsite_value,
                    "urls": new_urls
                }

                # Verificamos si ya existe el sitio y añadimos el nuevo subsite
                site_entry = next((entry for entry in scraped_sites if entry["site"] == base_url), None)
                if site_entry:
                    site_entry["subsites"].append(new_subsite)
                else:
                    # Si no existe el sitio, lo creamos
                    new_site_entry = {
                        "site": base_url,
                        "subsites": [new_subsite]
                    }
                    scraped_sites.append(new_site_entry)
            else:
                # Si no hay subsite, simplemente añadimos las URLs al sitio
                site_entry = next((entry for entry in scraped_sites if entry["site"] == base_url), None)
                if site_entry:
                    if "urls" in site_entry:
                        site_entry["urls"].extend(new_urls)
                    else:
                        site_entry["urls"] = new_urls
                else:
                    # Si no existe el sitio, lo creamos sin subsite
                    new_site_entry = {
                        "site": base_url,
                        "urls": new_urls
                    }
                    scraped_sites.append(new_site_entry)
        
        # Guardar el archivo JSON actualizado
        tree_scraped.save_json_file(JSON_FILE_PATH, scraped_sites)

    return len(new_urls)