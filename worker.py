from steam.monkey import patch_minimal
patch_minimal()

from runner.jobs import JobManager
from runner.jobs.RunnerJob import RunnerJob

import logging
import datetime
import os
import subprocess
from os import walk, remove
from os.path import join, relpath, normpath, normcase, basename, abspath, dirname, exists
from typing import Optional, Union
from shutil import rmtree
from time import sleep

from mysql.connector import connect
from steam.client import SteamClient
from steam.client.cdn import CDNClient
from environs import Env
from discord_webhook import DiscordWebhook

from gmad.file_ext import File
import workshop
from gmad import fromgma

env = Env()
env.read_env()

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("SteamClient").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)

dbConnection = connect(
	host=os.environ['MYSQL_HOST'],
	port=os.environ['MYSQL_PORT'],
	user=os.environ['MYSQL_USER'],
	password=os.environ['MYSQL_PASS'],
	database=os.environ['MYSQL_DB']
)
dbCursor = dbConnection.cursor()
dbCursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;")
dbCursor.execute("SET CHARACTER SET utf8mb4;")

steam = SteamClient()
steam.anonymous_login()
net = CDNClient(steam)


class ClearAddon:
	workshop_id: int

	def __init__(self, workshop_id: int):
		self.workshop_id = workshop_id

	def __enter__(self):
		dbCursor.execute("START TRANSACTION")
		dbCursor.execute("DELETE FROM addons WHERE wsid = %s", (self.workshop_id,))

	def __exit__(self, exc_type, exc_val, exc_tb):
		if exc_type is not None:
			logging.debug("Rolling Back")
			dbCursor.execute("ROLLBACK")
		else:
			dbCursor.execute("COMMIT")
			return True


blocked_jobs = set()
blocked_types = set()
blocks = []
where = ""

manager = JobManager(dbConnection, RunnerJob)


def block(block: Union[int, str]):
	global where, blocks
	if isinstance(block, int):
		blocked_jobs.add(block)
	else:
		blocked_types.add(block)
	blocks = list(blocked_jobs)
	blocks.extend(blocked_types)

	where = []
	if len(blocked_jobs) != 0:
		where.append(f"id NOT IN ({', '.join(['%s'] * len(blocked_jobs))})")
	if len(blocked_types) != 0:
		where.append(f"type NOT IN ({', '.join(['%s'] * len(blocked_types))})")
	where = "" if len(where) == 0 else f"AND {' AND '.join(where)}"


def job():
	global where, blocks
	dbCursor.execute(f"SELECT * FROM jobs WHERE status = 'new' {where} ORDER BY FIELD(type, 'StatusMessage') DESC, ID ASC LIMIT 1 FOR UPDATE", blocks)
	jobs = dbCursor.fetchall()
	for job in jobs:
		dbCursor.execute("UPDATE jobs SET status = 'locked' WHERE id = %s", (job[0],))
		dbCursor.execute("COMMIT")
		return job
	dbCursor.execute("COMMIT")


def unlock(job_id: int):
	dbCursor.execute("UPDATE jobs SET status = 'new' WHERE id = %s", (job_id,))
	dbCursor.execute("COMMIT")


def queue(type: str, data: Optional[str] = None):
	if data is None:
		dbCursor.execute("INSERT INTO jobs (type) VALUES (%s);", (type,))
	else:
		dbCursor.execute("INSERT INTO jobs (type, data) VALUES (%s, %s);", (type, data,))
	dbCursor.execute("COMMIT")


def done(jobId: int):
	dbCursor.execute("UPDATE jobs SET status = 'done' WHERE id = %s;", (jobId,))


def author(community_id: int):
	logging.debug("Updating author %s", community_id)
	dbCursor.execute("SELECT NOW() > DATE_ADD(updated_at, INTERVAL 14 DAY) AS outdated FROM authors WHERE sid = %s;", (community_id,))
	outdated = dbCursor.fetchone()
	outdated = True if outdated is None else outdated[0] == 1

	if not outdated:
		return

	author = workshop.author(community_id)
	dbCursor.execute("INSERT INTO authors (sid, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = %s, updated_at = NOW();", (community_id, author, author))
	dbCursor.execute("COMMIT")


