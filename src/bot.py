import traceback

import discord
from discord.ext import tasks

from app import App
from logger import logger


class Bot(discord.Bot):
	def __init__(self) -> None:
		# くらいあんと
		self.client = discord.Bot(intents=None)
		"""クライアント"""

		self.presence_status_index: int = 0
		"""現在表示中のステータスのインデックス"""
		self.PRESENCE_STATUS_LIST: list[str] = [
			"Type /help | v{0}",
			"Servers: {1} | Embeds: {2}",
		]
		"""表示するステータスの文字列一覧"""

	@tasks.loop(hours=1)
	async def update_info(self) -> None:
		try:
			logger.info("BotのバナーURLを更新")
			if self.client.user.id is None:
				return
			App.bot_banner_url = (await self.client.fetch_user(self.client.user.id)).banner.url or None
		except Exception:
			App.bot_banner_url = None
			logger.error("BotのバナーURLの取得に失敗")
			logger.error(traceback.format_exc())

	# 5秒ごとにステータス表示を更新する
	@tasks.loop(seconds=5)
	async def update_presence_status(self) -> None:
		try:
			# ステータス表示を更新
			await self.client.change_presence(
				activity=discord.Game(
					name=self.PRESENCE_STATUS_LIST[self.presence_status_index].format(
						App.VERSION_STRING,
						str(len(self.client.guilds)),
						str(self.client.get_cog("ServerStatusEmbedManager").server_status_embeds_count),
					)
				),
			)
			if self.presence_status_index == len(self.PRESENCE_STATUS_LIST) - 1:
				self.presence_status_index = 0
			else:
				self.presence_status_index += 1
		except Exception:
			logger.error("ステータス表示の更新に失敗")
			logger.error(traceback.format_exc())
