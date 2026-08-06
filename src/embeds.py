import datetime

import discord
import r6sss
from pycord.i18n import _

import icons
import localizations
from client import bot
from logger import logger
from server_status import ServerStatusManager


class Notification:
	@classmethod
	def success(cls, title: str = "", description: str = "", lang: str = "") -> discord.Embed:
		"""成功時用埋め込みメッセージ"""
		if title == "":
			title = _("CmdMsg_Success") if lang.strip() == "" else localizations.translate("CmdMsg_Success", lang=lang)

		return discord.Embed(
			title=":white_check_mark: " + title,
			description=description,
			colour=discord.Colour.from_rgb(140, 176, 91),
		)

	@classmethod
	def warning(cls, title: str = "", description: str = "", lang: str = "") -> discord.Embed:
		"""警告用埋め込みメッセージ"""
		if title == "":
			title = _("CmdMsg_Warning") if lang.strip() == "" else localizations.translate("CmdMsg_Warning", lang=lang)

		return discord.Embed(
			title=":warning: " + title,
			description=description,
			colour=discord.Colour.from_rgb(228, 146, 16),
		)

	@classmethod
	def error(cls, title: str = "", description: str = "", lang: str = "") -> discord.Embed:
		"""エラー発生時用埋め込みメッセージ"""
		if title == "":
			title = _("CmdMsg_ExcutionError") if lang.strip() == "" else localizations.translate("CmdMsg_ExcutionError", lang=lang)

		return discord.Embed(
			title=":no_entry_sign: " + title,
			description=description,
			colour=discord.Colour.from_rgb(247, 206, 80),
		)

	@classmethod
	def internal_error(cls, description: str | None = None, error_code: str | None = None) -> discord.Embed:
		"""内部エラー発生時用埋め込みメッセージ"""
		embed = discord.Embed(
			title=":closed_book: " + _("CmdMsg_InternalError"),
			description=description if description else _("CmdMsg_InternalError_Description"),
			colour=discord.Colour.from_rgb(205, 61, 66),
		)
		# エラーコードが渡された場合は先頭に挿入する
		if error_code:
			embed.description = f"{embed.description}\n\n> :pencil: Error Code\n> ```{error_code}```"
		return embed

	@classmethod
	def get_by_comparison_result(
		cls,
		result: r6sss.types.ComparisonResult,
		lang: str,
		schedule_data: r6sss.types.MaintenanceSchedule | None = None,
	) -> discord.Embed | None:
		"""サーバーステータスの比較結果から通知用のEmbedを生成する"""
		if ServerStatusManager.data is None or bot.client.user is None:
			return None

		# if client.user is not None:
		# 	embed_author = discord.EmbedAuthor(client.user.display_name, icon_url=client.user.display_avatar.url)
		# else:
		# 	embed_author = None
		embed_author = None

		# 影響を受ける機能の名称を翻訳する
		impacted_features_list = [localizations.translate("Status_" + f, lang=lang) for f in result.impacted_features]
		# 影響を受けていた機能の名称を翻訳する
		resolved_impacted_features_list = [localizations.translate("Status_" + f, lang=lang) for f in result.resolved_impacted_features]

		# 対象プラットフォームの一覧テキストを生成
		# 全プラットフォームの場合は専用のテキストにする
		if {p.platform for p in ServerStatusManager.data}.issubset(
			set(result.platforms),
		):
			target_platforms_text = localizations.translate("Platform_All", lang=lang)
		else:
			target_platforms_text = "- " + "\n- ".join(
				[icons.Platform[p.name].value + " " + p.value for p in result.platforms],
			)

		embed = None

		# メンテナンス開始
		if result.detail == r6sss.types.ComparisonDetail.START_MAINTENANCE:
			embed = discord.Embed(
				color=discord.Colour.lighter_grey(),
				title=localizations.translate("Title_Maintenance_Start", lang=lang),
				author=embed_author,
			)
		# メンテナンス終了
		elif result.detail == r6sss.types.ComparisonDetail.END_MAINTENANCE:
			embed = discord.Embed(
				color=discord.Colour.lighter_grey(),
				title=localizations.translate("Title_Maintenance_End", lang=lang),
				author=embed_author,
			)

		# 計画メンテナンス開始
		elif result.detail == r6sss.types.ComparisonDetail.SCHEDULED_MAINTENANCE_START:
			embed = discord.Embed(
				color=discord.Colour.blue(),
				title=localizations.translate("Title_ScheduledMaintenance_Start", lang=lang),
				author=embed_author,
			)
			if schedule_data is not None:
				# メンテナンススケジュールの情報を追加する
				embed.fields.append(  # ダウンタイム
					discord.EmbedField(
						name=":clock3: " + localizations.translate("MaintenanceSchedule_Downtime", lang=lang),
						value=localizations.translate("MaintenanceSchedule_Downtime_Minute", [str(schedule_data.downtime)], lang=lang),
					),
				)
				embed.fields.append(  # パッチノート
					discord.EmbedField(
						name=":notepad_spiral: " + localizations.translate("MaintenanceSchedule_PatchNotes", lang=lang),
						value=schedule_data.patchnotes
						if schedule_data.patchnotes.strip() != ""
						else localizations.translate("None", lang=lang),
					),
				)
		# 計画メンテナンス終了
		elif result.detail == r6sss.types.ComparisonDetail.SCHEDULED_MAINTENANCE_END:
			embed = discord.Embed(
				color=discord.Colour.blue(),
				title=localizations.translate("Title_ScheduledMaintenance_End", lang=lang),
				author=embed_author,
			)
			if schedule_data is not None:
				# メンテナンススケジュールの情報を追加する
				embed.fields.append(  # ダウンタイム
					discord.EmbedField(
						name=":clock3: " + localizations.translate("MaintenanceSchedule_Downtime", lang=lang),
						value=localizations.translate("MaintenanceSchedule_Downtime_Minute", [str(schedule_data.downtime)], lang=lang),
					),
				)
				embed.fields.append(  # パッチノート
					discord.EmbedField(
						name=":notepad_spiral: " + localizations.translate("MaintenanceSchedule_PatchNotes", lang=lang),
						value=schedule_data.patchnotes
						if schedule_data.patchnotes.strip() != ""
						else localizations.translate("None", lang=lang),
					),
				)

		# すべての機能の問題が解消
		elif result.detail == r6sss.types.ComparisonDetail.ALL_FEATURES_OUTAGE_RESOLVED:
			embed = discord.Embed(
				color=discord.Colour.green(),
				title=localizations.translate(
					"Title_AllFeaturesOutageResolved",
					lang=lang,
				),
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate(
					"Detail_ImpactedFeatures_After",
					lang=lang,
				),
				value="- " + "\n- ".join(resolved_impacted_features_list),
			)
		# すべての機能で問題が発生中
		elif result.detail == r6sss.types.ComparisonDetail.ALL_FEATURES_OUTAGE:
			embed = discord.Embed(
				color=discord.Colour.red(),
				title=localizations.translate("Title_AllFeaturesOutage", lang=lang),
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures", lang=lang),
				value="- " + "\n- ".join(impacted_features_list),
			)

		# 一部の機能で問題が発生中
		elif result.detail == r6sss.types.ComparisonDetail.SOME_FEATURES_OUTAGE:
			embed = discord.Embed(
				color=discord.Colour.yellow(),
				title=localizations.translate("Title_SomeFeaturesOutage", lang=lang),
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures", lang=lang),
				value="- " + "\n- ".join(impacted_features_list),
			)
		# 一部の機能で問題が解消 (影響を受ける機能が変わった)
		elif result.detail == r6sss.types.ComparisonDetail.SOME_FEATURES_OUTAGE_RESOLVED:
			embed = discord.Embed(
				color=discord.Colour.yellow(),
				title=localizations.translate(
					"Title_SomeFeaturesOutageResolved",
					lang=lang,
				),
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures", lang=lang),
				value="- " + "\n- ".join(resolved_impacted_features_list),
			)
			embed.add_field(
				name=localizations.translate(
					"Detail_ImpactedFeatures_After",
					lang=lang,
				),
				value="- " + "\n- ".join(impacted_features_list),
			)
		else:
			embed = None

		# 対象プラットフォームのフィールドを末尾へ挿入
		if embed is not None:
			embed.fields.append(
				discord.EmbedField(
					name=":video_game: " + localizations.translate("TargetPlatform", lang=lang),
					value=target_platforms_text,
				),
			)

		return embed


