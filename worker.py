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
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'no result'), queue='results')

        if data["banned"] != 0:
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'item banned'), queue='results')

        if data["creator_app_id"] != 4000 or data["consumer_app_id"] != 4000:
            client.queue("WorkshopUpdate", args=(wsid, 'failure', 'not gmod'), queue='results')

        if not data["filename"].endswith(".gma"):
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
        curs.close()

        # DL / Extract our addon.
        workshop.download(data["file_url"], "worker.gma")
        fromgma.extract_gma("worker.gma", "worker")

        # And fetch our author.
        sid = data["creator"]
        author = workshop.author(sid)
        curs = con.cursor(prepared=True)
        curs.execute("INSERT INTO authors VALUES (%s, %s) ON DUPLICATE KEY UPDATE SET sname = %s ", (sid, author, author,))
        curs.execute("INSERT INTO addons VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE SET name = %s, lastup = UNIX_TIMESTAMP(NOW()) ", (wsid, data["title"], sid, data["title"],))
        curs.close()


        # Delete our old files.
        curs = con.cursor(prepared=True)
        curs.execute("DELETE FROM files WHERE owner = %s", (wsid,))
        curs.execute("DELETE FROM components WHERE owner = %s", (wsid,))
        curs.execute("DELETE FROM cars WHERE owner = %s", (wsid,))
        curs.execute("DELETE FROM errors WHERE owner = %s", (wsid,))
        curs.close()

        gma, ext = wsid + ".gma", wsid + "_extract"
        lua = join(ext, "lua")

        for rt, dirs, files in walk(lua):
            tld = basename(rt)
            for f in files:
                pf = join(rt, f)
                p = normpath(normcase(relpath(join(rt, f), ext)))

                curs.execute(
                    "SELECT files.path, addons.name FROM files INNER JOIN addons ON files.owner = addons.wsid WHERE path = %s AND owner != ?",
                    (p, wsid,))
                for res in curs:
                    print("\tADON-FILE: {}, '{}'!".format(*res))
                curs.execute("INSERT IGNORE INTO files VALUES (%s, %s)", (p, wsid,))

                if tld == "auto":
                    try:
                        comp = subprocess.run('lua components.lua "{}"'.format(pf), capture_output=True, text=True)
                        if comp.returncode != 0:
                            raise subprocess.SubprocessError(comp.stderr)
                        names = [x for x in comp.stdout.strip().split('--##--') if x != '']
                        for name in names:
                            curs.execute(
                                "SELECT components.cname, addons.name FROM components INNER JOIN addons ON components.owner = addons.wsid WHERE cname = %s AND owner != %s",
                                (name, wsid,))
                            for res in curs:
                                print("\tADON-CPMT: '{}', '{}'!".format(*res))
                            curs.execute("INSERT IGNORE INTO components VALUES (%s, %s)", (name, wsid,))
                    except subprocess.SubprocessError as err:
                        print("\tADON-ERR: '{}'!".format(str(err).replace("\n", "\n\t")))
                        curs.execute("INSERT IGNORE INTO errors VALUES (%s, %s, %s)", (p, str(err), wsid,))

                if tld == "autorun":
                    try:
                        comp = subprocess.run('lua cars.lua "{}"'.format(pf), capture_output=True, text=True)
                        if comp.returncode != 0:
                            raise subprocess.SubprocessError(comp.stderr)
                        names = [x for x in comp.stdout.strip().split('--##--') if x != '']
                        for name in names:
                            curs.execute(
                                "SELECT cars.cname, addons.name FROM cars INNER JOIN addons ON cars.owner = addons.wsid WHERE cname = %s AND owner != %s",
                                (name, wsid,))
                            for res in curs:
                                print("\tADON-VEH: '{}', '{}'!".format(*res))
                            curs.execute("INSERT IGNORE INTO cars VALUES (%s, %s)", (name, wsid,))
                    except subprocess.SubprocessError as err:
                        print("\tADON-ERR: '{}'!".format(str(err).replace("\n", "\n\t")))
                        curs.execute("INSERT IGNORE INTO errors VALUES (%s, %s, %s)", (p, str(err), wsid,))
        curs.close()
        client.queue("WorkshopUpdate", args=(wsid, 'complete', data["name"], author), queue='results')



w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
