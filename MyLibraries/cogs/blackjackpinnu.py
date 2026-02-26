import discord
from discord.ext import commands
from discord import app_commands
import random

import MyLibraries.Functions.utils as ut
import MyLibraries.Functions.blackjackpinnu_game as bj

class BlackjackPinnu(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    @app_commands.command(name="blackjack", description="Inizia una partita a Blackjack con Pinnu")
    @app_commands.describe(character_name="Nome del personaggio")
    @app_commands.describe(bet="Quanto scommetti?")
    async def blackjack(self, interaction: discord.Interaction, character_name: str, bet: int):
        '''
        Comando per far iniziare la partita contro Pinnu

        :param character_name: Nome del personaggio, presente nel database e legato al player
        :param bet: Ammontare di monete di rame che scommetti
        '''
        #Controlla che hai abbastanza soldi per scommettere l'ammontare voluto
        async with self.pool.acquire() as conn:
            row = await ut._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return
            row_Pinnu = await conn.fetchrow(
                """
                SELECT copper FROM bank_accounts
                WHERE character_name = 'Pinnu'
                """
                )
            if row_Pinnu is None:
                await interaction.response.send_message("Account di Pinnu non trovato.")
                return
        if bet > row['copper']:
            await interaction.response.send_message("❌ Non hai così tanti soldi...")
            return
        if self.bet > row_Pinnu['copper']:
            await interaction.response.send_message("🐐 Beeeeeeeeeeeeeeeee (CAZZO HO FINITO I SOLDI) 🐐")
            return
        if bet <= 0:
            await interaction.response.send_message("❌ Inserisci un valore positivo.")
            return
        
        #Inizializza la classe che contiene tutta la logica del gioco
        view = bj.BlackjackView(interaction.user, character_name, bet, self.pool)
        await interaction.response.send_message(
            "🐐 Behhhhhh Behhhh (Se vinco io ti scopo il culo) 🐐 \n"
            f"Saldo rimanente: {ut.format_currency(row['copper'])}\n"
            f"Hai scommesso: {ut.format_currency(bet)} \n"
            f"Pinnu: {bj.showsinglecard(view.dealer_cards[0])} (??) \n\n\n"
            f"{character_name}: {bj.showcards(view.player_cards)} ({view.player_score})",
            view=view
        )
    
    @blackjack.autocomplete("character_name")
    async def blackjack_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete_blackjack(interaction, current, self.pool)

