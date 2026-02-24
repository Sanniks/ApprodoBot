import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from pathlib import Path
import MyLibraries.Functions.utils as ut
DB_PATH = Path("Database/bank.db")

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #CREA UN CONTO BANCARIO
    @app_commands.command(name="createbankaccount", description="Crea un nuovo profilo bancario")
    @app_commands.describe(character_name="Nome del personaggio")
    async def createbankaccount(self, interaction: discord.Interaction, character_name: str, currency : int = 0):
        discord_id = interaction.user.id

        #Connessione al database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Controllo: esiste già?
        cursor.execute("SELECT id FROM bank_accounts WHERE character_name = ?", (character_name,))
        existing = cursor.fetchone()
        if existing:
            await interaction.response.send_message(f"❌ Esiste già un conto per **{character_name}**.")
            conn.close()
            return
        
        # Inserimento nuovo conto
        cursor.execute(
            "INSERT INTO bank_accounts (character_name, owner_discord_id, copper) VALUES (?, ?, ?)",
            (character_name, discord_id, currency)
        )
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ Conto creato per **{character_name}**.\n"
            f"Proprietario: {interaction.user.mention}"
        )


    #CONTROLLA IL SALDO
    @app_commands.command(name="balance", description="Controlla quanti soldi ha un personaggio")
    @app_commands.describe(character_name="Nome del personaggio")
    async def balance(self, interaction: discord.Interaction, character_name: str):

        #Connessione al database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not ut.has_permission(interaction, row["owner_discord_id"]):
                await interaction.response.send_message("❌ Non hai i permessi per vedere questo conto.")
                return
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                return
            formatted = ut.format_currency(row["copper"])

        await interaction.response.send_message(f"Saldo di **{character_name}**: {formatted}")
    
    @balance.autocomplete("character_name")
    async def addcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete(interaction, current)
    
    #Set soldi
    @app_commands.command(name="setcopper", description="Aggiungi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da aggiungere")
    async def setcopper(self, interaction: discord.Interaction, character_name: str, amount : int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                return
            
            if not ut.has_permission(interaction, row["owner_discord_id"]):
                await interaction.response.send_message("❌ Non hai i permessi per modificare questo conto.")
                return
            
            if amount <= 0:
                await interaction.response.send_message("❌ Inserisci un valore positivo.")
                return
            
            new_total = amount

            await conn.execute(
                "UPDATE bank_accounts SET copper = $1 WHERE character_name = $2",
                new_total, character_name
            )

        await interaction.response.send_message(f"✅ Aggiunti {amount} Copper al conto di **{character_name}**!")
    @setcopper.autocomplete("character_name")
    async def addcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete(interaction, current, self.pool)


    #AGGIUNGE FONDI
    @app_commands.command(name="addcopper", description="Aggiungi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da aggiungere")
    async def addcopper(self, interaction: discord.Interaction, character_name: str, amount : int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                return
            
            if not ut.has_permission(interaction, row["owner_discord_id"]):
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
        return await ut.character_name_autocomplete(interaction, current, self.pool)
    

    #RIMUOVE FONDI
    @app_commands.command(name="removecopper", description="Rimuovi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da rimuovere")
    async def removecopper(self, interaction: discord.Interaction, character_name: str, amount: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT copper, owner_discord_id FROM bank_accounts WHERE character_name = $1", character_name
            )
            if not row:
                await interaction.response.send_message(f"❌ Nessun conto trovato per **{character_name}**.")
                return
            if not ut.has_permission(interaction, row["owner_discord_id"]):
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
        return await ut.character_name_autocomplete(interaction, current, self.pool)
    
    #RIMUOVI UN CONTO BANCARIO
    @app_commands.command(name="deletebankaccount",description="ELIMINA DEFINITIVAMENTE UN CONTO BANCARIO")
    @app_commands.describe(character_name="Nome del personaggio")
    async def deletebankaccount(self, interaction: discord.Interaction, character_name: str):
        async with self.pool.acquire() as conn:
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

            if not ut.has_permission(interaction, row["owner_discord_id"]):
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
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bank_accounts WHERE character_name = $1",
                character_name
            )

        await interaction.followup.send(
            f"🔥 **CONTO DI {character_name} ELIMINATO DEFINITIVAMENTE. 🔥**"
        )

    @deletebankaccount.autocomplete("character_name")
    async def deletebankaccount_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete(interaction, current, self.pool)

