import asyncio
import time
import traceback

import discord
import r6sss
from box import Box
from discord.ext import commands, tasks

import embeds
import icons
import localizations
from client import bot
from config import GuildConfigManager
from db import DBManager
from kumasan import KumaSan
from localizations import Localization
from logger import logger
from maintenance_schedule import MaintenanceScheduleManager
from owner_message import GuildOwnerAnnounceUtil
from server_status import ServerStatusManager


class ServerStatusEmbedManager(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot
		self.server_status_update_loop_is_running: bool = False
		self.update_all.start()
		self.status_embeds: dict[str, list[list[discord.Embed]]] = {}
		self.server_status_embeds_count: int = 0
		self.server_status_embeds_update_time: float = 0.0
		"""作成されたサーバーステータス埋め込みメッセージの総数 (全ギルドの合計)"""

	def _check_data_changed(
		self,
		status_data: list[r6sss.types.Status] | None,
		schedule_data: dict[str, r6sss.types.MaintenanceSchedule] | None,
	) -> bool:
		"""データに変更があったかどうかを確認する"""
		# 初回実行時
		if ServerStatusManager.previous_data is None:
			logger.info("初回実行: 以前のデータが存在しません")
			return True

		# Noneチェック
		if (status_data is None) != (ServerStatusManager.previous_data is None):
			logger.info("変更検知: サーバーステータスのデータの有無が変化しました")
			return True

		# サーバーステータスの比較
		# 要素数が異なる場合は変更あり
		if len(ServerStatusManager.previous_data) != len(status_data):
			logger.info("変更検知: サーバーステータスの要素数が変化しました")
			return True

		for i, status in enumerate(status_data):
			prev = ServerStatusManager.previous_data[i]
			# 必要なフィールドのみ比較
			if (
				prev.platform != status.platform
				or prev.connectivity != status.connectivity
				or prev.maintenance != status.maintenance
				or prev.authentication != status.authentication
				or prev.matchmaking != status.matchmaking
				or prev.purchase != status.purchase
			):
				logger.info("変更検知: サーバーステータス (%s)", status.platform)
				if prev.platform != status.platform:
					logger.info("- Platform: %s -> %s", prev.platform, status.platform)
				if prev.connectivity != status.connectivity:
					logger.info("- Connectivity: %s -> %s", prev.connectivity, status.connectivity)
				if prev.maintenance != status.maintenance:
					logger.info("- Maintenance: %s -> %s", prev.maintenance, status.maintenance)
				if prev.authentication != status.authentication:
					logger.info("- Authentication: %s -> %s", prev.authentication, status.authentication)
				if prev.matchmaking != status.matchmaking:
					logger.info("- Matchmaking: %s -> %s", prev.matchmaking, status.matchmaking)
				if prev.purchase != status.purchase:
					logger.info("- Purchase: %s -> %s", prev.purchase, status.purchase)
				return True

		# メンテナンススケジュールの比較
		# Noneの場合は空の辞書として扱う
		prev_schedules = MaintenanceScheduleManager.previous_data or {}
		schedules = schedule_data or {}

		# 言語数が異なる場合は変更あり
		if len(prev_schedules) != len(schedules):
			logger.info("変更検知: メンテナンススケジュールの言語数が変化しました")
			return True

		# 各言語のメンテナンススケジュールの比較
		for lang, schedule in schedules.items():
			# 言語キーが存在しない場合は追加とみなす
			if lang not in prev_schedules:
				logger.info("変更検知: メンテナンススケジュールに新規言語 (%s) が追加されました", lang)
				return True

			prev_schedule = prev_schedules[lang]

			# 両方ともNoneの場合は変更なし
			if prev_schedule is None and schedule is None:
				continue

			# 片方だけNoneの場合は変更あり
			if (prev_schedule is None) != (schedule is None):
				logger.info("変更検知: メンテナンススケジュールの有無が変化しました (%s)", lang)
				return True

			# ここに来る時点で両方ともNoneではないので比較を行う
			if (
				prev_schedule.title != schedule.title
				or prev_schedule.detail != schedule.detail
				or prev_schedule.downtime != schedule.downtime
				or prev_schedule.date != schedule.date
				or [p.name for p in prev_schedule.platforms] != [p.name for p in schedule.platforms]
				or prev_schedule.patchnotes != schedule.patchnotes
			):
				logger.info("変更検知: メンテナンススケジュール (%s)", lang)
				if prev_schedule.title != schedule.title:
					logger.info("- Title changed")
				if prev_schedule.detail != schedule.detail:
					logger.info("- Detail changed")
				if prev_schedule.downtime != schedule.downtime:
					logger.info("- Downtime changed")
				if prev_schedule.date != schedule.date:
					logger.info("- Date changed")
				if [p.name for p in prev_schedule.platforms] != [p.name for p in schedule.platforms]:
					logger.info("- Platforms changed")
				if prev_schedule.patchnotes != schedule.patchnotes:
					logger.info("- Patchnotes changed")
				return True

		return False

	async def update(
		self,
		guild: discord.Guild,
		ch: discord.TextChannel | None = None,
		gc: Box | None = None,
		status_embeds: dict[str, list[list[discord.Embed]]] | None = None,
	) -> None:
		status_data: list[r6sss.types.Status] | None = None
		schedule_data: dict[str, r6sss.types.MaintenanceSchedule] | None = None
		msg = None

		# 作成されたサーバーステータス埋め込みメッセージの総数をリセット
		self.server_status_embeds_count = 0

		# 埋め込みメッセージが渡されていない場合は情報を取得して生成する (情報の更新はしない)
		if status_embeds is None:
			# 各言語のサーバーステータス埋め込みメッセージのリスト
			# 言語コードをキーとする辞書 値はリスト (ステータスの埋め込みリスト, メンテナンススケジュールの埋め込みリスト)
			status_embeds = {}
			try:
				status_data = ServerStatusManager.data
			except Exception:
				logger.error("サーバーステータスの取得に失敗")
				logger.error(traceback.format_exc())
				status_data = None

			try:
				schedule_data = MaintenanceScheduleManager.data
			except Exception:
				logger.error("メンテナンススケジュールの取得に失敗")
				logger.error(traceback.format_exc())
				schedule_data = None

			if schedule_data is None:
				schedule_data = {}

			# サーバーステータス情報を取得できなかった場合は処理を行わずにエラーを出力する
			if status_data is None:
				logger.error("- 更新中止: status_data is None")
				return

			# データに変更がない場合は処理をスキップする
			# if not self._check_data_changed(status_data, schedule_data):
			# 	logger.info("サーバーステータスおよびメンテナンススケジュールの変更がないため更新をスキップします")
			# 	await KumaSan.ping("up", "サーバーステータスの更新スキップ: 変更なし")
			# 	return

			# 各言語のサーバーステータス情報埋め込みメッセージと通知メッセージを生成する
			for lang_code in Localization.EXISTS_LOCALE_LIST:
				status_embeds[lang_code] = []

				# サーバーステータス情報の埋め込みメッセージを生成する
				generated_status_embed = await embeds.ServerStatus.generate_embed(lang_code, status_data)
				if generated_status_embed:
					status_embeds[lang_code].append(generated_status_embed)
				else:
					logger.error("サーバーステータス埋め込みメッセージの生成に失敗: 言語 %s", lang_code)
					continue

				# メンテナンススケジュール情報の埋め込みメッセージを生成する
				generated_schedule_embed = await embeds.MaintenanceSchedule.generate_embed(lang_code, schedule_data.get(lang_code))
				if generated_schedule_embed:
					status_embeds[lang_code].append(generated_schedule_embed)
				else:
					logger.error("メンテナンススケジュール埋め込みメッセージの生成に失敗: 言語 %s", lang_code)
					continue

		logger.info("ギルド: %s", guild.name)
		try:
			# ギルドコンフィグが渡されていない場合はデータベースからギルドコンフィグを取得する
			if gc is None:
				gc = await GuildConfigManager.get(guild.id)
				# 取得できなかった場合はスキップする
				if gc is None:
					logger.warning("更新スキップ: ギルドデータ (%s) の取得失敗", guild.name)
					return
			ch_id = int(gc.server_status_message.channel_id)
			msg_id = int(gc.server_status_message.message_id)
			schedule_display = gc.server_status_message.maintenance_schedule
			lang = gc.server_status_message.language
		except Exception:
			logger.warning("更新スキップ: ギルドデータ (%s) の取得時エラー", guild.name)
			logger.error(traceback.format_exc())
			return  # 更新をスキップ

		# サーバーステータス埋め込みメッセージの更新処理
		try:
			# テキストチャンネルとメッセージIDが両方とも設定されている場合は更新処理を実行する
			if ch_id != 0 and msg_id != 0:
				# テキストチャンネルが渡されていない場合はIDからテキストチャンネルを取得する
				if ch is None:
					ch = await guild.get_or_fetch(discord.TextChannel, ch_id)
				# チャンネルが存在しない場合はギルドデータのチャンネルIDとメッセージIDをリセットする
				if ch is None:
					logger.info("更新スキップ: テキストチャンネルの取得失敗")
					logger.info("- サーバーステータスメッセージ設定リセット実行")
					gc.server_status_message.channel_id = "0"
					gc.server_status_message.message_id = "0"
					# ギルドコンフィグを保存
					await GuildConfigManager.update(guild.id, gc)
					return  # 処理をスキップする

				ch_name = ch.name
				logger.info("- 更新実行: #%s", ch_name)

				# メッセージオブジェクトを取得 (APIリクエストなし)
				msg = ch.get_partial_message(msg_id)

				# 設定言語のサーバーステータスの埋め込みメッセージを取得
				target_embeds = status_embeds.get(lang)

				try:
					# 既存のサーバーステータス埋め込みメッセージを新しいものに編集する
					if target_embeds is not None:
						try:
							# メンテナンススケジュールの埋め込みが生成されているかつ
							# 表示設定が有効な場合はメンテナンススケジュールの埋め込みを追加する
							if schedule_display and len(target_embeds) >= 2:  # noqa: PLR2004
								await msg.edit(embeds=target_embeds[0] + target_embeds[1])
							# メンテナンススケジュール埋め込みなし (ステータス埋め込みのみ)
							else:
								await msg.edit(embeds=target_embeds[0])

							# 作成されたサーバーステータス埋め込みメッセージの総数をカウントする
							self.server_status_embeds_count += 1

						# メッセージが存在しない (削除されている) 場合
						except discord.errors.NotFound as err:
							logger.info(" - メッセージの編集失敗 - NotFound (%s)", str(err))
							logger.info("- 更新中止: メッセージの取得失敗")
							logger.info("- ギルド %s のメッセージ (ID: %s) の取得に失敗", guild.name, str(msg_id))
							logger.info("- サーバーステータスメッセージ設定リセット実行")
							# メッセージが存在しない(削除されている)場合はギルドデータのチャンネルIDとメッセージIDをリセットする
							gc.server_status_message.channel_id = "0"
							gc.server_status_message.message_id = "0"
							# ギルドデータを保存
							await GuildConfigManager.update(guild.id, gc)
							return

						# メッセージを取得する権限がない (チャンネルへのアクセス権がない) 場合
						except discord.errors.Forbidden as err:
							logger.info(" - メッセージの編集失敗 - Forbidden (%s)", str(err))
							# 権限がない場合はギルドのオーナーへ警告メッセージを送信する
							await GuildOwnerAnnounceUtil.send_warning(
								guild=guild,
								description=localizations.translate(
									"OwnerAnnounce_Warning_UpdateServerStatusMessage_Error_Forbidden",
									[guild.name, ch.mention],
									lang=lang,
								),
								lang=lang,
							)

						except discord.errors.HTTPException as err:
							logger.error(traceback.format_exc())
							logger.error(" - メッセージの編集失敗 - HTTPException (Status: %d / %s)", err.status, str(err))

						# ステータスインジケーターが有効かつインジケーターに変化があった場合は
						# 元の名前を保持して先頭にインジケーターを追加または置換する
						if all(
							(
								gc.server_status_message.status_indicator,  # ステータスインジケーターが有効
								ch_name[0] in icons.Indicator,  # チャンネル名の先頭がステータスインジケーターか
								ch_name[0] != ServerStatusManager.indicator,  # チャンネル名の先頭が現在のインジケーターと異なるか
							)
						):
							# インジケーター文字を除いたチャンネル名を取得する
							ch_name_min_count = 2
							ch_name = ch_name[1:] if len(ch_name) >= ch_name_min_count else ""
							try:
								# チャンネル名を更新する
								await ch.edit(
									name=ServerStatusManager.indicator + ch_name,
								)
							except Exception as e:
								logger.error(traceback.format_exc())
								logger.error("ギルド %s のステータスインジケーターの更新に失敗: %s", guild.name, str(e))

					else:
						logger.error("サーバーステータスメッセージの取得失敗: 言語 %s の埋め込みメッセージが存在しません", lang)
				except Exception as e:
					logger.error(traceback.format_exc())
					logger.error("サーバーステータスメッセージの編集失敗: %s", str(e))
		except Exception:
			logger.error("ギルド %s のサーバーステータスメッセージ (ID: %s) の更新失敗", guild.name, str(msg_id))
			logger.error(traceback.format_exc())

	# 2分毎にサーバーステータスを更新する
	@tasks.loop(minutes=2)
	async def update_all(self) -> None:  # noqa: PLR0915
		self.server_status_update_loop_is_running = True
		status_data = None  # 現在のサーバーステータス情報
		schedule_data = None  # 現在のメンテナンススケジュール情報
		# 各言語のサーバーステータス埋め込みメッセージのリスト
		# 言語コードをキーとする辞書 値はリスト (ステータスの埋め込みリスト, メンテナンススケジュールの埋め込みリスト)
		status_embeds: dict[str, list[list[discord.Embed]]] = {}
		notif_embeds: dict[str, list] = {}  # サーバーステータス通知埋め込みメッセージのリスト

		# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
		await KumaSan.ping(state="up", message="サーバーステータスの更新開始")

		logger.info("サーバーステータスの更新開始")
		start_time = time.perf_counter()

		try:
			# サーバーステータス情報とメンテナンススケジュール情報を取得 (更新) する
			try:
				status_data = await ServerStatusManager.get()
			except Exception:
				logger.error("サーバーステータスの取得に失敗")
				logger.error(traceback.format_exc())
				status_data = None

			try:
				schedule_data = await MaintenanceScheduleManager.get()
			except Exception:
				logger.error("メンテナンススケジュールの取得に失敗")
				logger.error(traceback.format_exc())
				schedule_data = None

			# サーバーステータス情報を取得できなかった場合は処理を行わずにエラーを出力する
			if status_data is None:
				logger.error("- 更新中止: status_data is None")
				await KumaSan.ping("pending", "サーバーステータスの更新中止: status_data is None")
				return

			# メンテナンススケジュール情報を取得できなかった場合は処理を行わずにエラーを出力する
			if schedule_data is None:
				logger.error("- 更新中止: schedule_data is None")
				await KumaSan.ping("pending", "メンテナンススケジュールの更新中止: schedule_data is None")
				return

			# データに変更がない場合は処理をスキップする
			if not self._check_data_changed(status_data, schedule_data):
				logger.info("サーバーステータスおよびメンテナンススケジュールの変更がないため更新をスキップします")
				await KumaSan.ping("up", "サーバーステータスの更新スキップ: 変更なし")
				return

			# 各言語のサーバーステータス情報埋め込みメッセージと通知メッセージを生成する
			for lang_code in Localization.EXISTS_LOCALE_LIST:
				status_embeds[lang_code] = []
				notif_embeds[lang_code] = []

				# サーバーステータス情報の埋め込みメッセージを生成する
				generated_status_embed = await embeds.ServerStatus.generate_embed(lang_code, status_data)
				if generated_status_embed:
					status_embeds[lang_code].append(generated_status_embed)
				else:
					logger.error("サーバーステータス埋め込みメッセージの生成に失敗: 言語 %s", lang_code)
					continue

				# メンテナンススケジュール情報の埋め込みメッセージを生成する
				generated_schedule_embed = await embeds.MaintenanceSchedule.generate_embed(lang_code, schedule_data.get(lang_code))
				if generated_schedule_embed:
					status_embeds[lang_code].append(generated_schedule_embed)
				else:
					logger.error("メンテナンススケジュール埋め込みメッセージの生成に失敗: 言語 %s", lang_code)
					continue

				# 以前のサーバーステータス情報が存在する場合はサーバーステータスの通知メッセージを生成する
				if ServerStatusManager.previous_data is not None:
					compare_result = r6sss.compare_server_status(
						ServerStatusManager.previous_data, status_data, schedule_data.get(lang_code)
					)
					# ステータスの比較結果一覧から通知用の埋め込みメッセージを生成する
					notif_embeds[lang_code] = [
						embeds.Notification.get_by_comparison_result(result, lang_code, schedule_data.get(lang_code))
						for result in compare_result
					]

			# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
			for guild in bot.client.guilds:
				logger.info("ギルド: %s", guild.name)
				try:
					# データベースからギルドコンフィグを取得する
					gc = await GuildConfigManager.get(guild.id)
					# 取得できなかった場合はスキップする
					if gc is None:
						logger.warning("更新スキップ: ギルドデータ (%s) の取得失敗", guild.name)
						continue
					msg_id = int(gc.server_status_message.message_id)
					notif_ch_id = int(gc.server_status_notification.channel_id)
					notif_role_id = int(gc.server_status_notification.role_id)
					lang = gc.server_status_message.language
				except Exception:
					logger.warning("更新スキップ: ギルドデータ (%s) の取得時エラー", guild.name)
					logger.error(traceback.format_exc())
					continue  # 更新をスキップ

				# サーバーステータス埋め込みメッセージの更新処理
				try:
					# サーバーステータス埋め込みメッセージを更新する
					await self.update(guild, None, gc, status_embeds)

					# 通知メッセージの送信処理
					try:
						# 通知埋め込みメッセージの個数が1以上かつ
						# 通知メッセージの送信先が設定されている場合は通知メッセージを送信する
						if len(notif_embeds[lang]) >= 1 and notif_ch_id != 0:
							# 通知メッセージを送信するチャンネルを取得
							notif_ch = await guild.get_or_fetch(discord.TextChannel, notif_ch_id)
							notif_role = await guild.get_or_fetch(discord.Role, notif_role_id)

							# メンションするロールが設定済みかつメンションが可能な場合はメンション用のテキストを設定
							notif_role_mention = (notif_role.mention if notif_role.mentionable else "") if notif_role is not None else ""

							# 通知送信先テキストチャンネルが存在する場合は通知メッセージの送信を実行する
							if notif_ch is not None:
								# 自動削除が有効の場合は削除までの時間を指定する
								notif_delete_after_seconds = int(gc.server_status_notification.auto_delete)
								if notif_delete_after_seconds > 0:
									await notif_ch.send(
										content=localizations.translate(
											"Notification_Server_Status_Updated",
											lang=lang,
										)
										+ "\n"
										+ notif_role_mention,
										embeds=notif_embeds[lang],
										delete_after=notif_delete_after_seconds,
									)
								# 自動削除が無効の場合は削除までの時間を指定しない
								else:
									# 通知メッセージを送信する
									logger.info("サーバーステータス通知メッセージ送信 - チャンネル: %s", notif_ch.name)
									await notif_ch.send(
										content=localizations.translate(
											"Notification_Server_Status_Updated",
											lang=lang,
										)
										+ "\n"
										+ notif_role_mention,
										embeds=notif_embeds[lang],
									)
							# 通知メッセージの送信先が存在しない場合は通知設定をリセットする
							else:
								logger.info("サーバーステータス通知メッセージ送信スキップ: チャンネルが存在しません")
								logger.info("- 設定リセット実行")
								gc.server_status_notification.channel_id = "0"
								gc.server_status_notification.role_id = "0"
								# ギルドコンフィグを保存
								await GuildConfigManager.update(guild.id, gc)

					except Exception as e:
						logger.error(traceback.format_exc())
						logger.error("サーバーステータス通知メッセージの送信失敗: %s", str(e))

				except Exception:
					logger.error("ギルド %s のサーバーステータスメッセージ (ID: %s) の更新失敗", guild.name, str(msg_id))
					logger.error(traceback.format_exc())

		except Exception as e:
			logger.error(traceback.format_exc())
			await KumaSan.ping(state="pending", message="サーバーステータスの更新エラー: " + str(e))

		end_time = time.perf_counter()
		p_time = end_time - start_time
		p_time_str = f"{(end_time - start_time):.2f}"
		logger.info("サーバーステータスの更新完了")
		logger.info("- 処理時間: %s s", p_time_str)

		await KumaSan.ping(state="up", message="サーバーステータスの更新完了", ping=str(int(p_time * 1000)))  # ミリ秒に直して渡す
		self.server_status_embeds_update_time = p_time

	@update_all.after_loop
	async def after_update_all(self) -> None:
		self.server_status_update_loop_is_running = False
		logger.info("サーバーステータスの定期更新終了")
		if not self.server_status_update_loop_is_running:
			self.update_all.start()

	@update_all.before_loop
	async def before_update_all(self) -> None:
		logger.info("サーバーステータスの定期更新待機中")
		logger.info("- クライアントの準備完了まで待機中")
		await self.bot.wait_until_ready()
		logger.info("- クライアントの準備完了")
		logger.info("- データベースの接続待機中")
		while not DBManager.connected:
			await asyncio.sleep(1)
		logger.info("- データベースの接続完了")
		logger.info("定期更新開始")


def setup(bot: discord.Bot) -> None:
	bot.add_cog(ServerStatusEmbedManager(bot))
