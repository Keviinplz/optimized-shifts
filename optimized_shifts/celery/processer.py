import asyncio
import json

import redis
from celery import Celery, Task

from .cloud.buckets import DataProcesorTypes
from .config import celeryconfig
from .tasks import process_data_task

celery_app = Celery("processer")
celery_app.config_from_object(celeryconfig)

r = redis.Redis.from_url(celery_app.conf["BROKER_URL"])
pubsub = r.pubsub(ignore_subscribe_messages=True)
pubsub.subscribe("notifications")


async def _process_data_async(
    task_id: str | None,
    data_type: DataProcesorTypes,
    data: str,
    r: "redis.Redis[bytes]",
):
    processed = await process_data_task(data_type, data)

    if not processed:
        r.publish(
            "notifications",
            json.dumps(
                {
                    "task_id": task_id,
                    "status": "FAILED",
                    "message": f"Unable to get data file from {data_type} or file cannot be converted into pandas",
                }
            ),
        )
        return

    r.publish(
        "notifications",
        json.dumps(
            {
                "task_id": task_id,
                "status": "DONE",
                "message": "Succesfully inserted data to postgis",
            }
        ),
    )


@celery_app.task(name="process_data", bind=True)
def process_data(self: Task, data_type: DataProcesorTypes, data: str):  # type: ignore
    asyncio.run(_process_data_async(self.request.id, data_type, data, r))
