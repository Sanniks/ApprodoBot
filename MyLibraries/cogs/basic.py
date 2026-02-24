import discord
from discord.ext import commands
from discord import app_commands


class Basic(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command(name="sito", description="Link alla wiki")
        async def sito(self, interaction: discord.Interaction):
            await interaction.response.send_message(f"Ecco a lei la wiki: https://mudslingar.github.io/TerrePerdute/")
