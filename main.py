from keep_alive import keep_alive
import localizations
import statusicon
import serverstatus

from replit import db

import argparse
import logging
import os

import discord
from discord.commands import Option
from discord.ext import tasks

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)

# Botの名前
bot_name = "R6SSS"
# Botのバージョン
bot_version = "1.0.0"

default_embed = discord.Embed

default_guilddata_item = {"server_status_message": [0, 0, "en-GB"]} # チャンネルID, メッセージID

# 引数ぱーさー
parser = argparse.ArgumentParser()
parser.add_argument(
	"--token",
	help="Botのトークン (使用法: --token ここにトークンを挿入)",
	type=str,
	required=False
)
args = parser.parse_args()

# くらいあんと
intents = discord.Intents.all()
client = discord.Bot(intents = intents)

# 言語データを読み込む
localizations.loadLocaleData()

# Bot起動時のイベント
@client.event
async def on_ready():
	print("---------------------------------------")
	print(f" {bot_name} - Version {bot_version}")
	print(f" using Pycord {discord.__version__}")
	print(f" Developed by Milkeyyy")
	print("---------------------------------------")
	print("")
	await client.change_presence(
		activity=discord.Game(
			name=f"Type /create | Version {bot_version}"
		)
	)
	logging.info(f"{client.user} へログインしました！ (ID: {client.user.id})")

	# ギルドデータの確認を開始
	checkGuildData()

	logging.info("サーバーステータスの定期更新開始")
	updateserverstatus.start()


# 関数
# ギルドデータの確認
def checkGuildData():
	global default_guilddata_item

	logging.info("ギルドデータの確認開始")
	for guild in client.guilds:
		# すべてのギルドのデータが存在するかチェック、存在しないギルドがあればそのギルドのデータを作成する
		if db.get(str(guild.id)) == None:
			db[str(guild.id)] = default_guilddata_item

	logging.info("ギルドデータの確認完了")


# 1分毎にサーバーステータスを更新する
@tasks.loop(seconds=60.0)
async def updateserverstatus():
	global server_status_embed

	logging.info("サーバーステータスの更新開始")

	# サーバーステータスを取得する
	status = await serverstatus.get()

	# サーバーステータスを更新する
	serverstatus.data = status

	# 埋め込みメッセージを更新する
	#await updateserverstatusembed()

	# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
	for guild in client.guilds:
		logging.info(f"ギルド: {guild.name}")
		try:
			ch_id = int(db[str(guild.id)]["server_status_message"][0])
			msg_id = int(db[str(guild.id)]["server_status_message"][1])
			loc = db[str(guild.id)]["server_status_message"][2]
		except Exception as e:
			logging.warning(f"ギルドデータ({guild.name}) の読み込み失敗")
			logging.warning(e)
			db[str(guild.id)]["server_status_message"] = default_guilddata_item
			ch_id = default_guilddata_item[0]
			msg_id = default_guilddata_item[1]
			loc = default_guilddata_item[2]

		if ch_id != 0 and msg_id != 0 and loc != None:
			ch = client.get_channel(ch_id) # IDからテキストチャンネルを取得する
			msg = await ch.fetch_message(msg_id) # 取得したテキストチャンネルからメッセージを取得する
			if msg is None:
				logging.warning("ギルド " + guild.name + " のメッセージ " + str(msg_id) + " の更新に失敗")
				db[str(guild.id)]["server_status_message"] = default_guilddata_item
			else:
				await msg.edit(embeds=await generateserverstatusembed(loc))

	logging.info("サーバーステータスの更新完了")

@updateserverstatus.after_loop
async def after_updateserverstatus():
	logging.info("サーバーステータスの定期更新終了")