def workshop_scan_addon(wsid: int, basedir: str):
	luadir = join(basedir, "lua")

	for rt, dirs, files in walk(luadir):
		tld = basename(rt)
		for f in files:
			pf = join(rt, f)
			p = normpath(normcase(relpath(join(rt, f), basedir)))
			dbCursor.execute("INSERT IGNORE INTO files VALUES (%s, %s)", (p, wsid,))

			if tld == "auto":
				try:
					comp = subprocess.run(['lua', 'components.lua', pf], capture_output=True, text=True)
					if comp.returncode != 0:
						raise subprocess.SubprocessError(comp.stderr)
					names = [x for x in comp.stdout.strip().split('--##--') if x != '']
					for name in names:
						dbCursor.execute("INSERT IGNORE INTO components VALUES (%s, %s)", (name, wsid,))
				except subprocess.SubprocessError as err:
					dbCursor.execute("INSERT IGNORE INTO errors VALUES (%s, %s, %s)", (p, str(err), wsid,))

			if tld == "autorun":
				try:
					comp = subprocess.run(['lua', 'cars.lua', pf], capture_output=True, text=True)
					if comp.returncode != 0:
						raise subprocess.SubprocessError(comp.stderr)
					names = [x for x in comp.stdout.strip().split('--##--') if x != '']
					for name in names:
						dbCursor.execute("INSERT IGNORE INTO vehicles VALUES (%s, %s)", (name, wsid,))
				except subprocess.SubprocessError as err:
					dbCursor.execute("INSERT IGNORE INTO errors VALUES (%s, %s, %s)", (p, str(err), wsid,))


def workshop_update_steampipe(wsid: int, addon: dict):
	logging.debug("Running SteamPipe update for %s.", wsid)

	manifest = net.get_manifest_for_workshop_item(int(wsid))
	tmpdir = abspath(join(".", "tmp"))
	files = list(manifest.iter_files())
	basedir = join(tmpdir, f"{wsid}_extract")
	if len(files) == 1:
		file = files[0]
		gma = abspath(join(tmpdir, f"{wsid}.gma"))
		with open(gma, "wb") as out:
			reading = True
			while reading:
				data = file.read(1024)
				if not data:
					reading = False
				else:
					out.write(data)
		fromgma.extract_gma(gma, basedir)
		remove(gma)
	else:
		basedir = f"{wsid}_extract"
		for file in manifest.iter_files():
			filepath = join(basedir, file.filename)
			filedir = dirname(filepath)
			if not exists(filedir):
				os.mkdir(filedir)
			with open(filepath, "wb") as out:
				reading = True
				while reading:
					data = file.read(1024)
					if not data:
						reading = False
					else:
						out.write(data)
	workshop_scan_addon(wsid, basedir)
	rmtree(basedir)


def workshop_update_legacy(wsid: int, data: dict):
	logging.debug("Running legacy update for %s.", wsid)
	if not data["filename"].endswith(".gma") and not data["filename"].endswith(".gm"):
		return queue("StatusMessage", f"{data.get('title', wsid)} does not contain a .gma file.")

	gma, ext = abspath(join(".", "tmp", f"{wsid}.gma")), abspath(join(".", "tmp", f"{wsid}_extract"))
	# Download / Extract our addon.
	workshop.download(data["file_url"], gma)
	fromgma.extract_gma(gma, ext)
	workshop_scan_addon(wsid, ext)

	remove(gma)
	rmtree(ext)


def workshop_update(wsid: int, forced: bool = False):
	forced = True
	data = workshop.query(wsid)
	logging.debug(data)

	if data["result"] != 1:
		return queue("StatusMessage", f"{wsid} failed to update, steam returned no result.")

	if data["banned"] != 0:
		return queue("StatusMessage", f"{data.get('title', wsid)} was banned.")

	if (data["creator_app_id"] != 4000 and data["creator_app_id"] != 4020) or (data["consumer_app_id"] != 4000 and data["consumer_app_id"] != 4020):
		return queue("StatusMessage", f"{data.get('title', wsid)} is not on the garry's mod workshop.")

	dbCursor.execute("SELECT updated_at FROM addons WHERE wsid = %s", (wsid,))
	updated_at = dbCursor.fetchone()

	is_new = True
	if updated_at is not None:
		updated_at: datetime.datetime = updated_at[0]
		is_new = datetime.datetime.fromtimestamp(data["time_updated"]) > updated_at

	if not is_new and not forced:
		return queue("StatusMessage", f"{data.get('title', wsid)} has not been changed since the last read.")

	author(data["creator"])

	with ClearAddon(wsid):
		dbCursor.execute("INSERT INTO addons (wsid, name, author) VALUES (%s, %s, %s)", (wsid, data['title'], data['creator']))

		if data["file_url"] == "":
			workshop_update_steampipe(wsid, data)
		else:
			workshop_update_legacy(wsid, data)

	return queue("StatusMessage", f"{data.get('title', wsid)} has been succesfully updated.")


def scan():
	for data in workshop.search('[Photon]'):
		if data['result'] == 1:
			author(data["creator"])
			queue("UpdateAddon", data["publishedfileid"])


print("started")
for job in manager.consume():
	jobId = job.id
	jobType = job.type
	jobData = job.data

	handled = False
	failed = False

	try:
		if job.handle():
			handled = True
		elif jobType == "UpdateAddon":
			workshop_update(jobData)
		elif jobType == "Scan":
			scan()
		else:
			handled = False
	except Exception as e:
		logging.error(e)
		logging.error(e.__traceback__)
		failed = True
		handled = False

	if handled:
		job.done()
	elif failed:
		manager.block(jobId)
		job.unlock()
	else:
		manager.block(jobType)
		job.unlock()
