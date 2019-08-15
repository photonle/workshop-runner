import subprocess
from os import walk

from environs import Env

env = Env()
env.read_env()

import faktory
from faktory import Worker
import logging
import workshop
import mysql.connector
from gmad import fromgma
from os.path import join, relpath, normpath, normcase, basename

logging.basicConfig(level=logging.DEBUG)

def workshop_update(args):
    with faktory.connection() as client:
        wsid = args["wsid"]
        data = workshop.query(wsid)
        logging.debug(data)

        if data["result"] != 1:
            client.queue("WorkshopUpdateResult", args=(wsid, 'failure', 'no result'))

        if data["banned"] != 0:
            client.queue("WorkshopUpdateResult", args=(wsid, 'failure', 'item banned'))

        if data["creator_app_id"] != 4000 or data["consumer_app_id"] != 4000:
            client.queue("WorkshopUpdateResult", args=(wsid, 'failure', 'not gmod'))

        if not data["filename"].endswith(".gma"):
            client.queue("WorkshopUpdateResult", args=(wsid, 'failure', 'not gma'))

        con = mysql.connector.connect(
            user=env.str("MYSQL_USER"),
            password=env.str("MYSQL_PASSWORD"),
            host="db",
            database=env.str("MYSQL_DATABASE")
        )

        curs = con.cursor()
        curs.execute('''CREATE TABLE IF NOT EXISTS `addons` ( `wsid` VARCHAR(32), `name` VARCHAR(500), `author` VARCHAR(32), `lastup` INTEGER, PRIMARY KEY(`wsid`) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `authors` ( `sid` VARCHAR(32), `sname` VARCHAR(500), PRIMARY KEY(`sid`) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `files` ( `path` VARCHAR(500), `owner` VARCHAR(32) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `components` ( `cname` VARCHAR(500), `owner` VARCHAR(32) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `cars` ( `cname` VARCHAR(500), `owner` VARCHAR(32) )''')
        curs.execute('''CREATE TABLE IF NOT EXISTS `errors` ( `path` VARCHAR(500), `error` VARCHAR(500), `owner` VARCHAR(32) )''')
        con.commit()
        curs.close()

        curs = con.cursor(prepared=True)
        curs.execute("SELECT lastup FROM addons WHERE wsid = %s", (wsid,))
        lastup = curs.fetchone()
        if lastup is not None:
            logging.error(lastup)
            # Don't run and return.:

        curs.close()
        logging.error("running")

        gma, ext = "worker.gma", "worker_extract"
        # DL / Extract our addon.
        logging.error("downloading")
        workshop.download(data["file_url"], gma)
        logging.error("extracting")
        fromgma.extract_gma(gma, ext)

        logging.error("fetching")
        # And fetch our author.
        sid = data["creator"]
        author = workshop.author(sid)
        curs = con.cursor(prepared=True)
        curs.execute("INSERT INTO authors VALUES (%s, %s) ON DUPLICATE KEY UPDATE sname = %s", (sid, author, author,))
        curs.execute("INSERT INTO addons VALUES (%s, %s, %s, UNIX_TIMESTAMP(NOW())) ON DUPLICATE KEY UPDATE name = %s, lastup = UNIX_TIMESTAMP(NOW()) ", (wsid, data["title"], sid, data["title"],))

        # Delete our old files.
        curs = con.cursor(prepared=True)
        curs.execute("DELETE FROM files WHERE owner = %s", (wsid,))
        curs.execute("DELETE FROM components WHERE owner = %s", (wsid,))
        curs.execute("DELETE FROM cars WHERE owner = %s", (wsid,))
        curs.execute("DELETE FROM errors WHERE owner = %s", (wsid,))
        con.commit()
        curs.close()
        logging.error("deleted old")

        lua = join(ext, "lua")

        logging.error("walking")
        for rt, dirs, files in walk(lua):
            tld = basename(rt)
            for f in files:
                curs = con.cursor(prepared=True)
                pf = join(rt, f)
                p = normpath(normcase(relpath(join(rt, f), ext)))
                logging.error("checking {}".format(pf))
                curs.execute("INSERT IGNORE INTO files VALUES (%s, %s)", (p, wsid,))

                if tld == "auto":
                    try:
                        comp = subprocess.run(['lua', 'components.lua', pf], capture_output=True, text=True)
                        if comp.returncode != 0:
                            raise subprocess.SubprocessError(comp.stderr)
                        names = [x for x in comp.stdout.strip().split('--##--') if x != '']
                        for name in names:
                            curs.execute("INSERT IGNORE INTO components VALUES (%s, %s)", (name, wsid,))
                    except subprocess.SubprocessError as err:
                        curs.execute("INSERT IGNORE INTO errors VALUES (%s, %s, %s)", (p, str(err), wsid,))

                if tld == "autorun":
                    try:
                        comp = subprocess.run(['lua', 'cars.lua', pf], capture_output=True, text=True)
                        if comp.returncode != 0:
                            raise subprocess.SubprocessError(comp.stderr)
                        names = [x for x in comp.stdout.strip().split('--##--') if x != '']
                        for name in names:
                            curs.execute("INSERT IGNORE INTO cars VALUES (%s, %s)", (name, wsid,))
                    except subprocess.SubprocessError as err:
                        curs.execute("INSERT IGNORE INTO errors VALUES (%s, %s, %s)", (p, str(err), wsid,))

                con.commit()
                curs.close()
        client.queue("WorkshopUpdateResult", args=(wsid, 'complete', data["title"], author))

def workshop_results(args):
    logging.error(args)

w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.register("WorkshopUpdateResult", workshop_results)
w.run()
