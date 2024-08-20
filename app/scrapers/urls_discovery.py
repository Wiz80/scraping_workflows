import os
import pika
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

async def discover_urls(base_url: str, rabbitmq_queue: str = 'url_queue'):
    rabbitmq_host = os.getenv('RABBITMQ_HOST')
    rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
    rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')

    # Configurar la conexión a RabbitMQ
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials))
    channel = connection.channel()

    # Crear la cola si no existe
    channel.queue_declare(queue=rabbitmq_queue, durable=True)

    pages_to_scrape = ["/"]
    visited_pages = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while pages_to_scrape:
            current_page = pages_to_scrape.pop(0)
            if current_page in visited_pages:
                continue

            url = base_url + current_page
            await page.goto(url, wait_until='networkidle')

            # Espera a que se cargue el cuerpo de la página
            await page.wait_for_selector("body")

            visited_pages.add(current_page)

            # Encontrar todos los enlaces internos y enviarlos a la cola de RabbitMQ
            links = await page.query_selector_all("a[href^='/']")
            for link in links:
                href = await link.get_attribute("href")
                if href and href not in visited_pages:
                    pages_to_scrape.append(href)
                    channel.basic_publish(
                        exchange='',
                        routing_key=rabbitmq_queue,
                        body=base_url + href,
                        properties=pika.BasicProperties(
                            delivery_mode=2,  # Hacer que el mensaje sea persistente
                        )
                    )

        await browser.close()

    # Cerrar la conexión con RabbitMQ
    connection.close()

    return len(visited_pages)  # Retorna el número de páginas descubiertas
