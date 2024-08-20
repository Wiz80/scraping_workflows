# services/scraping_service.py
from app.worker import scrape_page
import os
import pika

def start_scraping_tasks(rabbitmq_queue: str = 'url_queue'):
    rabbitmq_host = os.getenv('RABBITMQ_HOST')
    rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
    rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')

    # Configurar la conexión a RabbitMQ
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials))
    channel = connection.channel()

    try:
        for method_frame, properties, body in channel.consume(rabbitmq_queue, inactivity_timeout=5):
            if body is None:
                # Si no hay más mensajes después del tiempo de inactividad, salir del bucle
                break

            url = body.decode('utf-8')
            scrape_page.delay(url)  # Crear una tarea Celery para cada URL
            channel.basic_ack(method_frame.delivery_tag)  # Confirmar el mensaje

    finally:
        connection.close()
