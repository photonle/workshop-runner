from faktory import Worker
import logging


logging.basicConfig(level=logging.DEBUG)
def workshop_update(wsid, *arg):
    logging.error(wsid)
    return "no"


w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()