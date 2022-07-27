from logging import warning, debug

from discord_webhook import DiscordWebhook
from environs import Env

import workshop
from runner.jobs import DatabaseJob

env = Env()


class RunnerJob(DatabaseJob):
	def handle(self):
		handler = list(self.type)
		for id in range(len(handler)):
			char = handler[id]
			if char.isupper():
				handler[id] = f"_{char.lower()}"
		handler = f"handle{''.join(handler)}"
		handler = getattr(self, handler, None)

		if handler == "handle":
			return False

		if callable(handler):
			handler()
			return True
		else:
			warning(f"Missing Handler for {self.type}")
			return False

	def message(self, message: str) -> 'RunnerJob':
		return self.new(self.cursor, "StatusMessage", message)

	def author(self, community_id: int):
		debug("Updating author %s", community_id)
		self.cursor.execute(
			"SELECT NOW() > DATE_ADD(updated_at, INTERVAL 14 DAY) AS outdated FROM authors WHERE sid = %s;",
			(community_id,))
		outdated = self.cursor.fetchone()
		outdated = True if outdated is None else outdated[0] == 1

		if not outdated:
			return

		author = workshop.author(community_id)
		self.cursor.execute(
			"INSERT INTO authors (sid, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = %s, updated_at = NOW();",
			(community_id, author, author))
		self.cursor.execute("COMMIT")

	def handle_status_message(self):
		DiscordWebhook(
			url=env.str("DISCORD_WEBHOOK"),
			username="Bot Update Worker",
			content=str(self.data)
		).execute()

	def handle_update_author(self):
		self.author(int(self.data))
