import os
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from app.tasks.scraping_task import save_scraped_content
import logging
from celery import Celery

from dotenv import load_dotenv

load_dotenv()

rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')
rabbitmq_host = os.getenv('RABBITMQ_HOST')
rabbitmq_port = os.getenv('RABBITMQ_PORT')

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "rpc://")

@celery.task(name="scrape_page")
async def scrape_page(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Esperar a que se cargue completamente la página
            await page.goto(url, wait_until='networkidle')

            # Esperar a que se cargue el cuerpo de la página
            await page.wait_for_selector("body")

            # Scroll para cargar contenido dinámico
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(2000)  # Espera adicional después del scroll

            # Obtener el contenido HTML y texto visible
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator="\n", strip=True)

            await browser.close()

        # Guardar el contenido extraído
        try:
            save_scraped_content(url, text_content)
        except Exception as e:
            logging.error(f"Error saving content for {url}: {e}")
            return False

        return True  # Scraping successful

    except Exception as e:
        logging.error(f"An error occurred while scraping {url}: {e}")
        return False