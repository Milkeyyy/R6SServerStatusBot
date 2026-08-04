import discord
from discord.ext import commands

from cogs.tasks.server_status_embed import ServerStatusEmbedManager


class DevCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	@commands.is_owner()
	async def botstats(self, ctx: discord.ApplicationContext) -> None:
		embed = discord.Embed(
			title="R6SSS Bot Stats",
			description="",
			color=discord.Colour.from_rgb(79, 168, 254),
		)
		embed.add_field(name="Total Servers", value=str(len(self.bot.guilds)))
		embed.add_field(
			name="Total Server Status Embeds",
			value=str(self.bot.get_cog("ServerStatusEmbedManager").server_status_embeds_count),
		)
		embed.add_field(
			name="Server Preferred Locale List",
			value="- " + str("\n- ".join({(guild.preferred_locale or "Not Defined") for guild in self.bot.guilds})),
			inline=False,
		)

		await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
	bot.add_cog(DevCommands(bot))
