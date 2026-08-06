import copy
from typing import ClassVar

from box import Box

from client import bot
from db import DBManager
from kumasan import KumaSan
from logger import logger


class GuildConfigManager:
	"""各ギルドのコンフィグを管理するクラス"""

	DEFAULT_DB_DATA: ClassVar[dict] = {"guild_id": "", "config": {}}
	DEFAULT_GUILD_DATA: ClassVar[dict] = {
		"server_status_message": {
			"channel_id": "0",
			"message_id": "0",
			"language": "en_GB",
			"status_indicator": True,
			"maintenance_schedule": True,
		},
		"server_status_notification": {
			"channel_id": "0",
			"role_id": "0",
			"auto_delete": 10,
		},
	}

	@classmethod
	def generate_default_guild_data(cls, guild_id: str | int) -> dict:
		"""初期ギルドコンフィグを生成して返す"""
		d = copy.deepcopy(cls.DEFAULT_DB_DATA)
		d["guild_id"] = str(guild_id)
		d["config"] = copy.deepcopy(cls.DEFAULT_GUILD_DATA)
		return d

	@classmethod
	async def _check_dict_items(cls, item: dict, default_items: dict) -> dict:
		for k, v in default_items.items():
			if k not in item:
				item[k] = v
			if isinstance(item[k], dict):
				await cls._check_dict_items(item[k], default_items[k])
		return item

	@classmethod
	async def check(cls) -> None:
		"""各ギルドのコンフィグをチェックする 存在しなければ新規作成する"""
		logger.info("ギルドコンフィグをチェック")

		# コンフィグファイルの各ギルドの項目チェック
		for guild in bot.client.guilds:
			gid = str(guild.id)
			logger.info("- ID: %s", gid)
			# データベースからIDに一致するコンフィグを取得する
			gd = await DBManager.col.find_one({"guild_id": gid})
			if gd is None:
				# 見つからない場合は新規作成する
				await cls.create(gid)
			# なんらかの理由で config だけが存在しない場合も新規作成する
			elif not gd.get("config"):
				await cls.create(gid)
			else:
				# チェックしたコンフィグに更新する
				await DBManager.col.update_one(
					{"guild_id": gid},
					{
						"$set": {
							"config": (
								await cls._check_dict_items(
									gd.get("config"),
									copy.deepcopy(cls.DEFAULT_GUILD_DATA),
								)
							),
						},
					},
				)

	@classmethod
	async def load(cls) -> None:
		"""ギルドコンフィグをデータベースから読み込んでチェックする"""
		logger.info("ギルドコンフィグを読み込み")

		# 各項目のチェック
		await cls.check()

	@classmethod
	async def create(cls, guild_id: str | int) -> None:
		"""指定されたギルドIDのコンフィグを新規作成する"""
		guild_id = str(guild_id)

		logger.info("ギルドコンフィグを新規作成: %s", guild_id)
		await DBManager.col.update_one(
			{"guild_id": guild_id},
			{"$set": cls.generate_default_guild_data(guild_id)},
			upsert=True,
		)

	@classmethod
	async def delete(cls, guild_id: str | int) -> None:
		"""指定されたギルドIDのコンフィグを削除する"""
		guild_id = str(guild_id)

		logger.info("ギルドコンフィグを削除: %s", guild_id)
		await DBManager.col.delete_one({"guild_id": guild_id})

	@classmethod
	async def get(cls, guild_id: str | int) -> Box | None:
		"""指定されたギルドIDのコンフィグを取得して返す"""
		guild_id = str(guild_id)

		logger.info("ギルドコンフィグを取得 - ID: %s", guild_id)

		# データベースから指定されたギルドIDに一致するコンフィグを取得する
		obj = await DBManager.col.find_one({"guild_id": guild_id})

		# 見つからない場合は初期値を新たに作成する
		if obj is None:
			await cls.create(guild_id)
			obj = await DBManager.col.find_one({"guild_id": guild_id})
			if obj is None:
				logger.warning("ギルドコンフィグの取得失敗: obj is None")
				await KumaSan.ping("pending", "ギルドコンフィグの取得失敗: obj is None")
				return None

		if obj.get("config") is None:
			logger.warning("ギルドコンフィグの取得失敗: config is None")
			await KumaSan.ping("pending", "ギルドコンフィグの取得失敗: config is None")
			return None

		return Box(obj["config"])

	@classmethod
	async def update(cls, guild_id: str | int, value: Box) -> bool:
		"""指定されたギルドIDのコンフィグを更新する

		ギルドIDに一致するコンフィグが見つからない場合は `False` を返す
		"""
		guild_id = str(guild_id)

		result = await DBManager.col.update_one(
			{"guild_id": guild_id},
			{"$set": {"config": value.to_dict()}},
		)
		logger.info(
			"ギルドコンフィグを更新 - ID: %s | Matched: %d | Modified: %d",
			guild_id,
			result.matched_count,
			result.modified_count,
		)

		if result.matched_count == 0:
			logger.warning("- ギルドコンフィグの更新失敗")
			await KumaSan.ping("pending", "ギルドコンフィグの更新失敗")

		return result.matched_count != 0
