import discord
from discord.ext import commands

import embeds
from app import App
from client import bot
from config import GuildConfigManager
from localizations import Localization


class GeneralCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	async def _resolve_help_lang(self, ctx: discord.ApplicationContext) -> str:
		"""/help の表示言語を解決する。"""
		if ctx.guild is None:
			return "en_GB"

		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			return "en_GB"

		lang = gc.server_status_message.language
		if lang in Localization.LOCALE_DATA:
			return lang

		return "en_GB"

	@classmethod
	def _get_help_text(cls, lang: str, key: str) -> str:
		try:
			text_key = Localization.LOCALE_DATA[lang]["help"][key]
			return Localization.LOCALE_DATA[lang]["strings"][text_key]
		except KeyError:
			return key

	@commands.slash_command()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def ping(self, ctx: discord.ApplicationContext) -> None:
		raw_ping = bot.client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(
			title="Pong!",
			description=f"Latency: **`{ping}`** ms",
			color=discord.Colour.from_rgb(79, 168, 254),
		)
		await ctx.respond(embed=ping_embed)

	@commands.slash_command()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def about(self, ctx: discord.ApplicationContext) -> None:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_image(url=App.bot_banner_url)
		embed.set_author(name=App.NAME, icon_url=bot.client.user.display_avatar.url)
		embed.set_footer(text=App.COPYRIGHT)
		embed.add_field(
			name="Version",
			value=f"`{App.VERSION_STRING}` ([`{App.get_git_commit_hash()[0:7]}`]({App.GITHUB_REPO_URL}/commit/{App.get_git_commit_hash()}))",
		)
		embed.add_field(
			name="Guilds",
			value=f"`{len(bot.client.guilds)}`",
			inline=False,
		)
		embed.add_field(
			name="Source",
			value=f"- [GitHub]({App.GITHUB_REPO_URL})",
			inline=False,
		)
		embed.add_field(
			name="Developer",
			value=f"- {App.DEVELOPER_NAME}\n  - [Website]({App.DEVELOPER_WEBSITE_URL})\n  - [Twitter]({App.DEVELOPER_TWITTER_URL})",
			inline=True,
		)
		embed.add_field(
			name="Other Services",
			value=f"- [Bluesky Bot]({App.BLUESKY_BOT_URL})\n- [Twitter Bot]({App.TWITTER_BOT_URL})",
			inline=True,
		)
		await ctx.respond(embeds=[embed, await embeds.Donation.donation()])

	@commands.slash_command()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def help(self, ctx: discord.ApplicationContext) -> None:
		lang = await self._resolve_help_lang(ctx)

		embed = discord.Embed(
			title=self._get_help_text(lang, "title"),
			description=self._get_help_text(lang, "description"),
			color=discord.Colour.from_rgb(79, 168, 254),
		)

		if bot.client.user is not None:
			embed.set_author(name=App.NAME, icon_url=bot.client.user.display_avatar.url)

		embed.add_field(
			name=self._get_help_text(lang, "category_general"),
			value="- "
			+ "\n- ".join(
				[
					self._get_help_text(lang, "item_about"),
					self._get_help_text(lang, "item_ping"),
				]
			),
			inline=False,
		)
		embed.add_field(
			name=self._get_help_text(lang, "category_status"),
			value="- "
			+ "\n- ".join(
				[
					self._get_help_text(lang, "item_status"),
					self._get_help_text(lang, "item_schedule"),
				]
			),
			inline=False,
		)
		embed.add_field(
			name=self._get_help_text(lang, "category_admin"),
			value="- "
			+ "\n- ".join(
				[
					self._get_help_text(lang, "item_create"),
					self._get_help_text(lang, "item_viewsettings"),
					self._get_help_text(lang, "item_setindicator"),
					self._get_help_text(lang, "item_setlanguage"),
					self._get_help_text(lang, "item_setscheduledisplay"),
					self._get_help_text(lang, "item_setnotification"),
				]
			),
			inline=False,
		)

		embed.set_footer(text=self._get_help_text(lang, "footer"))
		await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
	bot.add_cog(GeneralCommands(bot))