class ServerStatus:
	@classmethod
	async def generate_embed(  # noqa: PLR0915
		cls,
		locale: str,
		status_data: list[r6sss.types.Status] | None,
	) -> list[discord.Embed]:
		"""サーバーステータス情報から埋め込みメッセージを生成する

		サーバーステータス情報が `None` の場合は空のリストを返す
		"""
		logger.info("サーバーステータス埋め込みメッセージ生成開始 - 言語: %s", locale)

		embed_settings = {
			"PC": [discord.Colour.from_rgb(255, 255, 255), 2],  # 埋め込みの色, 埋め込みのスペーシング
			"PS4": [discord.Colour.from_rgb(0, 67, 156), 0],
			"PS5": [discord.Colour.from_rgb(0, 67, 156), 1],
			"XB1": [discord.Colour.from_rgb(16, 124, 16), 0],
			"XBSX": [discord.Colour.from_rgb(16, 124, 16), 1],
		}
		embeds = []  # 埋め込みメッセージ一覧

		# サーバーステータスが取得できてない場合はエラーメッセージを返す
		if status_data is None:
			logger.error("サーバーステータス埋め込みメッセージ生成中止 (サーバーステータス情報なし)")
			return [
				discord.Embed(
					color=discord.Colour.light_grey(),
					title=localizations.translate("Embed_Unknown_Title", lang=locale),
					description=localizations.translate("Embed_Unknown_Desc", lang=locale),
				),
			]

		# 各プラットフォームごとの埋め込みメッセージを作成
		embed = discord.Embed()
		embed.title = icons.R6SSS.ICON.value + " Rainbow Six Siege Server Status"
		embed.description = (
			"🕒 "
			+ localizations.translate("Last Update", lang=locale)
			+ ": "
			+ f"<t:{ServerStatusManager.updated_at}:f> (<t:{ServerStatusManager.updated_at}:R>)"
		)
		embed.set_footer(
			text="⚠️\n" + localizations.translate("NotAffiliatedWithOrRndorsedBy", lang=locale),
		)
		embed.colour = ServerStatusManager.colour

		status_index = -1
		for status in status_data:
			status_index += 1

			connectivity_text_list = []

			pf_id = status.platform.name  # PC, PS4, XB1...
			pf_display_name = status.platform.value  # プラットフォームの表示名

			if pf_id.startswith("_"):
				continue

			# サーバーの状態によってアイコンを変更する
			# 問題なし
			if status.connectivity == "Operational":
				status_icon = icons.Status.OPERATIONAL.value
			# 計画メンテナンス
			elif status.connectivity == "Maintenance":
				status_icon = icons.Status.MAINTENANCE.value
			# 想定外の問題
			elif status.connectivity == "Interrupted":
				status_icon = icons.Status.INTERRUPTED.value
			# 想定外の停止
			elif status.connectivity == "Degraded":
				status_icon = icons.Status.DEGRADED.value
			# それ以外
			else:
				status_icon = icons.Status.UNKNOWN.value

			connectivity_text = localizations.translate(status.connectivity, lang=locale)

			mt_text = ""
			if status.maintenance:
				status_icon = icons.Status.MAINTENANCE.value
				connectivity_text = localizations.translate("Maintenance", lang=locale)

			features_list = []
			features_text = ""
			features_status_text = ""
			# 各サービスをループしてステータスに合わせてアイコンとテキストを設定
			# for f, s in status[pf_id]["Status"]["Features"].items():
			for s in [
				("Authentication", status.authentication),
				("Matchmaking", status.matchmaking),
				("Purchase", status.purchase),
			]:
				# 通常
				f_status_icon = icons.Status.OPERATIONAL.value
				features_status_text = localizations.translate(s[1], lang=locale)
				# 停止
				if s[1] != "Operational":
					f_status_icon = icons.Status.DEGRADED.value
				# メンテナンス
				if status.maintenance:
					f_status_icon = icons.Status.MAINTENANCE.value
				# 不明
				if s[1] == "Unknown":
					f_status_icon = icons.Status.UNKNOWN.value
					features_status_text = localizations.translate("Unknown", lang=locale)

				features_list.append(
					"" + localizations.translate(s[0], lang=locale) + "\n┗ " + f_status_icon + "`" + features_status_text + "`",
				)

			features_text = "" + "\n".join(features_list)

			# 埋め込みメッセージにプラットフォームのフィールドを追加
			connectivity_text_list.append(mt_text + features_text)

			# プラットフォームのステータスのフィールドを追加
			embed.add_field(
				name=icons.Platform[status.platform.name].value
				+ " "
				+ pf_display_name
				+ " - "
				+ status_icon
				+ "**`"
				+ connectivity_text
				+ "`**",
				value="\n".join(connectivity_text_list),
			)
			# 各プラットフォームごとに別の行にするために、リストで指定された数の空のフィールドを挿入する
			# for _ in range(embed_settings[status.platform.value][1]):
			# 	embed.add_field(name="", value="")
			for _n in range(list(embed_settings.values())[status_index][1]):
				embed.add_field(name="", value="")

		# メンテナンススケジュールの埋め込みメッセージを一覧へ追加して埋め込みメッセージ一覧を返す
		logger.info("サーバーステータス埋め込みメッセージ生成終了")
		embeds.append(embed)
		return embeds


