import argparse
import sys
import traceback
from os import getenv
from pathlib import Path

try:
	from dotenv import load_dotenv
except ImportError:
	pass


from client import bot
from localizations import Localization
from logger import logger

# コマンドライン引数
parser = argparse.ArgumentParser()
parser.add_argument("--dev", action="store_true")  # 開発モード
args = parser.parse_args()


# ログイン
try:
	# .envファイルが存在する場合はファイルから環境変数を読み込む
	env_path = Path(Path.cwd()) / ".env"
	if Path.is_file(env_path):
		try:
			load_dotenv(env_path)
		except NameError:
			pass

	if args.dev:
		logger.info("開発モードで起動")
		logger.info("開発用サーバーID: %s", getenv("DEBUG_GUILD_ID", ""))
		bot.client.debug_guilds = [int(getenv("DEBUG_GUILD_ID", ""))]  # 開発用サーバーのIDを指定

	# 言語データを読み込む
	Localization.load_locale_data()
	# Cogs の読み込み
	bot.client.load_extensions(
		"cogs.commands.settings", "cogs.commands.status", "cogs.commands.dev", "cogs.commands.general", "cogs.tasks.server_status_embed"
	)
	# コマンドのローカライズ
	Localization.localize_commands()

	# ログイン
	bot.client.run(getenv("CLIENT_TOKEN"))
except Exception:
	logger.error(traceback.format_exc())
	sys.exit(1)
