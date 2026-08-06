import json
import traceback

import discord
import r6sss
from discord.commands import Option
from discord.ext import commands
from pycord.i18n import _

import __main__
import embeds
from client import bot
from config import GuildConfigManager
from debug_logger import DebugLogger
from logger import logger
from maintenance_schedule import MaintenanceScheduleManager
from server_status import ServerStatusManager


class StatusCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def status(self, ctx: discord.ApplicationContext) -> None:
		await ctx.defer(ephemeral=False)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
				),
			)
			return

		# サーバーステータスを取得する
		status_data = ServerStatusManager.data
		# 取得できなかった場合 (None) はエラーメッセージを返す
		if status_data is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetServerStatus"),
					error_code=await DebugLogger.report_internal_error("FailedToGetServerStatus"),
				),
			)
			return

		# 埋め込みメッセージを生成して送信する
		await ctx.send_followup(
			embeds=await embeds.ServerStatus.generate_embed(gc.server_status_message.language, status_data),
		)

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def schedule(self, ctx: discord.ApplicationContext) -> None:
		await ctx.defer(ephemeral=False)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
				),
			)
			return

		# メンテナンススケジュールを取得する
		schedule_data = MaintenanceScheduleManager.data
		if schedule_data is None:
			logger.warning("メンテナンススケジュールの取得失敗: data is None")
			logger.warning(str(schedule_data))
			await ctx.send_followup(embeds=embeds.Notification.error(description=_("CmdMsg_FailedToGetMaintenanceSchedule")))
			return

		schedule_data = schedule_data.get(gc.server_status_message.language)

		# 埋め込みメッセージを生成して送信する
		await ctx.send_followup(embeds=await embeds.MaintenanceSchedule.generate_embed(gc.server_status_message.language, schedule_data))

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def create(
		self,
		ctx: discord.ApplicationContext,
		channel: Option(discord.TextChannel, required=False),  # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		await ctx.defer(ephemeral=True)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		gc = None

		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
				),
			)
			return

		additional_msg = ""
		if gc.server_status_message.message_id != "0":
			additional_msg = f"\n> {_('Cmd_create_OldMessagesWillNoLongerBeUpdated')}"

		# テキストチャンネルのID
		ch_id = channel.id if channel else ctx.channel_id
		# IDからテキストチャンネルを取得する
		ch = await ctx.guild.get_or_fetch(discord.TextChannel, ch_id)

		if ch is None:
			await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_TextChannelNotFound")))
			return

		try:
			# サーバーステータスを取得する
			status_data = ServerStatusManager.data
			# 取得できなかった場合 (None) はエラーメッセージを返す
			if status_data is None:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetServerStatus"),
						error_code=await DebugLogger.report_internal_error("FailedToGetServerStatus"),
					),
				)

			embed_list = await embeds.ServerStatus.generate_embed(gc.server_status_message.language, status_data)

			# メンテナンススケジュールの表示が有効の場合のみ埋め込みを追加する
			if gc.server_status_message.maintenance_schedule:
				# メンテナンススケジュールを取得する
				schedule_data = MaintenanceScheduleManager.data
				if schedule_data is not None:
					schedule_data = schedule_data.get(gc.server_status_message.language)

				# メンテナンススケジュールの埋め込みを生成してリストへ追加する
				embed_list.extend(await embeds.MaintenanceSchedule.generate_embed(gc.server_status_message.language, schedule_data))

			# サーバーステータス埋め込みメッセージ生成してを送信する (作成)
			try:
				msg = await ch.send(
					embeds=embed_list,
				)
			except discord.errors.Forbidden as e:
				logger.info("サーバーステータスメッセージ作成失敗 - %s", str(e))
				# Missing Access (テキストチャンネルを閲覧する権限なし)
				if e.code == 50001:
					await ctx.send_followup(
						embed=embeds.Notification.error(
							description=_(
								"Cmd_create_Error_MissingAccess",
								ch.mention,
							),
						),
					)
				# Missing Permission (メッセージを送信する権限なし)
				elif e.code == 50013:
					await ctx.send_followup(
						embed=embeds.Notification.error(
							description=_(
								"CmdMsg_DontHavePermission_SendMessage",
								ch.mention,
							),
						),
					)
				# それ以外
				else:
					await ctx.send_followup(
						embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
					)
				return

			# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
			gc.server_status_message.channel_id = str(ch.id)
			gc.server_status_message.message_id = str(msg.id)
			# ギルドコンフィグを保存
			await GuildConfigManager.update(ctx.guild.id, gc)

		except Exception:
			# 設定をリセット
			if gc is not None:
				gc.server_status_message.channel_id = "0"
				gc.server_status_message.message_id = "0"
				await GuildConfigManager.update(ctx.guild.id, gc)
			logger.error(traceback.format_exc())
			await ctx.send_response(
				embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc())),
			)
			return

		else:
			logger.info("サーバーステータスメッセージ新規作成: ギルド: %s | チャンネル: %s", ctx.guild.name, ch.name)
			await DebugLogger.log(f"サーバーステータスメッセージ新規作成\n- ギルド: `{ctx.guild.name}`\n- チャンネル: `{ch.name}`")
			# 作成成功メッセージを送信する
			await ctx.send_followup(
				embeds=[
					embeds.Notification.success(
						description=_("Cmd_create_Success", ch.mention) + additional_msg,
					),
					await embeds.Donation.donation(),
				],
			)

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def testnotification(
		self,
		ctx: discord.ApplicationContext,
		comparison_target: str,
	) -> None:
		if await bot.client.is_owner(ctx.user):
			await ctx.defer(ephemeral=True)

			raw_status = json.loads(comparison_target)["data"]
			status_list = []
			for _platform, _status in raw_status.items():
				status_list.append(
					r6sss.functions.Status(r6sss.types.Platform[_platform], _status),
				)

			status_data = ServerStatusManager.data
			schedule_data = MaintenanceScheduleManager.data

			if schedule_data is not None:
				schedule_data = schedule_data.get("ja")
			if schedule_data is None:
				logger.warning("メンテナンススケジュールの取得失敗: 指定された言語に該当するスケジュールが存在しません")
				logger.warning(str(schedule_data))
				await ctx.send_response(embeds=embeds.Notification.error(description=_("CmdMsg_FailedToGetMaintenanceSchedule")))
				return

			# サーバーステータスが None の場合はエラーメッセージを返す
			if status_data is None:
				logger.error("ServerStatusManager.data is None")
				await ctx.respond(
					embed=embeds.Notification.error(
						description=_("CmdMsg_FailedToGetServerStatus"),
					),
				)
				return

			# 比較を実行
			compare_result = r6sss.compare_server_status(
				status_data,
				status_list,
				schedule_data,
			)

			# 通知メッセージを送信
			await ctx.respond(f"テスト通知 ({len(compare_result)})")
			for result in compare_result:
				await ctx.channel.send(
					content=f"Test notification message\nType: `{result.detail}`",
					embed=embeds.Notification.get_by_comparison_result(result, "ja", schedule_data),
				)
		else:
			await ctx.respond(
				embed=embeds.Notification.error(
					description=_("CmdMsg_DontHavePermission_Execution"),
				),
			)


def setup(bot: discord.Bot) -> None:
	bot.add_cog(StatusCommands(bot))
