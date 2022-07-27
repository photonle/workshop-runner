from enum import Enum
from time import sleep
from typing import Optional, Any, Set, Union, List, Tuple, Iterator
from datetime import datetime

from mysql.connector import CMySQLConnection, MySQLConnection
from mysql.connector.cursor_cext import CMySQLCursor


class JobStatus(Enum):
	NEW = "new"
	LOCKED = "locked"
	DONE = "done"


class Job:
	id: int
	status: JobStatus
	type: str
	data: Optional[Any]
	created_at: datetime
	updated_at: datetime

	def __init__(self, id: int, status: JobStatus, type: str, created_at: datetime, updated_at: datetime, data: Optional[Any] = None):
		self.id = int(id)
		self.status = status
		self.type = type
		self.data = data
		self.created_at = created_at
		self.updated_at = updated_at


class DatabaseJob(Job):
	cursor: CMySQLCursor

	def __init__(self, row: Tuple[int, str, str, Optional[str], datetime, datetime], cursor: CMySQLCursor):
		super().__init__(row[0], JobStatus(row[1]), row[2], row[4], row[5], row[3])
		self.cursor = cursor

	@classmethod
	def new(cls, cursor: CMySQLCursor, type: str, data: Optional[Any] = None) -> 'DatabaseJob':
		if data is None:
			cursor.execute("INSERT INTO jobs (type) VALUES (%s);", (type,))
		else:
			cursor.execute("INSERT INTO jobs (type, data) VALUES (%s, %s);", (type, str(data),))
		cursor.execute("SELECT * FROM jobs WHERE id = LAST_INSERT_ID()")
		rows = cursor.fetchall()
		return cls(rows[0], cursor)

	def set_status(self, status: JobStatus, auto_commit: bool = True) -> 'DatabaseJob':
		self.cursor.execute("UPDATE jobs SET status = %s WHERE id = %s", (status.value, self.id,))
		if auto_commit:
			self.cursor.execute("COMMIT")
		return self

	def lock(self, auto_commit: bool = True) -> 'DatabaseJob':
		return self.set_status(JobStatus.LOCKED, auto_commit)

	def done(self, auto_commit: bool = True) -> 'DatabaseJob':
		return self.set_status(JobStatus.DONE, auto_commit)

	def unlock(self, auto_commit: bool = True) -> 'DatabaseJob':
		return self.set_status(JobStatus.NEW, auto_commit)


class JobManager:
	blocked_jobs: Set[int] = set()
	blocked_types: Set[str] = set()
	blocks: List[Union[int, str]] = []
	where: str = ""
	cursor: CMySQLCursor

	def __init__(self, connection: Union[CMySQLConnection, MySQLConnection]):
		self.cursor = connection.cursor()

	def block(self, block: Union[int, str]):
		if isinstance(block, int):
			self.blocked_jobs.add(block)
		else:
			self.blocked_types.add(block)
		self.blocks = list(self.blocked_jobs)
		self.blocks.extend(self.blocked_types)

		where = []
		if len(self.blocked_jobs) != 0:
			where.append(f"id NOT IN ({', '.join(['%s'] * len(self.blocked_jobs))})")
		if len(self.blocked_types) != 0:
			where.append(f"type NOT IN ({', '.join(['%s'] * len(self.blocked_types))})")
		self.where = "" if len(where) == 0 else f"AND {' AND '.join(where)}"

	def next(self) -> Optional[DatabaseJob]:
		self.cursor.execute("START TRANSACTION;")
		self.cursor.execute(
			f"""
				SELECT
					*
				FROM
					jobs
				WHERE
					status = 'new'
					{self.where}
				ORDER BY
					FIELD(type, 'StatusMessage') DESC,
					ID ASC
				LIMIT
					1
				FOR UPDATE;
			""", self.blocks)
		jobs = self.cursor.fetchall()

		if len(jobs) == 0:
			self.cursor.execute("COMMIT")
			return None

		return DatabaseJob(jobs[0], self.cursor).lock()

	def consume(self) -> Iterator[DatabaseJob]:
		while True:
			job = self.next()
			if job:
				yield job
			else:
				sleep(5)
			sleep(1)
