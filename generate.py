import sqlite3
import subprocess
import workshop
from gmad import fromgma
from os.path import join, relpath, normpath, normcase, exists, basename
from os.path import getmtime as modtime
from os import walk

conn = sqlite3.connect('photon.db')
curs = conn.cursor()

curs.execute('''CREATE TABLE IF NOT EXISTS "addons" ( `wsid` NUMERIC, `name` TEXT, `author` NUMERIC, PRIMARY KEY(`wsid`) )''')
curs.execute('''CREATE TABLE IF NOT EXISTS "authors" ( `sid` NUMERIC, `sname` TEXT, PRIMARY KEY(`sid`) )''')
curs.execute('''CREATE TABLE IF NOT EXISTS "files" ( `path` TEXT, `owner` NUMERIC )''')
curs.execute('''CREATE TABLE IF NOT EXISTS "components" ( `cname` TEXT, `owner` NUMERIC )''')
curs.execute('''CREATE TABLE IF NOT EXISTS "cars" ( `cname` TEXT, `owner` NUMERIC )''')
curs.execute('''CREATE TABLE IF NOT EXISTS "errors" ( `path` TEXT, `error` TEXT, `owner` NUMERIC )''')
conn.commit()

for data in workshop.search('[Photon]'):
	wsid, sid, url, title, lastup = data['publishedfileid'], data['creator'], data['file_url'], data['title'], data['time_updated']
	gma, ext = wsid + ".gma", wsid + "_extract"

	curs.execute("SELECT sname FROM authors WHERE sid = ?", (sid,))
	author = curs.fetchone()
	if author is None:
		author = workshop.author(sid)
		curs.execute("INSERT INTO authors VALUES (?, ?)", (sid,author,))
	else:
		author = author[0]

	print("Checking '{}' ({}) by '{}' ({})".format(title, wsid, author, sid))
	curs.execute("INSERT OR REPLACE INTO addons VALUES (?, ?, ?)", (wsid, title, sid,))

	if not exists(gma) or modtime(gma) < lastup:
		if not exists(gma):
			print("\tDownloading: NXEST")
		else:
			print("\tDownloading: OUTD")
		workshop.download(url, gma)

	if not exists(ext) or modtime(gma) < lastup:
		if not exists(ext):
			print("\tExtracting: NXEST")
		else:
			print("\tExtracting: OUTD")

		try:
			fromgma.extract_gma(gma, ext)
		except Exception:
			print("\tFile was not GMA.".format(title))
			continue

	lua = join(ext, "lua")

	curs.execute("DELETE FROM files WHERE owner = ?", (wsid,))
	curs.execute("DELETE FROM components WHERE owner = ?", (wsid,))
	curs.execute("DELETE FROM cars WHERE owner = ?", (wsid,))
	curs.execute("DELETE FROM errors WHERE owner = ?", (wsid,))

	for rt, dirs, files in walk(lua):
		tld = basename(rt)
		for f in files:
			pf = join(rt, f)
			p = normpath(normcase(relpath(join(rt, f), ext)))

			curs.execute("SELECT files.path, addons.name FROM files INNER JOIN addons ON files.owner = addons.wsid WHERE path = ? AND owner != ?", (p,wsid,))
			for res in curs:
				print("\tADON-FILE: {}, '{}'!".format(*res))
			curs.execute("INSERT OR IGNORE INTO files VALUES (?, ?)", (p, wsid,))

			if tld == "auto":
				try:
					comp = subprocess.run('lua.exe components.lua "{}"'.format(pf), capture_output = True, text = True)
					if comp.returncode != 0:
						raise subprocess.SubprocessError(comp.stderr)
					names = [x for x in comp.stdout.strip().split('--##--') if x != '']
					for name in names:
						curs.execute("SELECT components.cname, addons.name FROM components INNER JOIN addons ON components.owner = addons.wsid WHERE cname = ? AND owner != ?", (name,wsid,))
						for res in curs:
							print("\tADON-CPMT: '{}', '{}'!".format(*res))
						curs.execute("INSERT OR IGNORE INTO components VALUES (?, ?)", (name, wsid,))
				except subprocess.SubprocessError as err:
					print("\tADON-ERR: '{}'!".format(str(err).replace("\n", "\n\t")))
					curs.execute("INSERT OR IGNORE INTO errors VALUES (?, ?, ?)", (p, str(err), wsid,))

			if tld == "autorun":
				try:
					comp = subprocess.run('lua.exe cars.lua "{}"'.format(pf), capture_output = True, text = True)
					if comp.returncode != 0:
						raise subprocess.SubprocessError(comp.stderr)
					names = [x for x in comp.stdout.strip().split('--##--') if x != '']
					for name in names:
						curs.execute("SELECT cars.cname, addons.name FROM cars INNER JOIN addons ON cars.owner = addons.wsid WHERE cname = ? AND owner != ?", (name,wsid,))
						for res in curs:
							print("\tADON-VEH: '{}', '{}'!".format(*res))
						curs.execute("INSERT OR IGNORE INTO cars VALUES (?, ?)", (name, wsid,))
				except subprocess.SubprocessError as err:
					print("\tADON-ERR: '{}'!".format(str(err).replace("\n", "\n\t")))
					curs.execute("INSERT OR IGNORE INTO errors VALUES (?, ?, ?)", (p, str(err), wsid,))

	conn.commit()