import json
from pathlib import Path
from typing import get_args

from pycord.i18n import I18n, Locale

from client import bot
from logger import logger


class Localization:
	i18n: I18n | None
	LOCALE_DATA: dict
	EXISTS_LOCALE_LIST: dict

	@classmethod
	def load_locale_data(cls) -> None:
		# 言語一覧
		cls.LOCALE_DATA = {}
		cls.EXISTS_LOCALE_LIST = {}

		# 言語ファイルを読み込む
		logger.info("言語ファイルを読み込み")
		for lang_code in get_args(Locale):
			# 言語ファイルのフォルダー
			lang_file_base_path = "./locales"
			# - を _ へ置き換える
			lang = lang_code.replace("-", "_")
			# 言語ファイルのパス
			lang_file_path = Path(lang_file_base_path) / (lang + ".json")
			# 対象の言語ファイルが存在するかチェック
			if not Path(lang_file_path).exists():
				# ファイルが存在しない場合は英語 (en_GB) のファイルを読み込むようにする (フォールバック
				logger.info("- %s -> en_GB (フォールバック)", lang)
				lang_file_path = Path(lang_file_base_path) / "en_GB.json"
			else:
				logger.info("- %s", lang)
				# 有効な言語一覧へ追加
				cls.EXISTS_LOCALE_LIST[lang] = lang

			# 翻訳データを読み込む
			with Path(lang_file_path).open(encoding="utf-8") as lang_file:
				cls.LOCALE_DATA[lang] = json.loads(lang_file.read())

			# 有効な言語一覧の名称を設定する
			if lang in cls.EXISTS_LOCALE_LIST:
				cls.EXISTS_LOCALE_LIST[lang] = cls.LOCALE_DATA[lang]["info"]["name"]

		# Pycord の多言語対応用クラスのインスタンスを生成
		cls.i18n = I18n(bot.client, consider_user_locale=True, **cls.LOCALE_DATA)

	@classmethod
	def localize_commands(cls) -> None:
		logger.info("コマンドの多言語化実行")
		if cls.i18n is not None:
			cls.i18n.localize_commands()
			logger.info("- 完了")
		else:
			logger.error("- エラー: i18n is None")

	@classmethod
	def translate(cls, text: str, values: list | None = None, lang: str = "en_GB") -> str:
		if values is None:
			values = []

		try:
			if cls.LOCALE_DATA is not None:
				return cls.LOCALE_DATA[lang]["strings"][text].format(*values)
		except KeyError as e:
			logger.error("Translate Error - KeyError: %s", str(e))
			return text

		logger.error("Translate Error - LOCALE_DATA is None")
		return text


def translate(text: str, values: list | None = None, lang: str = "en_GB") -> str:
	"""指定されたキーのテキストを取得する"""
	return Localization.translate(text, values, lang)