# サーバーステータス埋め込みメッセージを更新
async def generateserverstatusembed(locale):
	global server_status_embed

	embeds = []
	pf_list = {"PC / Stadia": ["PC", "Stadia"], "PlayStation": ["PS4", "PS5"], "Xbox": ["XBOXONE", "XBOX SERIES X"]}

	# 翻訳先言語を設定
	localizations.locale = locale

	# 各プラットフォームの埋め込みメッセージの色
	color_list = {"PC / Stadia": discord.Colour.from_rgb(255, 255, 255), "PlayStation": discord.Colour.from_rgb(0, 67, 156), "Xbox": discord.Colour.from_rgb(16, 124, 16)}

	# サーバーステータスを取得
	status = serverstatus.data

	# 各プラットフォームごとの埋め込みメッセージを作成
	for pf in pf_list:
		embed = discord.Embed(color=color_list[pf])
		embed.set_author(name="Server Status - " + pf, icon_url="https://www.google.com/s2/favicons?sz=64&domain_url=https://www.ubisoft.com/en-us/game/rainbow-six/siege/status")
		embed.set_footer(text=localizations.translate("Last Update") + ": " + status["_update_date"].strftime('%Y/%m/%d %H:%M:%S') + " (JST)")

		for p in pf_list[pf]:
			if p.startswith("_"): continue
	
			# サーバーの状態によってアイコンを変更する
			# 問題なし
			if status[p]["Status"]["Connectivity"] == "Operational":
				status_icon = statusicon.Operational
			# 計画メンテナンス
			elif status[p]["Status"]["Connectivity"] == "Maintenance":
				status_icon = statusicon.Maintenance
			# 想定外の問題
			elif status[p]["Status"]["Connectivity"] == "Interrupted":
				status_icon = statusicon.Interrupted
			# 想定外の停止
			elif status[p]["Status"]["Connectivity"] == "Degraded":
				status_icon = statusicon.Degraded
			# それ以外
			else:
				status_icon = statusicon.Unknown
	
			mt_text = ""
			if status[p]["Maintenance"] == True:
				mt_text = "- **`" + localizations.translate("Maintenance") + "`**"
	
			f_list = []
			f_text = ""
			for f, s in status[p]["Status"].items():
				if f == "Connectivity": continue
				f_status_icon = statusicon.Operational
				if s != "Operational": f_status_icon = statusicon.Degraded
				if s == "Unknown": f_status_icon = statusicon.Unknown
				f_list.append("┣━ **" + localizations.translate(f) + "**\n┣━ " + f_status_icon + "`" + localizations.translate(s) + "`")
			f_text = "" + "\n".join(f_list)
	
			# 埋め込みメッセージにプラットフォームのフィールドを追加
			embed.add_field(name=status_icon + "__" + p + "__" + " - `" + localizations.translate(status[p]["Status"]["Connectivity"]) + "`", value=mt_text + f_text)

		embeds.append(embed)

	return embeds

# コマンド
@client.slash_command()
async def setlanguage(ctx, locale: Option(
	str,
	name="language",
	choices=localizations.locales
)):
	global guilddata

	await ctx.defer()

	if locale in localizations.data["Locales"].values():
		db[str(ctx.guild.id)]["server_status_message"][2] = [k for k, v in localizations.data["Locales"].items() if v == locale][0]
	else:
		db[str(ctx.guild.id)]["server_status_message"][2] = "en-GB"

	await ctx.followup.send(content="サーバーステータスメッセージの言語を `" + locale + "` に設定しました。")

@client.slash_command()
async def status(ctx):
	logging.info(f"コマンド実行: status / 実行者: {ctx.user}")

	await ctx.defer()
	await ctx.followup.send(embeds=await generateserverstatusembed(db[str(ctx.guild_id)]["server_status_message"][2]))

@client.slash_command()
async def create(ctx, channel: Option(
	discord.TextChannel,
	required=False,
	name="textchannel",
	description="サーバーステータスを送信するテキストチャンネルを指定します。指定しない場合は現在のチャンネルになります。")
):
	logging.info(f"コマンド実行: create / 実行者: {ctx.user}")

	await ctx.defer()

	checkGuildData()

	additional_msg = ""
	if db[str(ctx.guild_id)]["server_status_message"][1] != 0:
		additional_msg = "\n(以前送信した古いメッセージは更新されなくなります。)"

	if channel is None:
		ch_id = ctx.channel_id
	else:
		ch_id = channel.id
	ch = client.get_channel(ch_id)

	# サーバーステータス埋め込みメッセージを送信
	msg = await ch.send(embeds=await generateserverstatusembed(db[str(ctx.guild_id)]["server_status_message"][2]))

	# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
	db[str(ctx.guild_id)]["server_status_message"][0] = ch_id
	db[str(ctx.guild_id)]["server_status_message"][1] = msg.id

	await ctx.send_followup(content="テキストチャンネル " + ch.mention + " へサーバーステータスメッセージを送信しました。\n以後このメッセージは自動的に更新されます。" + additional_msg)

@client.slash_command()
async def ping(ctx):
	logging.info(f"コマンド実行: ping / 実行者: {ctx.user}")
	raw_ping = client.latency
	ping = round(raw_ping * 1000)
	ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
	await ctx.respond(embed=ping_embed)

@client.slash_command()
async def about(ctx):
	logging.info(f"コマンド実行: about / 実行者: {ctx.user}")
	embed = discord.Embed(color=discord.Colour.blue())
	embed.set_author(name=bot_name, icon_url=client.user.display_avatar.url)
	embed.set_footer(text=f"Developed by Milkeyyy#0625")
	embed.add_field(name="Version", value="`" + bot_version + "`")
	embed.add_field(name="Library", value=f"Pycord: `{discord.__version__}`")

	await ctx.respond(embed=embed)


# ログイン
try:
	keep_alive()
	client.run(os.getenv("TOKEN"))
except Exception as e:
	logging.error(str(e))
	os.system("kill 1")