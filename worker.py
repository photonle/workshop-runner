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
    curs.execute('''CREATE TABLE IF NOT EXISTS "addons" ( `wsid` NUMERIC, `name` TEXT, `author` NUMERIC, `lastup` NUMERIC, PRIMARY KEY(`wsid`) )''')
    curs.execute('''CREATE TABLE IF NOT EXISTS "authors" ( `sid` NUMERIC, `sname` TEXT, PRIMARY KEY(`sid`) )''')
    curs.execute('''CREATE TABLE IF NOT EXISTS "files" ( `path` TEXT, `owner` NUMERIC )''')
    curs.execute('''CREATE TABLE IF NOT EXISTS "components" ( `cname` TEXT, `owner` NUMERIC )''')
    curs.execute('''CREATE TABLE IF NOT EXISTS "cars" ( `cname` TEXT, `owner` NUMERIC )''')
    curs.execute('''CREATE TABLE IF NOT EXISTS "errors" ( `path` TEXT, `error` TEXT, `owner` NUMERIC )''')
    curs.close()

    curs = con.cursor(prepared=True)
    curs.execute("SELECT lastup FROM addons WHERE wsid = %s", (wsid,))
    lastup = curs.next()
    logging.debug(lastup)





w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
