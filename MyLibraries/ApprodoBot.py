import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncpg
from dotenv import load_dotenv
import os

from MyLibraries.cogs.basic import Basic
from MyLibraries.cogs.currency_database import Currency



def run_bot():

    #------------------SETUP------------------------
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN_TEST')
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN_TEST non impostata")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL non impostata")
    
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix='/', intents=intents)

    #------------------EVENTS------------------------
    @bot.event
    async def on_ready():
        #INIZIALIZZA IL BOT
        try:
            pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=5
            )
        except Exception as e:
            print(f"Errore durante init_db: {e}")
        try:
            basic_commands = Basic(bot)
            currency_commands = Currency(bot, pool)
            await bot.add_cog(basic_commands)
            await bot.add_cog(currency_commands)
            # Registrazione manuale del comando per la guild
            guild_test = discord.Object(id=1468198221972115551)
            bot.tree.copy_global_to(guild=guild_test)
            await bot.tree.sync(guild=guild_test)
            print(f"{bot.user.name} è online! Yuppie!")
        except Exception as e:
            print(f"Errore durante tree.sync: {e}")

    @bot.event
    async def on_member_join(member):
        #Comportamento all'ingresso di un membro
        await member.send(f"Benvenuto ad Approdo, {member.name}!")
        await member.send(f"Ecco a te il link alla wiki, dove puoi trovare il riassunto degli eventi fin'ora!")
        await member.send(f"https://mudslingar.github.io/TerrePerdute/") 

    bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)