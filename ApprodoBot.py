import discord
from discord import app_commands
from discord.ext import commands
import asyncpg
import logging
from dotenv import load_dotenv
import os

#SETUP------------------------
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non impostata")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

#Initialize database
async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5
    )
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id SERIAL PRIMARY KEY,
                character_name TEXT NOT NULL,
                owner_discord_id BIGINT NOT NULL,
                copper INTEGER DEFAULT 0
            )
        """)

def format_currency(copper_total: int):
    platinum = copper_total // 1000
    copper_total %= 1000
    gold = copper_total // 100
    copper_total %= 100
    silver = copper_total // 10
    copper = copper_total % 10
    parts = []
    if platinum: parts.append(f"{platinum} Platinum")
    if gold: parts.append(f"{gold} Gold")
    if silver: parts.append(f"{silver} Silver")
    if copper: parts.append(f"{copper} Copper")
    return ", ".join(parts) if parts else "0 Copper"

def has_permission(interaction, owner_id: int):
    # Controlla se l'autore è il proprietario
    if interaction.user.id == owner_id:
        return True
    # Controlla se ha ruolo Master o Master Supremo
    roles = [role.name for role in interaction.user.roles]
    if "Master" in roles or "Master Supremo" in roles:
        return True
    return False

async def character_name_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete che mostra solo i personaggi su cui l'utente ha permessi"""

    user_id = interaction.user.id
    roles = [role.name for role in interaction.user.roles]
    is_master = "Master" in roles or "Master Supremo" in roles

    async with pool.acquire() as conn:
        if is_master:
            rows = await conn.fetch(
                """
                SELECT character_name
                FROM bank_accounts
                WHERE character_name ILIKE $1
                ORDER BY character_name
                LIMIT 25
                """,
                f"{current}%"
            )
        else:
            rows = await conn.fetch(
                """
                SELECT character_name
                FROM bank_accounts
                WHERE owner_discord_id = $1
                  AND character_name ILIKE $2
                ORDER BY character_name
                LIMIT 25
                """,
                user_id, f"{current}%"
            )

    return [
        discord.app_commands.Choice(
            name=row["character_name"],
            value=row["character_name"]
        )
        for row in rows
    ]

