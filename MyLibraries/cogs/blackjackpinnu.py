import discord
from discord.ext import commands
from discord import app_commands
import random

import MyLibraries.Functions.utils as ut

card_categories = ['♥️', '♦️', '♣️', '♠️']
cards_list = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

def card_value(card):
    if card[0] in ['J', 'Q', 'K']:
        return 10
    elif card[0] == 'A':
        return 11
    else:
        return int(card[0])
    
def showcards(hand):
    hand_str = ""
    for card in hand:
        hand_str += f"{card[0]}{card[1]}  "
    return hand_str

def showsinglecard(card):
    hand_str = f"{card[0]}{card[1]}  "
    return hand_str


class BlackjackEndView(discord.ui.View):
    def __init__(self, player, character_name, bet, pool):
        super().__init__(timeout=60)
        self.player = player
        self.character_name = character_name
        self.bet = bet
        self.pool = pool

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.player.id

    @discord.ui.button(label="Rigioca", style=discord.ButtonStyle.success)
    async def replay(self, interaction: discord.Interaction, button: discord.ui.Button):
        view=BlackjackView(self.player, self.character_name, self.bet, self.pool)
        await interaction.response.edit_message(
            content=f"🐐 Behhhhhh Behhhh (Se vinco io ti scopo il culo) 🐐 \nHai scommesso: {ut.format_currency(self.bet)} \nPinnu: {showsinglecard(view.dealer_cards[0])} (??) \n\n\n{self.character_name}: {showcards(view.player_cards)} ({view.player_score})",
            view=view
        )

    @discord.ui.button(label="Termina partita", style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="🐐 BEH!? (Scappi, pivello!?)",
            view=None
        )

class BlackjackView(discord.ui.View):
    def __init__(self, player, character_name, bet, pool):
        super().__init__(timeout=120)
        self.player = player
        self.character_name = character_name
        self.bet = bet
        self.pool = pool

        self.deck = [(card, suit) for suit in card_categories for card in cards_list]
        random.shuffle(self.deck)
        self.player_cards = [self.deck.pop(), self.deck.pop()]
        self.dealer_cards = [self.deck.pop(), self.deck.pop()]
        self.finished = False
        
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.player

    @property
    def player_score(self):
        score = sum(card_value(c) for c in self.player_cards)
        aces = sum(1 for c in self.player_cards if c[0] == 'A')
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    @property
    def dealer_score(self):
        score = sum(card_value(c) for c in self.dealer_cards)
        aces = sum(1 for c in self.dealer_cards if c[0] == 'A')
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    async def end_game(self, interaction: discord.Interaction):
        while (self.dealer_score < 17 or (self.dealer_score < self.player_score and self.dealer_score < 21)):
            self.dealer_cards.append(self.deck.pop())
        content = f"**Game Over!**\nDealer: {showcards(self.dealer_cards)} ({self.dealer_score})\n\n\n{self.character_name}: {showcards(self.player_cards)} ({self.player_score})\n\n"
        if self.player_score > 21:
            content += "🐐 BEHHHH!! (HO VINTO IO STRONZO) 🐐\n"
            content += f"Hai perso {ut.format_currency(self.bet)}!"

            async with self.pool.acquire() as conn:
                await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper - $1 
                WHERE character_name = $2""",
                self.bet, self.character_name
            )

        elif self.dealer_score > 21 or self.player_score > self.dealer_score:
            content += "🐐 BEH! (Se ti butti in un fosso godo come uno stronzo) 🐐\n"
            content += f"Hai vinto {ut.format_currency(self.bet)}!"

            async with self.pool.acquire() as conn:
                await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper + $1 
                WHERE character_name = $2""",
                self.bet, self.character_name
            )

        elif self.player_score < self.dealer_score:
            content += "🐐 BEHHHH!! (HO VINTO IO STRONZO) 🐐\n"
            content += f"Hai perso {ut.format_currency(self.bet)}!"

            async with self.pool.acquire() as conn:
                await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper - $1 
                WHERE character_name = $2""",
                self.bet, self.character_name
            )
        else:
            content += "🐐 Beh beh (Pareggio! Nel pareggio, il dealer prende tutto!) 🐐\n"
            content += f"Hai perso {ut.format_currency(self.bet)}!"

            async with self.pool.acquire() as conn:
                await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper - $1 
                WHERE character_name = $2""",
                self.bet, self.character_name
            )

        self.finished = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=content, view=BlackjackEndView(self.player, self.character_name, self.bet, self.pool))

    @discord.ui.button(label="Pesca", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player or self.finished:
            return
        self.player_cards.append(self.deck.pop())
        if self.player_score > 21:
            await self.end_game(interaction)
        else:
            await interaction.response.edit_message(
                content=f"🐐 Beehhh (Tanto ho la vittoria in zampa!) 🐐 \nPinnu: {showsinglecard(self.dealer_cards[0])} (??)\n\n\n{self.character_name}: {showcards(self.player_cards)} ({self.player_score})\nIn palio ci sono {ut.format_currency(self.bet)}, scegli bene!",
                view=self
            )

    @discord.ui.button(label="Stai", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player or self.finished:
            return
        await self.end_game(interaction)

class BlackjackPinnu(commands.Cog):
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

    @app_commands.command(name="blackjack", description="Inizia una partita a Blackjack con Pinnu")
    @app_commands.describe(character_name="Nome del personaggio")
    @app_commands.describe(bet="Quanto scommetti?")
    async def blackjack(self, interaction: discord.Interaction, character_name: str, bet: int):
        async with self.pool.acquire() as conn:
            row = await self._get_account_with_permission(interaction, conn, character_name)
            if not row:
                return
        if bet > row['copper']:
            await interaction.response.send_message("❌ Non hai così tanti soldi...")
            return
        if bet <= 0:
            await interaction.response.send_message("❌ Inserisci un valore positivo.")
            return
        
        view = BlackjackView(interaction.user, character_name, bet, self.pool)
        await interaction.response.send_message(
            "🐐 Behhhhhh Behhhh (Se vinco io ti scopo il culo) 🐐 \n"
            f"Hai scommesso: {ut.format_currency(bet)} \n"
            f"Pinnu: {showsinglecard(view.dealer_cards[0])} (??) \n\n\n"
            f"{character_name}: {showcards(view.player_cards)} ({view.player_score})",
            view=view
        )
    
    @blackjack.autocomplete("character_name")
    async def blackjack_autocomplete(self, interaction: discord.Interaction, current: str):
        return await ut.character_name_autocomplete_blackjack(interaction, current, self.pool)

