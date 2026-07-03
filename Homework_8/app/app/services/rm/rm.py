import pika
import os

# Параметры подключения
connection_params = pika.ConnectionParameters(
    host=os.getenv('RABBITMQ_HOST'),  # Замените на адрес вашего RabbitMQ сервера
    port=os.getenv('RABBITMQ_PORT'),          # Порт по умолчанию для RabbitMQ
    virtual_host='/',   # Виртуальный хост (обычно '/')
    credentials=pika.PlainCredentials(
        username= os.getenv('RABBITMQ_USER'),  # Имя пользователя по умолчанию
        password=os.getenv('RABBITMQ_PASSWORD')   # Пароль по умолчанию
    ),
    heartbeat=30,
    blocked_connection_timeout=2
)

def send_task(message:str):
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    
    # Имя очереди
    queue_name = 'ml_task_queue'

    # Отправка сообщения
    channel.queue_declare(queue=queue_name, durable = True)  # Создание очереди (если не существует)

    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message
    )

    # Закрытие соединения
    connection.close()