import subprocess
from os import walk, remove

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
from discord_webhook import DiscordWebhook
from shutil import rmtree
from time import time

logging.basicConfig(level=logging.DEBUG)

def workshop_update(args):
    with faktory.connection() as client:
        wsid = args["wsid"]
        forced = args["force"]

        data = workshop.query(wsid)
        logging.debug(data)

        if data["result"] != 1:
            client.queue("WorkshopUpdateFailed", args=({"wsid": wsid, "reason": 'no result'},), priority=10)
            return

        if data["banned"] != 0:
            client.queue("WorkshopUpdateFailed", args=({"wsid": wsid, "reason": 'banned', "title": data["title"]},), priority=10)
            return

        if data["creator_app_id"] != 4000 or data["consumer_app_id"] != 4000:
            client.queue("WorkshopUpdateFailed", args=({
               "wsid": wsid,
               "reason": 'not gmod',
               "title": data["title"],
               "creator": data["creator_app_id"],
               "consumer": data["consumer_app_id"]
           },), priority=10)
            return

        if not data["filename"].endswith(".gma"):
            client.queue("WorkshopUpdateFailed", args=({
                "wsid": wsid,
                "reason": 'not gma',
                "title": data["title"],
                "file": data["filename"]
            },), priority=10)
            return

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
        if lastup is not None and int(lastup[0]) <= int(time()) and not forced:
            client.queue("WorkshopUpdateFailed", args=(wsid, 'not updated'), priority=10)
            return

        curs.close()
        logging.error("running")

        gma, ext = wsid + ".gma", wsid + "_extract"
        # DL / Extract our addon.
        workshop.download(data["file_url"], gma)
        fromgma.extract_gma(gma, ext)

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

        lua = join(ext, "lua")

        for rt, dirs, files in walk(lua):
            tld = basename(rt)
            for f in files:
                curs = con.cursor(prepared=True)
                pf = join(rt, f)
                p = normpath(normcase(relpath(join(rt, f), ext)))
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
        remove(gma)
        rmtree(ext)
        client.queue("WorkshopUpdateComplete", args=(wsid, data["title"], author), priority=7)


def workshop_results_failed(data):
    reason = data["reason"]
    reasonStr = "for an unknown reason"
    if reason == "no result":
        reasonStr = "because the item could not be found"
    elif reason == "item banned":
        reasonStr = "because the item was banned from the steam workshop"
    elif reason == "not gmod":
        reasonStr = "because the item wasn't a gmod addon (creator {}, consumer {})".format(data["creator"], data["consumer"])
    elif reason ==  "not gma":
        reasonStr = "because the item was packaged incorrectly ({})".format(data["file"])
    elif reason == "not updated":
        reasonStr = "because the addon hasn't been updated since it was last read"

    nameStr = data["wsid"]
    if "title" in data:
        nameStr = "{} ({})".format(data["title"], data["wsid"])

    DiscordWebhook(
        url=env.str("DISCORD_WEBHOOK"),
        username="Bot Update Worker",
        content="The update for {} failed {}.".format(nameStr, reasonStr)
    ).execute()

def workshop_results_success(wsid, title, author):
    DiscordWebhook(
        url=env.str("DISCORD_WEBHOOK"),
        username="Bot Update Worker",
        content="The update for {} ({}) by {} succeded!".format(title, wsid, author)
    ).execute()

def workshop_queued(wsid, title):
    DiscordWebhook(
        url=env.str("DISCORD_WEBHOOK"),
        username="Bot Update Worker",
        content="[Bulk Update] Queued {} ({}).".format(title, wsid)
    ).execute()

def workshop_update_bulk(args):
    with faktory.connection() as client:
        for data in workshop.search('[Photon]'):
            client.queue("WorkshopUpdateQueued", args=(data["publishedfileid"], data["title"]))
            client.queue("UpdateWorkshop", args=({"wsid": data["publishedfileid"]},), priority=8)

w = Worker(concurrency=5)
w.register("UpdateWorkshop", workshop_update)
w.register("WorkshopUpdateFailed", workshop_results_failed)
w.register("WorkshopUpdateComplete", workshop_results_success)
w.register("WorkshopUpdateQueued", workshop_queued)
w.register("UpdateAllWorkshop", workshop_update_bulk)
w.run()
