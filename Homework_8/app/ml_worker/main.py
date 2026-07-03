import pika
import time
import logging
import os
import json
from app.models.model import Model
from app.services.crud import event as EventService
from sqlmodel import Session
from app.database.database import engine

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
# Настройка логирования 

ml_model = Model()

def get_model():
    return ml_model

connection_params = pika.ConnectionParameters(
    host=os.getenv('RABBITMQ_HOST'),  
    port=int(os.getenv('RABBITMQ_PORT')),       
    virtual_host='/',  
    credentials=pika.PlainCredentials(
        username= os.getenv('RABBITMQ_USER'),  
        password=os.getenv('RABBITMQ_PASSWORD')   
    ),
    heartbeat=30,
    blocked_connection_timeout=2
)

connection = pika.BlockingConnection(connection_params)
channel = connection.channel()
queue_name = 'ml_task_queue'
channel.queue_declare(queue=queue_name, durable = True)  



def callback(ch, method, properties, body):    

    try:
        task = json.loads(body)
        event_id = task.get("event_id")
        image_path = task.get("image_path")        
        logger.info(f"Received: '{body}'")

        filename = os.path.basename(image_path)
        full_path = os.path.join("/data/images", filename)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")

        prediction = ml_model.predict(full_path)
        time.sleep(3) 
      #  ch.basic_ack(delivery_tag=method.delivery_tag)

        with Session(engine) as session:
            EventService.prediction_update(event_id, prediction, session)

        logger.info(f" Success {event_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Error processing: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


channel.basic_qos(prefetch_count=1)


channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=False 
)

logger.info('Waiting for messages. To exit, press Ctrl+C')
channel.start_consuming()


