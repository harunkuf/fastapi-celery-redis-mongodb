from time import sleep
import traceback

from celery import current_task
from celery import states
from celery.exceptions import Ignore

from worker import celery

import pymongo
from pymongo import MongoClient

with open('cluster_password.txt', 'r') as file:
    cluster_password = file.read()

cluster = MongoClient(cluster_password)

db = cluster["b2metric"]
collection = db["library"]

@celery.task(name='borrow.many', bind=True)
def borrow_many(self, amount):
    amount = int(amount)
    try:
        for x in range(amount):
            collection.update_one({"_id":x},{"$set":{"status":"borrowed"}})
            self.update_state(state='PROGRESS', meta={'done': x, 'total': len(range(amount))})
        return {"result": "{} books have been borrowed from the library.".format(str(amount))}
    except Exception as ex:
        self.update_state(
            state=states.FAILURE,
            meta={
                'exc_type': type(ex).__name__,
                'exc_message': traceback.format_exc().split('\n')
            })
        raise ex