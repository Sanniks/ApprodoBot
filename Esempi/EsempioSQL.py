import sqlite3
from pathlib import Path

# Percorso del database locale
DB_PATH = Path("bank.db")

# ---------- INIZIALIZZAZIONE DATABASE ----------
def init_db():
    """Crea il database e la tabella se non esistono"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT NOT NULL UNIQUE,
            owner_discord_id INTEGER NOT NULL,
            copper INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print("Database inizializzato correttamente.")

# ---------- FUNZIONI BASE ----------
def create_account(character_name: str, owner_id: int, copper: int = 0):
    """Crea un nuovo conto bancario"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO bank_accounts (character_name, owner_discord_id, copper) VALUES (?, ?, ?)",
            (character_name, owner_id, copper)
        )
        conn.commit()
        print(f"✅ Conto creato per {character_name} (Owner ID: {owner_id}, Copper: {copper})")
    except sqlite3.IntegrityError:
        print(f"❌ Errore: il conto {character_name} esiste già.")
    conn.close()

def get_account(character_name: str):
    """Restituisce il conto di un personaggio"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT character_name, owner_discord_id, copper FROM bank_accounts WHERE character_name = ?",
        (character_name,)
    )
    row = cursor.fetchone()
    conn.close()
    return row  # None se non esiste

def update_copper(character_name: str, amount: int):
    """Aggiorna il numero di copper (aggiunge o rimuove)"""
    account = get_account(character_name)
    if not account:
        print(f"❌ Nessun conto trovato per {character_name}")
        return
    new_total = account[2] + amount
    if new_total < 0:
        print(f"❌ Saldo insufficiente per {character_name}")
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bank_accounts SET copper = ? WHERE character_name = ?",
        (new_total, character_name)
    )
    conn.commit()
    conn.close()
    print(f"✅ {('Aggiunti' if amount>0 else 'Rimossi')} {abs(amount)} copper a {character_name}. Saldo ora: {new_total}")

def delete_account(character_name: str):
    """Elimina un conto"""
    account = get_account(character_name)
    if not account:
        print(f"❌ Nessun conto trovato per {character_name}")
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bank_accounts WHERE character_name = ?", (character_name,))
    conn.commit()
    conn.close()
    print(f"🔥 Conto di {character_name} eliminato.")

def list_accounts():
    """Stampa tutti i conti"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT character_name, owner_discord_id, copper FROM bank_accounts")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        print("📂 Nessun conto presente.")
        return
    print("📂 Tutti i conti:")
    for row in rows:
        print(f"- {row[0]} (Owner ID: {row[1]}, Copper: {row[2]})")

# ---------- FUNZIONE UTILE ----------
def format_currency(copper_total: int):
    """Formatta il saldo in Platinum, Gold, Silver, Copper"""
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

# ---------- ESEMPIO DI UTILIZZO ----------
if __name__ == "__main__":
    init_db()
    create_account("Bhar", 1234567890, 150)
    create_account("Alice", 987654321, 320)
    list_accounts()
    update_copper("Bhar", 50)
    update_copper("Alice", -100)
    print(get_account("Bhar"))
    delete_account("Alice")
    list_accounts()
