Inserire un file nominato ".env" in cui è presente:
DISCORD_TOKEN = $Token del bot$

Il bot è hostato su fly.io
Il database invece su neon.com

Il database contiene:
                id (SERIAL PRIMARY KEY)
                character_name (TEXT)
                owner_discord_id (BIGINT)
                copper (INTEGER)

Nella visualizzazione cambio da copper in Platinum Gold Silver Copper
Platinum (1000 copper)
Gold (100 copper)
Silver (10 copper)
Copper (1 copper)