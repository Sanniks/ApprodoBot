import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncpg
from dotenv import load_dotenv
import os

from MyLibraries.cogs.basic import Basic
from MyLibraries.cogs.currency_database import Currency
from MyLibraries.cogs.blackjackpinnu import BlackjackPinnu



def run_bot():

    # ==========================================================
    #                     SETUP
    # ==========================================================
    
    #Carica i TOKEN del bot e del DATABASE dal file .env
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN non impostata")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL non impostata")

    #Dove mandare i messaggi di log
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    #Queli permessi ha il bot
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    #Definisce il bot
    bot = commands.Bot(command_prefix='/', intents=intents)

    # ==========================================================
    #                     INIZIALIZZA IL BOT
    # ==========================================================

    #Comportamento del bot quando appena va online
    @bot.event
    async def on_ready():
        #Apre un collegamento con il Database su Neon
        try:
            pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=5
            )
        except Exception as e:
            print(f"Errore durante init_db: {e}")

        #Aggiunge i comandi
        try:
            basic_commands = Basic(bot)
            currency_commands = Currency(bot, pool)
            blackjack_commands = BlackjackPinnu(bot, pool)
            await bot.add_cog(basic_commands)
            await bot.add_cog(currency_commands)
            await bot.add_cog(blackjack_commands)

            # Registrazione manuale del comando per la guild

            #guild_test possiede il codice ID del server dove faccio i test
            #guild_test = discord.Object(id=1468198221972115551)
            #bot.tree.copy_global_to(guild=guild_test)
            #await bot.tree.sync(guild=guild_test)

            #guild possiede il codice ID del server di Approdo
            guild = discord.Object(id=1220664060585050182)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"{bot.user.name} V2.1 è online! Yuppie!")

        except Exception as e:
            print(f"Errore durante tree.sync: {e}")

    #Comportamento all'ingresso di un membro
    @bot.event
    async def on_member_join(member):
        await member.send(f"Benvenuto ad Approdo, {member.name}!\n"
                          f"Ecco a te il link alla wiki, dove puoi trovare il riassunto degli eventi fin'ora!\n"
                          f"https://mudslingar.github.io/TerrePerdute/")


    #Fa partire il bot
    bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)