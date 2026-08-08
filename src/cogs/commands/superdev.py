import discord
from discord.ext import commands

from cogs_list import COGS


class SuperDevCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	@commands.is_owner()
	async def reloadcogs(self, ctx: discord.ApplicationContext) -> None:
		"""Reload all cogs."""
		for cog in COGS:
			self.bot.reload_extension(cog)
		await ctx.respond("All cogs reloaded.")


def setup(bot: discord.Bot) -> None:
	bot.add_cog(SuperDevCommands(bot))
