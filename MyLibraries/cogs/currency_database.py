import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
import MyLibraries.Functions.utils as ut

class Currency(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    async def _get_account_with_permission(self, interaction, conn, character_name):
        row = await conn.fetchrow(
            """
            SELECT copper, owner_discord_id FROM bank_accounts
            WHERE character_name = $1
            """,
            character_name
        )
        if not row:
            await interaction.response.send_message(
                f"❌ Nessun conto trovato per **{character_name}**."
            )
            return None
        if not ut.has_permission(interaction, row["owner_discord_id"]):
            await interaction.response.send_message(
                "❌ Non hai i permessi per questo conto."
            )
            return None
        return row

    # ==========================================================
    #                     BANK ACCOUNT CREATION
    # ==========================================================
    @app_commands.command(name="createbankaccount", description="Crea un nuovo profilo bancario")
    @app_commands.describe(character_name="Nome del personaggio")
    async def createbankaccount(self, interaction: discord.Interaction, character_name: str, currency : int = 0):
        discord_id = interaction.user.id
        async with self.pool.acquire() as conn:
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

    # ==========================================================
    #                     SHOW BALANCE
    # ==========================================================
    @app_commands.command(name="balance", description="Controlla quanti soldi ha un personaggio")
    @app_commands.describe(character_name="Nome del personaggio")
    async def balance(self, interaction: discord.Interaction, character_name: str):
        async with self.pool.acquire() as conn:
            row = await self._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return
            formatted = ut.format_currency(row["copper"])

        await interaction.response.send_message(f"Saldo di **{character_name}**: {formatted}")
    
    @balance.autocomplete("character_name")
    async def balance_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete_database(interaction, current, self.pool)
    
    # ==========================================================
    #                     SET AMOUNT
    # ==========================================================
    @app_commands.command(name="setcopper", description="Aggiungi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da aggiungere")
    async def setcopper(self, interaction: discord.Interaction, character_name: str, amount : int):
        async with self.pool.acquire() as conn:
            row = await self._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return
            if amount <= 0:
                await interaction.response.send_message("❌ Inserisci un valore positivo.")
                return
        
        # Avviso di pericolo
        await interaction.response.send_message(
            f"Stai per cambiare il conto di **{character_name}**.\n"
            f"Il saldo passerà da {ut.format_currency(row['copper'])}\n"
            f"a {ut.format_currency(amount)}\n\n"
            "Scrivi **y** o **yes** per confermare.\n"
            "Scrivi **n** o **no** per annullare.\n",
        )

        def check(msg: discord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and msg.content.lower() in ("y", "yes", "n", "no")
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except TimeoutError:
            await interaction.followup.send(
                "⏳ Operazione annullata: tempo scaduto."
            )
            return
        
        # Se arriva qui significa che è stata scritta una risposta valida
        if msg.content.lower() in ("n", "no"):
            await interaction.followup.send("❌ Operazione annullata.")
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE bank_accounts SET copper = $1 WHERE character_name = $2",
                amount, character_name
            )

        await interaction.followup.send(f"✅ **{character_name}** ora possiede {ut.format_currency(amount)}!")
    @setcopper.autocomplete("character_name")
    async def setcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete_database(interaction, current, self.pool)


    # ==========================================================
    #                     ADD AMOUNT
    # ==========================================================
    @app_commands.command(name="addcopper", description="Aggiungi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da aggiungere")
    async def addcopper(self, interaction: discord.Interaction, character_name: str, amount : int):
        async with self.pool.acquire() as conn:
            row = await self._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return
            
            if amount <= 0:
                await interaction.response.send_message("❌ Inserisci un valore positivo.")
                return

            await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper + $1 
                WHERE character_name = $2""",
                amount, character_name
            )
            new_row = await conn.fetchrow(
            """
            SELECT copper FROM bank_accounts
            WHERE character_name = $1
            """,
            character_name
            )
            new_total = new_row['copper']

        await interaction.response.send_message(f"✅ Aggiunti {ut.format_currency(amount)} al conto di **{character_name}**!\n"
                                                f"**{character_name}** ora possiede {ut.format_currency(new_total)}!")
    @addcopper.autocomplete("character_name")
    async def addcopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete_database(interaction, current, self.pool)
    

    # ==========================================================
    #                     REMOVE AMOUNT
    # ==========================================================
    @app_commands.command(name="removecopper", description="Rimuovi monete di rame al conto di un personaggio")
    @app_commands.describe(character_name="Nome del personaggio", amount="Quantità di copper da rimuovere")
    async def removecopper(self, interaction: discord.Interaction, character_name: str, amount: int):
        async with self.pool.acquire() as conn:
            row = await self._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return
            if row["copper"] < amount:
                await interaction.response.send_message(f"❌ Impossibile rimuovere {amount}: saldo insufficiente.")
                return
            if amount <= 0:
                await interaction.response.send_message("❌ Inserisci un valore positivo.")
                return
            
            await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper - $1 
                WHERE character_name = $2""",
                amount, character_name
            )
            new_row = await conn.fetchrow(
            """
            SELECT copper FROM bank_accounts
            WHERE character_name = $1
            """,
            character_name
            )
            new_total = new_row['copper']
        await interaction.response.send_message(f"✅ Rimossi {ut.format_currency(amount)} dal conto di **{character_name}**!\n"
                                                f"**{character_name}** ora possiede {ut.format_currency(new_total)}!")
    @removecopper.autocomplete("character_name")
    async def removecopper_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete_database(interaction, current, self.pool)
    
    # ==========================================================
    #                     DELETE BANK ACCOUNT
    # ==========================================================
    @app_commands.command(name="deletebankaccount",description="ELIMINA DEFINITIVAMENTE UN CONTO BANCARIO")
    @app_commands.describe(character_name="Nome del personaggio")
    async def deletebankaccount(self, interaction: discord.Interaction, character_name: str):
        async with self.pool.acquire() as conn:
            row = await self._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return

        # Avviso di pericolo
        await interaction.response.send_message(
            "⚠️ **ATTENZIONE! OPERAZIONE PERICOLOSA** ⚠️\n\n"
            f"STAI PER **ELIMINARE DEFINITIVAMENTE** IL CONTO DI **{character_name}**.\n"
            "**QUESTA AZIONE È IRREVERSIBILE.**\n\n"
            "Scrivi **y** o **yes** per confermare.\n"
            "Scrivi **n** o **no** per annullare.\n",
        )

        def check(msg: discord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and msg.content.lower() in ("y", "yes", "n", "no")
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except TimeoutError:
            await interaction.followup.send(
                "⏳ Operazione annullata: tempo scaduto."
            )
            return
        
        # Se arriva qui significa che è stata scritta una risposta valida
        if msg.content.lower() in ("n", "no"):
            await interaction.followup.send("❌ Operazione annullata.")
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
        return await ut.character_name_autocomplete_database(interaction, current, self.pool)

