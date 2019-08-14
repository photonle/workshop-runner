from environs import Env
env = Env()
env.read_env()

from faktory import Worker
import logging
import workshop
import mysql.connector


logging.error(env.dump())
logging.basicConfig(level=logging.DEBUG)


def workshop_update(args):
    wsid = args["wsid"]
    data = workshop.query(wsid)
    logging.error(data)


w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
