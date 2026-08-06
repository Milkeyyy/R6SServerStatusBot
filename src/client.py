import json
import traceback
from os import getenv

import discord
from discord.ext import commands
from pycord.i18n import _

from app import App
from bot import Bot
from db import DBManager
from kumasan import KumaSan
from logger import logger

bot = Bot()

import embeds
from config import GuildConfigManager
from debug_logger import DebugLogger


# Bot起動時のイベント
@bot.client.event
async def on_ready() -> None:
	logger.info("---------------------------------------")
	logger.info(f" {App.NAME} - Version {App.VERSION_STRING}")
	logger.info(f" using Pycord {discord.__version__}")
	logger.info(f" Developed by {App.DEVELOPER_NAME}")
	logger.info(f" {App.COPYRIGHT}")
	logger.info("---------------------------------------")
	logger.info("")

	logger.info(
		"%s へログインしました！ (ID: %s)",
		bot.client.user.display_name,
		str(bot.client.user.id),
	)

	# 内部エラー報告機能の初期化
	try:
		logger.info("デバッグ用サーバー/チャンネル取得")
		debug_gd_id = getenv("DEBUG_GUILD_ID", "")
		debug_ch_id = getenv("DEBUG_TEXT_CHANNEL_ID", "")
		# サーバーを取得
		DebugLogger.debug_guild = bot.client.get_guild(int(debug_gd_id))
		if DebugLogger.debug_guild is not None:
			logger.info("- サーバー: %s (ID: %d)", DebugLogger.debug_guild.name, DebugLogger.debug_guild.id)
			# テキストチャンネルを取得
			DebugLogger.debug_channel = await DebugLogger.debug_guild.get_or_fetch(discord.TextChannel, int(debug_ch_id))
		else:
			logger.warning("- サーバーが見つかりません: %s", debug_gd_id)
		if DebugLogger.debug_channel:
			logger.info("- チャンネル: %s (ID: %d)", DebugLogger.debug_channel.name, DebugLogger.debug_channel.id)
		else:
			logger.warning("- チャンネルが見つかりません: %s", debug_ch_id)
	except Exception:
		logger.error("内部エラー報告機能の初期化に失敗")
		logger.error(traceback.format_exc())

	# データベースへ接続する
	await DBManager.connect()

	# ギルドデータのチェックを実行
	await GuildConfigManager.load()

	# ボット情報定期更新開始
	bot.update_info.start()
	bot.update_presence_status.start()

	await KumaSan.ping(state="up", message="ログイン完了")


# サーバー参加時のイベント
@bot.client.event
async def on_guild_join(guild: discord.Guild) -> None:
	logger.info("ギルド参加: %s (%d)", guild.name, guild.id)
	await DebugLogger.log(f"ギルド参加\n- ギルド: `{guild.name}`\n- ID: `{guild.id}`")
	# 参加したギルドのコンフィグを作成する
	await GuildConfigManager.create(guild.id)


# サーバー脱退時のイベント
@bot.client.event
async def on_guild_remove(guild: discord.Guild) -> None:
	logger.info("ギルド脱退: %s (%d)", guild.name, guild.id)
	await DebugLogger.log(f"ギルド脱退\n- ギルド: `{guild.name}`\n- ID: `{guild.id}`")
	# 脱退したギルドのコンフィグを削除する
	await GuildConfigManager.delete(guild.id)


# アプリケーションコマンド実行時のイベント
@bot.client.event
async def on_application_command_completion(ctx: discord.ApplicationContext) -> None:
	full_command_name = ctx.command.qualified_name
	if ctx.guild is not None:
		logger.info(
			"アプリケーションコマンド実行 - %s | ギルド: %s (%d) | 実行者: %s (%s)",
			full_command_name,
			ctx.guild.name,
			ctx.guild.id,
			ctx.user,
			ctx.user.id,
		)
	else:
		logger.info(
			"アプリケーションコマンド実行 - %s | DM | 実行者: %s (%s)",
			full_command_name,
			ctx.user,
			ctx.user.id,
		)


# アプリケーションコマンドエラー時のイベント
@bot.client.event
async def on_application_command_error(
	ctx: discord.ApplicationContext,
	ex: discord.DiscordException,
) -> None:
	full_command_name = ctx.command.qualified_name
	gn = None
	if ctx.guild is not None:
		gn = ctx.guild.name
		logger.info(
			"アプリケーションコマンド実行 - %s | ギルド: %s (%d) | 実行者: %s (%s)",
			full_command_name,
			ctx.guild.name,
			ctx.guild.id,
			ctx.user,
			ctx.user.id,
		)
	else:
		logger.info(
			"アプリケーションコマンド実行 - %s | DM | 実行者: %s (%s)",
			full_command_name,
			ctx.user,
			ctx.user.id,
		)
	logger.error("アプリケーションコマンド実行エラー")
	logger.error(ex)
	# クールダウン
	if isinstance(ex, commands.CommandOnCooldown):
		await ctx.respond(
			embed=embeds.Notification.warning(description=_("CmdMsg_CooldownWarning", int(ex.retry_after))),
			ephemeral=True,
		)
	# 実行者がオーナーではない
	elif isinstance(ex, commands.NotOwner):
		await ctx.respond(embed=embeds.Notification.error(description=_("CmdMsg_NotOwner")), ephemeral=True)
	# その他
	else:
		# 内部エラーを報告してメッセージを送信する
		# 1. Pycord特有のラップされたエラーから、大元のエラーを取り出す
		# original が存在しないエラー(HTTPExceptionなど)に備えて getattr を使う
		original_ex = getattr(ex, "original", ex)

		# 2. 例外オブジェクトから直接トレースバック文字列を生成する
		tb_strings = traceback.format_exception(type(original_ex), original_ex, original_ex.__traceback__)
		tb_text = "".join(tb_strings)

		# 内部エラーを報告してメッセージを送信する
		await ctx.respond(
			embed=embeds.Notification.internal_error(
				error_code=await DebugLogger.report_internal_error(
					"<Exception>\n" + str(original_ex) + "\n\n<Traceback>\n" + tb_text,
					description="".join(
						"<Application Command Error>\n"
						f"- {'DM' if gn is None else f'Guild: {gn} (`{ctx.guild.id}`)'}\n"
						f"- User: {ctx.user} (`{ctx.user.id}`)\n"
						f"- Command: `{full_command_name}`\n"
						"  - Options\n"
						+ (
							"\n".join(["    - `" + json.dumps(o) + "`" for o in ctx.selected_options])
							if ctx.selected_options
							else "    - None"
						)
					),
				),
			)
		)
