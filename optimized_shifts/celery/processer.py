import redis
from celery import Celery

from .config import celeryconfig

celery_app = Celery("processer")
celery_app.config_from_object(celeryconfig)

r = redis.Redis.from_url(celery_app.conf["BROKER_URL"])
pubsub = r.pubsub()
pubsub.subscribe("notifications")


@celery_app.task(name="process_data")
def process_data(data: str):
    r.publish("notifications", f"{data} is done")
    return f"returned: {data}"
