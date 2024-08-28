import asyncio
import os
import logging
from celery import Celery

from app.prefect.tasks.scraping_task import scrape_page_async, scrape_pdf_async

from dotenv import load_dotenv

load_dotenv()

rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')
rabbitmq_host = os.getenv('RABBITMQ_HOST')
rabbitmq_port = os.getenv('RABBITMQ_PORT')

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "rpc://")

# Configuración de logging
celery.conf.update(
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s"
)

# Configuración del logger
logger = logging.getLogger('celery')
logger.setLevel(logging.INFO)  # Cambia el nivel de logging según lo necesites

# Si deseas agregar un handler de consola
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s: %(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

@celery.task(name="scrape_page")
def scrape_page(url):
    asyncio.run(scrape_page_async(url))

@celery.task(name="scrape_pdf")
def scrape_pdf(url):
    asyncio.run(scrape_pdf_async(url))