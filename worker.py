from faktory import Worker
import logging


logging.basicConfig(level=logging.DEBUG)
def workshop_update(wsid):
    print(wsid)


w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()