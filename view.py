from shutil import copy
import sqlite3
import sys

sys.stdout = open("report.txt", "w", encoding="utf8")

copy('photon.db', 'photon.read.db')
conn = sqlite3.connect('photon.read.db')
curs = conn.cursor()

curs.execute("SELECT * FROM (SELECT path, COUNT(*) as count FROM files GROUP BY path) WHERE count > 1 ORDER BY count ASC, path ASC")
for reply in curs:
	print("\nLua Path '{}' has been seen in {} addons.".format(*reply))
	inner = conn.cursor()
	inner.execute("SELECT path, owner, name, author, sname FROM files INNER JOIN addons ON files.owner = addons.wsid INNER JOIN authors ON addons.author = authors.sid WHERE path = ? ORDER BY wsid ASC", (reply[0],))
	for addon in inner:
		print("\tSeen in: '{2}' ({1}) by '{4}' ({3}).".format(*addon))

curs.execute("SELECT * FROM (SELECT cname, COUNT(*) as count FROM cars GROUP BY cname) WHERE count > 1 ORDER BY count ASC, cname ASC")
for reply in curs:
	print("\nVehicle ID '{}' has been seen in {} addons.".format(*reply))
	inner = conn.cursor()
	inner.execute("SELECT cname, owner, name, author, sname FROM cars INNER JOIN addons ON cars.owner = addons.wsid INNER JOIN authors ON addons.author = authors.sid WHERE cname = ? ORDER BY wsid ASC", (reply[0],))
	for addon in inner:
		print("\tSeen in: '{2}' ({1}) by '{4}' ({3}).".format(*addon))

curs.execute("SELECT * FROM (SELECT cname, COUNT(*) as count FROM components GROUP BY cname) WHERE count > 1 ORDER BY count ASC, cname ASC")
for reply in curs:
	print("\nComponent '{}' has been seen in {} addons.".format(*reply))
	inner = conn.cursor()
	inner.execute("SELECT cname, owner, name, author, sname FROM components INNER JOIN addons ON components.owner = addons.wsid INNER JOIN authors ON addons.author = authors.sid WHERE cname = ? ORDER BY wsid ASC", (reply[0],))
	for addon in inner:
		print("\tSeen in: '{2}' ({1}) by '{4}' ({3}).".format(*addon))

# curs.execute("SELECT * FROM files INNER JOIN addons ON files.owner = addons.wsid WHERE owner IN (SELECT wsid FROM addons WHERE author = 76561198166686412)")
# for reply in curs:
# 	inner = conn.cursor()
# 	inner.execute("SELECT path, owner, name, author, sname FROM files INNER JOIN addons ON files.owner = addons.wsid INNER JOIN authors ON addons.author = authors.sid WHERE path = ? ORDER BY wsid ASC", (reply[0],))
# 	# res = inner.fetchone()
# 	# if res is not None:
# 	# 	print("Lua Path '{0}'.".format(*reply))
# 	# 	print("\tSeen in: '{2}' ({1}) by '{4}' ({3}).".format(*res))
# 	for reply in curs:
# 		print("\nLua Path '{}' has been seen in {} addons.".format(*reply))
# 		inner = conn.cursor()
# 		inner.execute("SELECT path, owner, name, author, sname FROM files INNER JOIN addons ON files.owner = addons.wsid INNER JOIN authors ON addons.author = authors.sid WHERE path = ? ORDER BY wsid ASC", (reply[0],))
# 		for addon in inner:
# 			print("\tSeen in: '{2}' ({1}) by '{4}' ({3}).".format(*addon))
