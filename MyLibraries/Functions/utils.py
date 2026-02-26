import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from pathlib import Path
DB_PATH = Path("Database/bank.db")


def has_permission(interaction, owner_id: int):
    '''
    Controlla se l'autore del messaggio è anche il proprietario del conto bancario.
    Oppure se è un Master

    :param owner_id: Parametro di discord per identificare un utente
    :type owner_id: int
    '''
    # Controlla se l'autore è il proprietario
    if interaction.user.id == owner_id:
        return True
    # Controlla se ha ruolo Master o Master Supremo
    roles = [role.name for role in interaction.user.roles]
    if "Master" in roles or "Master Supremo" in roles:
        return True
    return False


def format_currency(copper_total: int):
    '''
    Formatta la visualizzazione del saldo:
    1 Platinum = 1000 Copper
    1 Gold = 100 Copper
    1 Silver = 10 Copper
    1 Copper = 1 Copper

    :param copper_total: Numero di monete di rame da convertire
    :type copper_total: int
    '''
    platinum = copper_total // 1000
    copper_total %= 1000
    gold = copper_total // 100
    copper_total %= 100
    silver = copper_total // 10
    copper = copper_total % 10
    parts = []
    if platinum: parts.append(f"🔵 {platinum} Platinum")
    if gold: parts.append(f"🟡 {gold} Gold")
    if silver: parts.append(f"⚪ {silver} Silver")
    if copper: parts.append(f"🟤 {copper} Copper")
    return ", ".join(parts) if parts else "🟤 0 Copper, You Broke 🫵"


async def character_name_autocomplete_local(interaction: discord.Interaction, current: str):
    """
    Autocomplete mentre scrivi il codice che mostra solo i personaggi su cui l'utente ha permessi
    """

    user_id = interaction.user.id
    roles = [role.name for role in interaction.user.roles]
    is_master = "Master" in roles or "Master Supremo" in roles

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if is_master:
        cursor.execute(
            """
            SELECT character_name
            FROM bank_accounts
            WHERE UPPER(character_name) LIKE UPPER(?) || '%'
            ORDER BY character_name
            LIMIT 25
            """,
            (current,)
        )
    else:
        cursor.execute(
            """
            SELECT character_name
            FROM bank_accounts
            WHERE owner_discord_id = ?
              AND UPPER(character_name) LIKE UPPER(?) || '%'
            ORDER BY character_name
            LIMIT 25
            """,
            (user_id, current)
        )

    rows = cursor.fetchall()
    conn.close()

    return [
        app_commands.Choice(
            name=row[0],
            value=row[0]
        )
        for row in rows
    ]


async def character_name_autocomplete_database(interaction: discord.Interaction, current: str, pool):
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

async def character_name_autocomplete_blackjack(interaction: discord.Interaction, current: str, pool):
    """Autocomplete che mostra solo i personaggi su cui l'utente ha permessi"""
    user_id = interaction.user.id
    async with pool.acquire() as conn:
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


async def _get_account_with_permission(interaction, conn, character_name):
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
    if not has_permission(interaction, row["owner_discord_id"]):
        await interaction.response.send_message(
            "❌ Non hai i permessi per questo conto."
        )
        return None
    return row