class MaintenanceSchedule:
	@classmethod
	async def generate_embed(cls, locale: str, schedule_data: r6sss.types.MaintenanceSchedule | None) -> list[discord.Embed]:
		"""メンテナンススケジュール情報から埋め込みメッセージを生成する

		メンテナンススケジュール情報が `None` の場合は専用の埋め込みメッセージを返す
		"""
		logger.info("メンテナンススケジュール埋め込みメッセージ生成開始 - 言語: %s", locale)

		embeds = []  # 埋め込みメッセージ一覧

		# platform_list = [p["Name"] for p in sched["Platforms"]]

		# 全プラットフォーム同一
		# if "All" in platform_list:
		# 	# スケジュールが範囲内か判定
		# 	if datetime.datetime.now().timestamp() >= (date_timestamp + (sched.downtime * 60)):
		# 		create = False
		# 	# プラットフォーム一覧テキストを生成
		# 	pf_list_text = "・**" + localizations.translate('Platform_All', lang=locale) + "**\n"
		# else: # プラットフォーム別

		# メンテナンススケジュール情報が存在するか
		if schedule_data is not None:
			pf_list_text = ""
			platform_list = schedule_data.platforms
			date_timestamp = int(schedule_data.date.timestamp())
			# スケジュールが範囲内か判定
			# 範囲内であればスケジュールの埋め込みメッセージを生成する
			if datetime.datetime.now(tz=datetime.UTC).timestamp() <= (date_timestamp + (schedule_data.downtime * 60)):
				# TODO: プラットフォームごとに実施日時が異なる場合があるかもしれないのでそれに対応する？
				for p in platform_list:
					# プラットフォーム一覧テキストを生成
					pf_list_text = (
						pf_list_text
						+ "- **"
						+ icons.Platform[p.name].value
						+ " "
						+ localizations.translate(f"Platform_{p.name}", lang=locale)
						+ "**\n"
					)

				# 埋め込みメッセージを生成
				embed = discord.Embed(
					colour=discord.colour.Colour.nitro_pink(),
					title=":wrench::calendar: " + localizations.translate("MaintenanceSchedule", lang=locale),
					description="**" + schedule_data.title + "**\n" + schedule_data.detail,
					footer=discord.EmbedFooter(
						"⚠️\n" + localizations.translate("MaintenanceSchedule_Notes", lang=locale),
					),
					fields=[
						# ダウンタイム
						discord.EmbedField(
							name="**:clock3: "
							+ localizations.translate(
								"MaintenanceSchedule_Downtime",
								lang=locale,
							)
							+ "**",
							value="- "
							+ localizations.translate(
								"MaintenanceSchedule_Downtime_Minute",
								[str(schedule_data.downtime)],
								lang=locale,
							),
						),
						# 予定日時
						discord.EmbedField(
							name="**:calendar: "
							+ localizations.translate(
								"MaintenanceSchedule_ScheduledDT",
								lang=locale,
							)
							+ "**",
							value=f"- <t:{date_timestamp}:f> (<t:{date_timestamp}:R>)",
						),
						# 対象プラットフォーム一覧
						discord.EmbedField(
							name="**:video_game: "
							+ localizations.translate(
								"MaintenanceSchedule_TargetPlatform",
								lang=locale,
							)
							+ "**",
							value=pf_list_text,
						),
					],
				)
				# パッチノートのURLが指定されている場合は末尾にフィールドを追加する
				if schedule_data.patchnotes.startswith(("http://", "https://")):
					embed.fields.append(
						discord.EmbedField(
							name="**:notepad_spiral: "
							+ localizations.translate(
								"MaintenanceSchedule_PatchNotes",
								lang=locale,
							)
							+ "**",
							value=schedule_data.patchnotes,
						),
					)
				# 埋め込みメッセージを一覧へ追加
				embeds.append(embed)

				logger.info("メンテナンススケジュール埋め込みメッセージ生成終了")
				return embeds

		# 予定されているメンテナンスがない場合の埋め込みメッセージ
		embed = discord.Embed(
			colour=discord.colour.Colour.nitro_pink(),
			title=":wrench::calendar: " + localizations.translate("MaintenanceSchedule", lang=locale),
			description=localizations.translate(
				"MaintenanceSchedule_NoMaintenanceScheduled",
				lang=locale,
			),
			footer=discord.EmbedFooter(
				"⚠️\n" + localizations.translate("MaintenanceSchedule_Notes", lang=locale),
			),
		)
		# 埋め込みメッセージを一覧へ追加
		embeds.append(embed)

		# メンテナンススケジュールの埋め込みメッセージを一覧へ追加して埋め込みメッセージ一覧を返す
		logger.info("メンテナンススケジュール埋め込みメッセージ生成終了")
		return embeds


class Donation:
	@classmethod
	async def donation(cls) -> discord.Embed:
		embed = discord.Embed(
			colour=discord.colour.Colour.nitro_pink(),
			title=":pink_heart: " + _("DonationEmbed_Title"),
			description=_("DonationEmbed_Description"),
		)
		return embed
