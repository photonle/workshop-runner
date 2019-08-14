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
    logging.debug(data)

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
    lastup = curs.next()
    logging.debug(lastup)





w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
