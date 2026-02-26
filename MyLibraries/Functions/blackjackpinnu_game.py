import discord
from discord.ext import commands
from discord import app_commands
import random

import MyLibraries.Functions.utils as ut

card_categories = ['♥️', '♦️', '♣️', '♠️']
cards_list = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

def card_value(card):
    '''
    Calcola il valore della carta secondo le regole del Blackjack
    '''
    if card[0] in ['J', 'Q', 'K']:
        return 10
    elif card[0] == 'A':
        return 11
    else:
        return int(card[0])
    
def showcards(hand):
    '''
    Funzione per migliorare la visualizzazione delle carte.
    Prende le carte in mano e ritorna una stringa del tipo "A♣️"

    :param hand: Lista di carte in mano in formato tipo ('A','♣️')
    :type hand: tuple
    '''
    hand_str = ""
    for card in hand:
        hand_str += f"{card[0]}{card[1]}  "
    return hand_str

def showsinglecard(card):
    '''
    Funzione per migliorare la visualizzazione delle carte.
    Prende una singola carta e ritorna una stringa del tipo "A♣️"

    :param hand: Carta in formato tipo ('A','♣️')
    :type hand: tuple
    '''
    hand_str = f"{card[0]}{card[1]}  "
    return hand_str

class BlackjackView(discord.ui.View):
    '''
    Classe che contiene la logica del gioco.
    Sono inoltre presenti i pulsanti "Pesca" e "Stai"
    '''

    def __init__(self, player, character_name, bet, pool):
        '''
        Inizializza la classe BlackjackView

        :param player: Codice id della persona che sta giocando, per permettere solo a lui di premere i tasti
        :param character_name: Nome del personaggio, presente nel database e legato al player
        :param bet: Ammontare di monete di rame che scommetti
        :param pool: Chiave di collegamento al database su Neon
        '''
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
        '''
        Controlla che la persona che sta giocando sia quella che ha iniziato la partita
        '''
        return interaction.user == self.player

    @property
    def player_score(self):
        '''
        Il tag "property" sulla funzione permette di considerare questa funzione come attributo di classe
        Calcola il punteggio della mano del giocatore
        '''
        score = sum(card_value(c) for c in self.player_cards)
        aces = sum(1 for c in self.player_cards if c[0] == 'A')
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    @property
    def dealer_score(self):
        '''
        Il tag "property" sulla funzione permette di considerare questa funzione come attributo di classe
        Calcola il punteggio della mano del dealer
        '''
        score = sum(card_value(c) for c in self.dealer_cards)
        aces = sum(1 for c in self.dealer_cards if c[0] == 'A')
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    async def end_game(self, interaction: discord.Interaction):
        '''
        Comportamento del bot quando viene premuto il tasto "Stai" o in genereale quando finisce la partita
        '''
        #Intelligenza del dealer. Prima di calcolare il punteggio finale il dealer deve pescare le sue carte.
        #Segue il comportamento dei dealer nei casinò classici, ovvero pesca solo se sta sotto il 17
        while (self.dealer_score < 17):
            self.dealer_cards.append(self.deck.pop())

        #Frase con cui modificare il messaggio.
        #Alla fine di questo messaggio viene aggiunta una stringa in base al risultato della partita
        content = f"**Game Over!**\nDealer: {showcards(self.dealer_cards)} ({self.dealer_score})\n\n\n{self.character_name}: {showcards(self.player_cards)} ({self.player_score})\n\n"
        
        #Il punteggio del giocatore ha sforato il 21  - SCONFITTA
        if self.player_score > 21:
            content += "🐐 BEHHHH!! (HO VINTO IO STRONZO) 🐐\n"
            content += f"Hai perso {ut.format_currency(self.bet)}!"

            #Rimuove l'ammontare scommesso dal conto del personaggio
            async with self.pool.acquire() as conn:
                await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper - $1 
                WHERE character_name = $2""",
                self.bet, self.character_name
                )
                
                #Aggiungo a Pinnu
                await conn.execute(
                    """
                    UPDATE bank_accounts
                    SET copper = copper + $1
                    WHERE character_name = 'Pinnu'
                    """,
                    self.bet
                )

        #VITTORIA del giocatore
        elif self.dealer_score > 21 or self.player_score > self.dealer_score:
            content += "🐐 BEH! (Se ti butti in un fosso godo come uno stronzo) 🐐\n"
            content += f"Hai vinto {ut.format_currency(self.bet)}!"

            async with self.pool.acquire() as conn:
                #Aggiungo al giocatore
                await conn.execute(
                """UPDATE bank_accounts 
                SET copper = copper + $1 
                WHERE character_name = $2""",
                self.bet, self.character_name
                )
                #Tolgo a Pinnu
                await conn.execute(
                    """
                    UPDATE bank_accounts
                    SET copper = copper - $1
                    WHERE character_name = 'Pinnu'
                    """,
                    self.bet
                )

        #SCONFITTA del giocatore nel caso in cui il dealer abbia un punteggio più alto 
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
                    
                #Aggiungo a Pinnu
                await conn.execute(
                    """
                    UPDATE bank_accounts
                    SET copper = copper + $1
                    WHERE character_name = 'Pinnu'
                    """,
                    self.bet
                )
        else:
            content += "🐐 Beh beh (Pareggio! Rigiochiamo!) 🐐\n"

        #Setta il gioco a finito
        self.finished = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=content, view=BlackjackEndView(self.player, self.character_name, self.bet, self.pool))

    @discord.ui.button(label="Pesca", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        '''
        Pulsante "Hit". 
        Se il punteggio del giocatore supera il 21 la partita finisce, altrimenti permette la pesca di altre carte.
        '''
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
        '''
        Pulsante "Stai". 
        Conclude la partita e procede al calcolo dei punti.
        '''
        if interaction.user != self.player or self.finished:
            return
        await self.end_game(interaction)


class BlackjackEndView(discord.ui.View):
    '''
    Classe che contiene i pulsanti "Rigioca" e "Termina Partita" che compaiono solo dopo la fine della partita
    '''

    def __init__(self, player, character_name, bet, pool):
        '''
        Inizializza la classe BlackjackEndView

        :param player: Codice id della persona che sta giocando, per permettere solo a lui di premere i tasti
        :param character_name: Nome del personaggio, presente nel database e legato al player
        :param bet: Ammontare di monete di rame che scommetti
        :param pool: Chiave di collegamento al database su Neon
        '''
        super().__init__(timeout=60)
        self.player = player
        self.character_name = character_name
        self.bet = bet
        self.pool = pool

    async def interaction_check(self, interaction: discord.Interaction):
        '''
        Controlla che la persona che sta giocando sia quella che ha iniziato la partita
        '''
        return interaction.user.id == self.player.id

    @discord.ui.button(label="Rigioca", style=discord.ButtonStyle.success)
    async def replay(self, interaction: discord.Interaction, button: discord.ui.Button):
        '''
        Pulsante "Rigioca". 
        Controlla che hai abbastanza fondi per continuare a giocare, nel caso affermativo ti rimanda alla classe BlackjackView
        '''
        async with self.pool.acquire() as conn:
            row = await ut._get_account_with_permission(interaction, conn, self.character_name)
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
        view=BlackjackView(self.player, self.character_name, self.bet, self.pool)
        if self.bet > row['copper']:
            await interaction.response.send_message("🐐 Beeeh eheheheh (Ma se hai finito i soldi eheheh) 🐐")
            return
        elif self.bet > row_Pinnu['copper']:
            await interaction.response.send_message("🐐 Beeeeeeeeeeeeeeeee (CAZZO HO FINITO I SOLDI) 🐐")
            return
        else:
            await interaction.response.edit_message(
                content=f"🐐 Behhhhhh Behhhh (Se vinco io ti scopo il culo) 🐐 \nSaldo rimanente: {ut.format_currency(row['copper'])}\nHai scommesso: {ut.format_currency(self.bet)} \nPinnu: {showsinglecard(view.dealer_cards[0])} (??) \n\n\n{self.character_name}: {showcards(view.player_cards)} ({view.player_score})",
                view=view
            )

    @discord.ui.button(label="Termina partita", style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        '''
        Pulsante "Termina partita". 
        Termina la partita con un messaggio senza pulsanti
        '''
        await interaction.response.edit_message(
            content="🐐 BEH!? (Scappi, pivello!?)",
            view=None
        )