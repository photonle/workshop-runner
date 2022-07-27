from logging import debug

from mysql.connector.cursor_cext import CMySQLCursor


class ClearAddon:
	cursor: CMySQLCursor
	workshop_id: int

	def __init__(self, cursor: CMySQLCursor, workshop_id: int):
		self.cursor = cursor
		self.workshop_id = workshop_id

	def __enter__(self):
		self.cursor.execute("START TRANSACTION")
		self.cursor.execute("DELETE FROM addons WHERE wsid = %s", (self.workshop_id,))

	def __exit__(self, exc_type, exc_val, exc_tb):
		if exc_type is not None:
			debug("Rolling Back")
			self.cursor.execute("ROLLBACK")
		else:
			self.cursor.execute("COMMIT")
			return True