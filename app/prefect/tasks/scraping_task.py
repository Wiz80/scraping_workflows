# services/scraping_service.py
from app.celery.worker import scrape_page, scrape_pdf
import os
import pika

def start_scraping_tasks(rabbitmq_queue: str = 'url_queue',
                         extract: str = '/'):
    
    rabbitmq_host = os.getenv('RABBITMQ_HOST')
    rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
    rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS')

    # Configurar la conexión a RabbitMQ
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials))
    channel = connection.channel()
    count = 1
    try:
        for method_frame, properties, body in channel.consume(rabbitmq_queue, inactivity_timeout=5):
            if body is None:
                # Si no hay más mensajes después del tiempo de inactividad, salir del bucle
                break

            url = body.decode('utf-8')
            #TODO: BORRAR COUNT == 1 -> DEBUGGING
            if count == 1:
                if extract == 'pdf':
                    scrape_pdf.delay(url)
                else:
                    scrape_page.delay(url)
                channel.basic_ack(method_frame.delivery_tag)  # Confirmar el mensaje
            else:
                break
            count += 1

    finally:
        connection.close()
