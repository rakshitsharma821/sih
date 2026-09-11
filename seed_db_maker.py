import sqlite3
import os
import json

def make_seed_db(output_db="seed_database.db"):
    if os.path.exists(output_db):
        os.remove(output_db)

    src_conn = sqlite3.connect("bitcoin_traffic.db")
    src_c = src_conn.cursor()

    # Get all alert TXIDs
    alert_txs = set()
    if os.path.exists("alerts.json"):
        with open("alerts.json", "r") as f:
            alerts = json.load(f)
            alert_txs = set(a["txid"] for a in alerts)
    print(f"Loaded {len(alert_txs)} alert txids")

    # Select representative transactions
    placeholders = ",".join(["?"] * len(alert_txs))
    query = f"""
    SELECT txid FROM transactions WHERE txid IN ({placeholders})
    UNION
    SELECT txid FROM (SELECT txid FROM transactions WHERE pattern_label = 'PEELING_CHAIN' LIMIT 800)
    UNION
    SELECT txid FROM (SELECT txid FROM transactions WHERE pattern_label = 'COINJOIN_MIXING' LIMIT 600)
    UNION
    SELECT txid FROM (SELECT txid FROM transactions WHERE pattern_label LIKE 'STATISTICAL%' LIMIT 600)
    UNION
    SELECT txid FROM (SELECT txid FROM transactions WHERE pattern_label = 'NORMAL' LIMIT 3000)
    """
    src_c.execute(query, list(alert_txs))
    chosen_txs = set(r[0] for r in src_c.fetchall())
    print(f"Total chosen txs: {len(chosen_txs)}")

    dst_conn = sqlite3.connect(output_db)
    dst_c = dst_conn.cursor()

    # Copy schemas
    for tbl in ["transactions", "tx_inputs", "tx_outputs", "wallet_entities"]:
        src_c.execute(f'SELECT sql FROM sqlite_master WHERE type="table" AND name="{tbl}"')
        row = src_c.fetchone()
        if row:
            dst_c.execute(row[0])

    # Copy transactions
    tx_placeholders = ",".join(["?"] * len(chosen_txs))
    src_c.execute(f"SELECT * FROM transactions WHERE txid IN ({tx_placeholders})", list(chosen_txs))
    tx_rows = src_c.fetchall()
    if tx_rows:
        dst_c.executemany(f"INSERT INTO transactions VALUES ({','.join(['?']*len(tx_rows[0]))})", tx_rows)

    # Copy inputs
    src_c.execute(f"SELECT * FROM tx_inputs WHERE txid IN ({tx_placeholders})", list(chosen_txs))
    in_rows = src_c.fetchall()
    if in_rows:
        dst_c.executemany(f"INSERT INTO tx_inputs VALUES ({','.join(['?']*len(in_rows[0]))})", in_rows)

    # Copy outputs
    src_c.execute(f"SELECT * FROM tx_outputs WHERE txid IN ({tx_placeholders})", list(chosen_txs))
    out_rows = src_c.fetchall()
    if out_rows:
        dst_c.executemany(f"INSERT INTO tx_outputs VALUES ({','.join(['?']*len(out_rows[0]))})", out_rows)

    # Copy wallet_entities
    src_c.execute("SELECT * FROM wallet_entities")
    ent_rows = src_c.fetchall()
    if ent_rows:
        dst_c.executemany(f"INSERT INTO wallet_entities VALUES ({','.join(['?']*len(ent_rows[0]))})", ent_rows)

    # Indexes
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_tx_country ON transactions(geo_country);",
        "CREATE INDEX IF NOT EXISTS idx_inputs_txid ON tx_inputs(txid);",
        "CREATE INDEX IF NOT EXISTS idx_inputs_address ON tx_inputs(address);",
        "CREATE INDEX IF NOT EXISTS idx_outputs_txid ON tx_outputs(txid);",
        "CREATE INDEX IF NOT EXISTS idx_outputs_address ON tx_outputs(address);",
        "CREATE INDEX IF NOT EXISTS idx_entity_wallet ON wallet_entities(wallet_address);",
        "CREATE INDEX IF NOT EXISTS idx_entity_group ON wallet_entities(entity_group_id);"
    ]:
        dst_c.execute(idx)

    dst_conn.commit()
    dst_conn.execute("VACUUM;")
    dst_conn.close()
    src_conn.close()

    size_mb = os.path.getsize(output_db) / (1024 * 1024)
    print(f"Created {output_db} successfully! Size: {size_mb:.2f} MB")

if __name__ == "__main__":
    make_seed_db()
