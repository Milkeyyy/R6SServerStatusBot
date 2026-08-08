import discord
from discord.ext import commands


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
		embed.add_field(name="Total Servers", value=str(len(self.bot.guilds)), inline=False)

		embed.add_field(
			name="Total Server Status Embeds",
			value=str(self.bot.get_cog("ServerStatusEmbedManager").server_status_embeds_count),
		)
		update_time = self.bot.get_cog("ServerStatusEmbedManager").server_status_embeds_update_time
		ut_min, ut_min_sec = divmod(update_time, 60)
		embed.add_field(
			name="Server Status Embeds Last Update Time",
			value=f"{int(ut_min)} m {ut_min_sec:.0f} s ({update_time:.1f} s)",
			inline=False,
		)

		embed.add_field(
			name="Server Preferred Locale List",
			value="- " + str("\n- ".join({"`" + (guild.preferred_locale or "Not Defined") + "`" for guild in self.bot.guilds})),
			inline=False,
		)

		await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
	bot.add_cog(DevCommands(bot))