#COMMANDS--------------------------------
class MyBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sito", description="Link alla wiki")
    async def sito(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Ecco a lei la wiki: https://mudslingar.github.io/TerrePerdute/")

    #CREA UN CONTO BANCARIO
    @app_commands.command(name="createbankaccount", description="Crea un nuovo profilo bancario")
    @app_commands.describe(character_name="Nome del personaggio")
    async def createbankaccount(self, interaction: discord.Interaction, character_name: str, currency : int = 0):
        discord_id = interaction.user.id
        async with pool.acquire() as conn:
            # Controllo: esiste già?
            existing = await conn.fetchrow(
                """
                SELECT id FROM bank_accounts
                WHERE character_name = $1
                """,
                character_name
            )
            if existing:
                await interaction.response.send_message(f"❌ Esiste già un conto per **{character_name}**.")
                return

            # Inserimento
            await conn.execute(
                """
                INSERT INTO bank_accounts (character_name, owner_discord_id, copper)
                VALUES ($1, $2, $3)
                """,
                character_name, discord_id, currency
            )
        await interaction.response.send_message(
            f"✅ Conto creato per **{character_name}**.\n"
            f"Proprietario: {interaction.user.mention}"
        )


    #CONTROLLA IL SALDO
    @app_commands.command(name="balance", description="Controlla quanti soldi ha un personaggio")
    @app_commands.describe(character_name="Nome del personaggio")
    async def balance(self, interaction: discord.Interaction, character_name: str):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not has_permission(interaction, row["owner_discord_id"]):
                await interaction.response.send_message("❌ Non hai i permessi per vedere questo conto.")
                ephemeral=True
                return
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                ephemeral=True
                return
            formatted = format_currency(row["copper"])

        await interaction.response.send_message(f"Saldo di **{character_name}**: {formatted}")
    
    @balance.autocomplete("character_name")
    async def addcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await character_name_autocomplete(interaction, current)


    #AGGIUNGE FONDI
    @app_commands.command(name="addcopper", description="Aggiungi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da aggiungere")
    async def addcopper(self, interaction: discord.Interaction, character_name: str, amount : int):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                return
            
            if not has_permission(interaction, row["owner_discord_id"]):
                await interaction.response.send_message("❌ Non hai i permessi per modificare questo conto.")
                return
            
            if amount <= 0:
                await interaction.response.send_message("❌ Inserisci un valore positivo.")
                return
            
            new_total = row["copper"] + amount

            await conn.execute(
                "UPDATE bank_accounts SET copper = $1 WHERE character_name = $2",
                new_total, character_name
            )

        await interaction.response.send_message(f"✅ Aggiunti {amount} Copper al conto di **{character_name}**!")
    @addcopper.autocomplete("character_name")
    async def addcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await character_name_autocomplete(interaction, current)
    

    #RIMUOVE FONDI
    @app_commands.command(name="removecopper", description="Rimuovi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da rimuovere")
    async def removecopper(self, interaction: discord.Interaction, character_name: str, amount: int):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                return
            if not has_permission(interaction, row["owner_discord_id"]):
                await interaction.response.send_message("❌ Non hai i permessi per modificare questo conto.")
                return
            if row["copper"] < amount:
                await interaction.response.send_message(f"❌ Impossibile rimuovere {amount} Copper: saldo insufficiente.")
                return
            if amount <= 0:
                await interaction.response.send_message("❌ Inserisci un valore positivo.")
                return
            
            new_total = row["copper"] - amount
            await conn.execute(
                "UPDATE bank_accounts SET copper = $1 WHERE character_name = $2",
                new_total, character_name
            )
        await interaction.response.send_message(f"✅ Rimossi {amount} Copper dal conto di **{character_name}**!")
    @removecopper.autocomplete("character_name")
    async def addcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await character_name_autocomplete(interaction, current)
    
    #RIMUOVI UN CONTO BANCARIO
    @app_commands.command(name="deletebankaccount",description="ELIMINA DEFINITIVAMENTE UN CONTO BANCARIO")
    @app_commands.describe(character_name="Nome del personaggio")
    async def deletebankaccount(self, interaction: discord.Interaction, character_name: str):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT owner_discord_id FROM bank_accounts WHERE character_name = $1",
                character_name
            )
            if not row:
                await interaction.response.send_message(
                    f"❌ Nessun conto trovato per **{character_name}**.",
                    ephemeral=True
                )
                return

            if not has_permission(interaction, row["owner_discord_id"]):
                await interaction.response.send_message(
                    "❌ NON HAI I PERMESSI PER ELIMINARE QUESTO CONTO.",
                    ephemeral=True
                )
                return

        # Avviso di pericolo
        await interaction.response.send_message(
            "⚠️ **ATTENZIONE! OPERAZIONE PERICOLOSA** ⚠️\n\n"
            f"STAI PER **ELIMINARE DEFINITIVAMENTE** IL CONTO DI **{character_name}**.\n"
            "**QUESTA AZIONE È IRREVERSIBILE.**\n\n"
            "Scrivi **y** o **yes** per confermare.\n",
        )

        def check(msg: discord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and msg.content.lower() in ("y", "yes")
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except TimeoutError:
            await interaction.followup.send(
                "⏳ Operazione annullata: tempo scaduto."
            )
            return

        # Eliminazione definitiva
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bank_accounts WHERE character_name = $1",
                character_name
            )

        await interaction.followup.send(
            f"🔥 **CONTO DI {character_name} ELIMINATO DEFINITIVAMENTE. 🔥**"
        )

    @deletebankaccount.autocomplete("character_name")
    async def deletebankaccount_autocomplete(self, interaction: discord.Interaction, current: str):
        return await character_name_autocomplete(interaction, current)



#EVENTS----------------------------
@bot.event
async def on_ready():
    #INIZIALIZZA IL BOT
    try:
        await init_db()
        try:
            cog = MyBot(bot)
            await bot.add_cog(cog)
            # Registrazione manuale del comando per la guild
            #guild_test = discord.Object(id=1468198221972115551)
            guild = discord.Object(id=1220664060585050182)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            await bot.tree.sync()

            #await bot.tree.sync(guild=guild)

            print(f"{bot.user.name} è online! Yuppie!")
        except Exception as e:
            print(f"Errore durante tree.sync: {e}")
    except Exception as e:
        print(f"Errore durante init_db: {e}")

@bot.event
async def on_member_join(member):
    #Comportamento all'ingresso di un membro
    await member.send(f"Benvenuto ad Approdo, {member.name}!")
    await member.send(f"Ecco a te il link alla wiki, dove puoi trovare il riassunto degli eventi fin'ora!")
    await member.send(f"https://mudslingar.github.io/TerrePerdute/") 

bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)