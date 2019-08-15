from environs import Env

env = Env()
env.read_env()

import faktory
from faktory import Worker
import logging
import workshop
import mysql.connector
from gmad import fromgma

logging.basicConfig(level=logging.DEBUG)

def workshop_update(args):
    with faktory.connection() as client:
        wsid = args["wsid"]
        data = workshop.query(wsid)
        logging.debug(data)

        if data["result"] != 1:
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'no result'), queue='results')

        if data["banned"] != 0:
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'item banned'), queue='results')

        if data["creator_app_id"] != 4000 or data["consumer_app_id"] != 4000:
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'not gmod'), queue='results')

        if not data["file_url"].endswith(".gma"):
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'not gma'), queue='results')

        con = mysql.connector.connect(
            user=env.str("MYSQL_USER"),
            password=env.str("MYSQL_PASSWORD"),
            host="db",
            database=env.str("MYSQL_DATABASE")
        )

        curs = con.cursor()
        curs.execute('''CREATE TABLE IF NOT EXISTS `addons` ( `wsid` INTEGER, `name` VARCHAR(500), `author` INTEGER, `lastup` INTEGER, PRIMARY KEY(`wsid`) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `authors` ( `sid` INTEGER, `sname` VARCHAR(500), PRIMARY KEY(`sid`) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `files` ( `path` VARCHAR(500), `owner` INTEGER )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `components` ( `cname` VARCHAR(500), `owner` INTEGER )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `cars` ( `cname` VARCHAR(500), `owner` INTEGER )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `errors` ( `path` VARCHAR(500), `error` VARCHAR(500), `owner` INTEGER )''')
        curs.close()

        curs = con.cursor(prepared=True)
        curs.execute("SELECT lastup FROM addons WHERE wsid = %s", (wsid,))
        lastup = curs.fetchone()
        if lastup is not None:
            logging.error(lastup)
            # Don't run and return.:

        # DL / Extract our addon.
        workshop.download(data["file_url"], "worker.gma")
        fromgma.extract_gma("worker.gma", "worker")








w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
