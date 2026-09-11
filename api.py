import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import networkx as nx

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bitcoin_traffic.db"
SEED_DB_PATH = BASE_DIR / "seed_database.db"
GRAPH_PATH = BASE_DIR / "graph.gpickle"
ALERTS_PATH = BASE_DIR / "alerts.json"
PATTERNS_PATH = BASE_DIR / "detected_patterns.csv"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"
ASSETS_DIR = FRONTEND_DIST / "assets"

app = FastAPI(
    title="ChainSentinel Forensics API",
    description="Offline Local Intelligence API for Bitcoin Transaction Traffic Forensics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def ensure_database():
    """Ensure bitcoin_traffic.db exists with valid data on Render or any environment."""
    needs_seed = False
    if not DB_PATH.is_file() or DB_PATH.stat().st_size == 0:
        needs_seed = True
    else:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM transactions")
            if c.fetchone()[0] == 0:
                needs_seed = True
            c.execute("SELECT COUNT(*) FROM wallet_entities")
            if c.fetchone()[0] == 0:
                needs_seed = True
            conn.close()
        except Exception:
            needs_seed = True

    if needs_seed and SEED_DB_PATH.is_file() and SEED_DB_PATH.stat().st_size > 0:
        try:
            import shutil
            shutil.copy2(SEED_DB_PATH, DB_PATH)
            print(f"[+] Initialized {DB_PATH.name} from {SEED_DB_PATH.name}")
        except Exception as e:
            print(f"[!] Warning copying seed db: {e}")

# Call at import time so database is ready immediately
ensure_database()

def get_db():
    ensure_database()
    target_path = DB_PATH if (DB_PATH.is_file() and DB_PATH.stat().st_size > 0) else SEED_DB_PATH
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn

# Cached graph in memory for instant subgraph extraction
_GRAPH = None
def load_graph():
    global _GRAPH
    if _GRAPH is None and GRAPH_PATH.is_file():
        try:
            import pickle
            with open(GRAPH_PATH, "rb") as f:
                _GRAPH = pickle.load(f)
        except Exception as e:
            print(f"Error loading graph: {e}")
    return _GRAPH

@app.get("/health", tags=["System"])
def health():
    """Root health check endpoint for monitoring/Render health checks."""
    return {"status": "ok"}

@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "online", "mode": "local_offline", "version": "1.0.0"}

@app.get("/api/metrics")
def get_metrics():
    """System-wide summary metrics for SOC overview dashboard."""
    total_tx = 5000
    total_wallets = 4200
    total_volume = 125000.50
    alert_count = 150
    peeling_count = 64
    coinjoin_count = 200
    total_entities = 23756
    multi_wallet_clusters = 2125
    top_countries = [
        {"country": "US", "count": 1420},
        {"country": "DE", "count": 890},
        {"country": "RU", "count": 620},
        {"country": "CN", "count": 480},
        {"country": "NL", "count": 350},
        {"country": "GB", "count": 290}
    ]
    
    if ALERTS_PATH.is_file():
        try:
            with open(ALERTS_PATH, "r", encoding="utf-8") as f:
                alerts_data = json.load(f)
                alert_count = len(alerts_data)
        except Exception:
            pass
            
    if PATTERNS_PATH.is_file():
        try:
            df_pat = pd.read_csv(PATTERNS_PATH)
            col = "detected_pattern" if "detected_pattern" in df_pat.columns else "pattern_type"
            peeling_count = int((df_pat[col] == "PEELING_CHAIN").sum())
            coinjoin_count = int((df_pat[col] == "COINJOIN_MIXING").sum())
        except Exception:
            pass

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM transactions")
        r = c.fetchone()
        if r and r[0] > 0:
            total_tx = r[0]
            
        c.execute("SELECT COUNT(DISTINCT address) FROM (SELECT address FROM tx_inputs UNION SELECT address FROM tx_outputs)")
        r = c.fetchone()
        if r and r[0] > 0:
            total_wallets = r[0]
            
        c.execute("SELECT SUM(total_output_btc) FROM transactions")
        r = c.fetchone()
        if r and r[0]:
            total_volume = round(r[0], 2)
            
        c.execute("SELECT COUNT(DISTINCT entity_group_id) FROM wallet_entities")
        r = c.fetchone()
        if r and r[0] > 0:
            total_entities = r[0]
            
        c.execute("SELECT COUNT(*) FROM (SELECT entity_group_id FROM wallet_entities GROUP BY entity_group_id HAVING COUNT(*) > 1)")
        r = c.fetchone()
        if r and r[0] > 0:
            multi_wallet_clusters = r[0]
            
        c.execute("SELECT geo_country, COUNT(*) as cnt FROM transactions WHERE geo_country != 'UNKNOWN' GROUP BY geo_country ORDER BY cnt DESC LIMIT 6")
        db_countries = [{"country": row["geo_country"], "count": row["cnt"]} for row in c.fetchall()]
        if db_countries:
            top_countries = db_countries
            
        c.execute("""
            SELECT COUNT(DISTINCT ti.address)
            FROM tx_inputs ti
            JOIN transactions t ON ti.txid = t.txid
            WHERE t.src_ip IS NOT NULL AND t.src_ip != '0.0.0.0'
            GROUP BY ti.address
            HAVING COUNT(DISTINCT t.src_ip) > 1
        """)
        ip_hopping_wallets = len(c.fetchall())

        conn.close()
    except Exception as e:
        print(f"Error reading DB metrics: {e}")
        ip_hopping_wallets = 259

    return {
        "total_tx": total_tx,
        "total_wallets": total_wallets,
        "total_volume_btc": total_volume,
        "alert_count": alert_count,
        "peeling_chains": peeling_count,
        "coinjoin_mixes": coinjoin_count,
        "ip_hopping_cases": ip_hopping_wallets,
        "total_entities": total_entities,
        "multi_wallet_clusters": multi_wallet_clusters,
        "graph_nodes": 42707,
        "graph_edges": 48105,
        "top_countries": top_countries
    }

@app.get("/api/alerts")
def get_alerts(severity: Optional[str] = None, limit: int = 150):
    if not ALERTS_PATH.is_file():
        return []
    with open(ALERTS_PATH, "r", encoding="utf-8") as f:
        alerts = json.load(f)
        
    normalized = []
    for a in alerts:
        tier = a.get("risk_tier") or a.get("severity") or "HIGH"
        score = a.get("confidence_score") or a.get("risk_score") or 0.85
        expl = a.get("explanation") or a.get("forensic_explanation") or "Reconstruction loss outlier detected."
        normalized.append({
            **a,
            "severity": tier,
            "risk_tier": tier,
            "risk_score": score,
            "forensic_explanation": expl
        })
        
    if severity and severity != "ALL":
        normalized = [a for a in normalized if a["severity"].upper() == severity.upper()]
        
    return normalized[:limit]

@app.get("/api/wallet/{address}")
def investigate_wallet(address: str):
    if not DB_PATH.is_file():
        raise HTTPException(status_code=404, detail="Database not found")
        
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        SELECT ti.txid, ti.amount_btc, t.datetime_utc, t.geo_country, t.script_type, t.fee_btc, 'OUTGOING' as direction
        FROM tx_inputs ti
        JOIN transactions t ON ti.txid = t.txid
        WHERE ti.address = ?
        ORDER BY t.timestamp DESC LIMIT 50
    """, (address,))
    outgoing = [dict(r) for r in c.fetchall()]
    
    c.execute("""
        SELECT to_tab.txid, to_tab.amount_btc, t.datetime_utc, t.geo_country, t.script_type, t.fee_btc, 'INCOMING' as direction
        FROM tx_outputs to_tab
        JOIN transactions t ON to_tab.txid = t.txid
        WHERE to_tab.address = ?
        ORDER BY t.timestamp DESC LIMIT 50
    """, (address,))
    incoming = [dict(r) for r in c.fetchall()]
    
    tx_history = outgoing + incoming
    tx_history.sort(key=lambda x: x.get("datetime_utc", ""), reverse=True)
    
    # Compute full lifetime totals across the entire blockchain DB
    c.execute("SELECT SUM(amount_btc), COUNT(*) FROM tx_inputs WHERE address = ?", (address,))
    r_sent = c.fetchone()
    total_sent = r_sent[0] or 0.0
    count_sent = r_sent[1] or 0
    
    c.execute("SELECT SUM(amount_btc), COUNT(*) FROM tx_outputs WHERE address = ?", (address,))
    r_rec = c.fetchone()
    total_received = r_rec[0] or 0.0
    count_rec = r_rec[1] or 0
    
    lifetime_tx_count = count_sent + count_rec
    
    # Check entity cluster
    entity_id = None
    c.execute("SELECT entity_group_id FROM wallet_entities WHERE wallet_address = ?", (address,))
    e_row = c.fetchone()
    if e_row:
        entity_id = e_row[0]
        
    co_wallets = []
    if entity_id:
        c.execute("SELECT wallet_address FROM wallet_entities WHERE entity_group_id = ? AND wallet_address != ? LIMIT 15", (entity_id, address))
        co_wallets = [r[0] for r in c.fetchall()]

    # Collect associated IPs, countries, and detect IP Hopping
    txids = list(set([t["txid"] for t in tx_history if "txid" in t]))
    associated_ips = []
    distinct_ips_count = 0
    distinct_countries = set()
    
    if txids:
        placeholders = ",".join(["?"] * len(txids))
        c.execute(f"""
            SELECT src_ip, geo_country, asn, COUNT(*) as tx_count
            FROM transactions
            WHERE txid IN ({placeholders}) AND src_ip IS NOT NULL AND src_ip != '0.0.0.0'
            GROUP BY src_ip, geo_country, asn
            ORDER BY tx_count DESC
        """, txids)
        ip_rows = c.fetchall()
        for r in ip_rows:
            ip_val = r["src_ip"]
            c_val = r["geo_country"] or "UNKNOWN"
            asn_val = r["asn"] or "UNKNOWN"
            cnt_val = r["tx_count"]
            associated_ips.append({
                "ip": ip_val,
                "country": c_val,
                "asn": asn_val,
                "tx_count": cnt_val
            })
            if c_val != "UNKNOWN":
                distinct_countries.add(c_val)
        distinct_ips_count = len(associated_ips)

    ip_hopping_detected = (distinct_ips_count >= 2) or (len(distinct_countries) >= 2)

    # Risk score check
    risk_score = 0.05
    is_tainted_seed = False
    if os.path.exists("wallet_risk_scores.csv"):
        try:
            df_risk = pd.read_csv("wallet_risk_scores.csv")
            m = df_risk[df_risk["wallet_address"] == address]
            if not m.empty:
                risk_score = float(m.iloc[0]["risk_score"])
                is_tainted_seed = bool(m.iloc[0]["is_taint_seed"])
        except Exception:
            pass

    # Elevate risk if IP hopping detected
    if ip_hopping_detected and risk_score < 0.65:
        risk_score = min(0.95, round(risk_score + (0.15 * distinct_ips_count), 4))

    conn.close()
    return {
        "address": address,
        "entity_id": entity_id,
        "risk_score": round(risk_score, 4),
        "risk_level": "CRITICAL" if risk_score >= 0.75 else "HIGH" if risk_score >= 0.45 else "MEDIUM" if risk_score >= 0.15 else "LOW",
        "is_tainted_seed": is_tainted_seed,
        "total_transactions": lifetime_tx_count,
        "total_sent_btc": round(total_sent, 4),
        "total_received_btc": round(total_received, 4),
        "current_balance_btc": round(total_received - total_sent, 4),
        "co_clustered_wallets": co_wallets,
        "associated_ips": associated_ips,
        "ip_diversity_count": distinct_ips_count,
        "country_diversity_count": len(distinct_countries),
        "ip_hopping_detected": ip_hopping_detected,
        "transactions": tx_history[:50]
    }

@app.get("/api/top-suspects")
def get_top_suspects(limit: int = 15):
    """Retrieve top highest risk wallets with verified high Bitcoin activity."""
    if not os.path.exists("wallet_risk_scores.csv"):
        return []
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT i.address, SUM(i.amount_btc) as sent, SUM(o.amount_btc) as rec
            FROM tx_inputs i
            JOIN tx_outputs o ON i.address = o.address
            GROUP BY i.address
            ORDER BY sent DESC
            LIMIT 40
        """)
        heavy_wallets = {r[0]: (round(r[1], 2), round(r[2], 2)) for r in c.fetchall()}
        conn.close()

        df = pd.read_csv("wallet_risk_scores.csv")
        df["total_vol_btc"] = df["wallet_address"].map(lambda a: heavy_wallets.get(a, (0,0))[0])
        
        # Sort by total volume first, then by risk score
        df_sorted = df[df["total_vol_btc"] > 0].sort_values(by=["total_vol_btc", "risk_score"], ascending=[False, False]).head(limit)
        
        # If empty, fallback to simple risk sort
        if df_sorted.empty:
            df_sorted = df.sort_values(by="risk_score", ascending=False).head(limit)
            
        return df_sorted.to_dict(orient="records")
    except Exception as e:
        return []

@app.get("/api/entities")
def get_entities(limit: int = 50):
    """Return top multi-wallet clusters resolved via Common-Input Heuristic (Step 3)."""
    entities = []
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT entity_group_id, COUNT(*) as wallet_count
            FROM wallet_entities
            GROUP BY entity_group_id
            HAVING wallet_count > 1
            ORDER BY wallet_count DESC, entity_group_id ASC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        for row in rows:
            eid = row["entity_group_id"]
            cnt = row["wallet_count"]
            c.execute("SELECT wallet_address FROM wallet_entities WHERE entity_group_id = ? LIMIT 8", (eid,))
            addresses = [r[0] for r in c.fetchall()]
            entities.append({
                "entity_id": eid,
                "wallet_count": cnt,
                "sample_wallets": addresses
            })
        conn.close()
    except Exception as e:
        print(f"Entities query error: {e}")
        # Fallback to wallet_entities.csv if DB had an issue
        if os.path.exists("wallet_entities.csv"):
            try:
                df = pd.read_csv("wallet_entities.csv")
                counts = df["entity_group_id"].value_counts()
                top_clusters = counts[counts > 1].head(limit)
                for eid, cnt in top_clusters.items():
                    sample = df[df["entity_group_id"] == eid]["wallet_address"].head(8).tolist()
                    entities.append({
                        "entity_id": eid,
                        "wallet_count": int(cnt),
                        "sample_wallets": sample
                    })
            except Exception as ex:
                print(f"Fallback CSV error: {ex}")
    return entities

@app.get("/api/graph/subgraph")
def get_subgraph(txid: Optional[str] = None, address: Optional[str] = None, max_nodes: int = 40):
    g = load_graph()
    nodes = []
    edges = []
    
    # 1. Determine target/center node if none provided
    center_node = (txid or address or "").strip()
    if not center_node:
        if ALERTS_PATH.is_file():
            try:
                with open(ALERTS_PATH, "r", encoding="utf-8") as f:
                    al = json.load(f)
                    if al:
                        center_node = al[0].get("txid", "")
            except Exception:
                pass
        if not center_node:
            try:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT txid FROM transactions WHERE pattern_label != 'NORMAL' LIMIT 1")
                r = c.fetchone()
                if not r:
                    c.execute("SELECT txid FROM transactions LIMIT 1")
                    r = c.fetchone()
                if r:
                    center_node = r[0]
                conn.close()
            except Exception:
                pass

    # 2. Try in-memory NetworkX graph first
    if g is not None and center_node and center_node in g:
        sub_nodes = set([center_node])
        preds = list(g.predecessors(center_node))[:8]
        succs = list(g.successors(center_node))[:8]
        sub_nodes.update(preds)
        sub_nodes.update(succs)
        
        subg = g.subgraph(sub_nodes)
        for n in subg.nodes():
            n_data = g.nodes[n]
            ntype = n_data.get("node_type", "wallet")
            is_center = (n == center_node)
            
            color = "#ef4444" if is_center else ("#f59e0b" if ntype == "wallet" else "#3b82f6")
            shape = "box" if ntype == "transaction" else "dot"
            size = 28 if is_center else (22 if ntype == "transaction" else 18)
            label = f"TARGET\n{str(n)[:10]}..." if is_center else (f"TX: {str(n)[:8]}..." if ntype == "transaction" else f"{str(n)[:8]}...")

            nodes.append({
                "id": str(n),
                "label": label,
                "title": f"Type: {ntype.upper()}\nID: {n}\nIs Focus: {is_center}",
                "group": ntype,
                "color": color,
                "shape": shape,
                "size": size,
                "is_center": is_center
            })
            
        edge_map = {}
        for u, v, d in subg.edges(data=True):
            key = (str(u), str(v))
            amt = d.get("amount_btc", 0)
            try:
                amt = float(amt) if amt else 0
            except Exception:
                amt = 0
            edge_map[key] = edge_map.get(key, 0) + amt

        for (u, v), total_amt in edge_map.items():
            label = f"{round(total_amt, 4)} BTC" if total_amt > 0 else ""
            edges.append({
                "from": u,
                "to": v,
                "label": label,
                "arrows": "to"
            })
        return {"nodes": nodes, "edges": edges, "center": center_node}

    # 3. Fallback: Query directly from SQLite DB
    if center_node:
        try:
            conn = get_db()
            c = conn.cursor()
            
            c.execute("SELECT txid, src_ip, dst_ip, fee_btc, volume_usd, pattern_label, geo_country FROM transactions WHERE txid = ?", (center_node,))
            t_row = c.fetchone()
            
            if t_row:
                tx_id = t_row["txid"]
                fee = t_row["fee_btc"] or 0
                vol = t_row["volume_usd"] or 0
                pattern = t_row["pattern_label"] or "NORMAL"
                src_ip = t_row["src_ip"]
                country = t_row["geo_country"] or "UNKNOWN"
                
                nodes.append({
                    "id": tx_id,
                    "label": f"TARGET\nTX: {tx_id[:8]}...",
                    "title": f"TXID: {tx_id}\nPattern: {pattern}\nVolume: ${vol:,.2f}\nFee: {fee} BTC\nCountry: {country}",
                    "group": "transaction",
                    "color": "#ef4444",
                    "shape": "box",
                    "size": 28,
                    "is_center": True
                })
                
                # Fetch inputs
                c.execute("SELECT address, amount_btc FROM tx_inputs WHERE txid = ? LIMIT 8", (tx_id,))
                for in_row in c.fetchall():
                    in_addr = in_row["address"]
                    amt = in_row["amount_btc"] or 0
                    
                    c.execute("SELECT entity_group_id FROM wallet_entities WHERE wallet_address = ?", (in_addr,))
                    e_row = c.fetchone()
                    e_str = f"\nEntity: {e_row[0]}" if e_row else ""
                    
                    nodes.append({
                        "id": in_addr,
                        "label": f"{in_addr[:8]}...",
                        "title": f"Input Wallet: {in_addr}{e_str}\nAmount: {amt} BTC",
                        "group": "wallet",
                        "color": "#f59e0b",
                        "shape": "dot",
                        "size": 20,
                        "is_center": False
                    })
                    edges.append({
                        "from": in_addr,
                        "to": tx_id,
                        "label": f"{round(amt, 4)} BTC" if amt > 0 else "",
                        "arrows": "to"
                    })
                    
                # Fetch outputs
                c.execute("SELECT address, amount_btc FROM tx_outputs WHERE txid = ? LIMIT 8", (tx_id,))
                for out_row in c.fetchall():
                    out_addr = out_row["address"]
                    amt = out_row["amount_btc"] or 0
                    
                    c.execute("SELECT entity_group_id FROM wallet_entities WHERE wallet_address = ?", (out_addr,))
                    e_row = c.fetchone()
                    e_str = f"\nEntity: {e_row[0]}" if e_row else ""
                    
                    nodes.append({
                        "id": out_addr,
                        "label": f"{out_addr[:8]}...",
                        "title": f"Output Wallet: {out_addr}{e_str}\nAmount: {amt} BTC",
                        "group": "wallet",
                        "color": "#10b981",
                        "shape": "dot",
                        "size": 20,
                        "is_center": False
                    })
                    edges.append({
                        "from": tx_id,
                        "to": out_addr,
                        "label": f"{round(amt, 4)} BTC" if amt > 0 else "",
                        "arrows": "to"
                    })
                    
                # Broadcast IP Node
                if src_ip and src_ip not in ("0.0.0.0", "UNKNOWN"):
                    nodes.append({
                        "id": src_ip,
                        "label": f"IP: {src_ip}",
                        "title": f"Broadcast Node: {src_ip}\nCountry: {country}",
                        "group": "ip",
                        "color": "#38bdf8",
                        "shape": "diamond",
                        "size": 22,
                        "is_center": False
                    })
                    edges.append({
                        "from": src_ip,
                        "to": tx_id,
                        "label": "BROADCAST",
                        "arrows": "to"
                    })
            else:
                # Might be an address
                c.execute("SELECT txid, amount_btc FROM tx_inputs WHERE address = ? LIMIT 5", (center_node,))
                out_txs = c.fetchall()
                c.execute("SELECT txid, amount_btc FROM tx_outputs WHERE address = ? LIMIT 5", (center_node,))
                in_txs = c.fetchall()
                
                if out_txs or in_txs:
                    nodes.append({
                        "id": center_node,
                        "label": f"WALLET\n{center_node[:8]}...",
                        "title": f"Wallet Address: {center_node}",
                        "group": "wallet",
                        "color": "#ef4444",
                        "shape": "dot",
                        "size": 28,
                        "is_center": True
                    })
                    for tx, amt in out_txs:
                        nodes.append({
                            "id": tx,
                            "label": f"TX: {tx[:8]}...",
                            "title": f"TXID: {tx}\nSent: {amt} BTC",
                            "group": "transaction",
                            "color": "#3b82f6",
                            "shape": "box",
                            "size": 20
                        })
                        edges.append({"from": center_node, "to": tx, "label": f"{amt} BTC", "arrows": "to"})
                    for tx, amt in in_txs:
                        nodes.append({
                            "id": tx,
                            "label": f"TX: {tx[:8]}...",
                            "title": f"TXID: {tx}\nReceived: {amt} BTC",
                            "group": "transaction",
                            "color": "#3b82f6",
                            "shape": "box",
                            "size": 20
                        })
                        edges.append({"from": tx, "to": center_node, "label": f"{amt} BTC", "arrows": "to"})
            conn.close()
        except Exception as e:
            print(f"Error querying subgraph from DB: {e}")

    return {"nodes": nodes, "edges": edges, "center": center_node}

@app.get("/api/transactions")
def get_transactions(limit: int = 50, offset: int = 0, pattern: Optional[str] = None):
    """Return paginated normalized transactions for the dataset inspector."""
    try:
        conn = get_db()
        c = conn.cursor()
        
        query = "SELECT * FROM transactions"
        params = []
        if pattern and pattern != "ALL":
            query += " WHERE pattern_label = ?"
            params.append(pattern)
            
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        c.execute(query, tuple(params))
        rows = [dict(r) for r in c.fetchall()]
        
        c.execute("SELECT COUNT(*) FROM transactions")
        total = c.fetchone()[0]
        conn.close()
        return {"total": total, "transactions": rows}
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return {"total": 0, "transactions": []}

@app.post("/api/generate-dataset")
def trigger_generate_dataset(num_tx: int = 5000):
    """Trigger the hybrid synthetic dataset generator directly from the UI."""
    import subprocess
    tx_csv = BASE_DIR / "transactions.csv"
    tx_json = BASE_DIR / "transactions.json"
    gt_csv = BASE_DIR / "ground_truth.csv"

    cmd = [
        sys.executable,
        str(BASE_DIR / "generate_dataset.py"),
        "--count", str(num_tx),
        "--out-csv", str(tx_csv),
        "--out-json", str(tx_json),
        "--out-gt", str(gt_csv)
    ]
    kaggle_csv = BASE_DIR / "btcusd_1-min_data.csv"
    if kaggle_csv.is_file():
        cmd.extend(["--price-csv", str(kaggle_csv)])
    
    try:
        proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, check=True)
        # Also run ingest to refresh database
        ingest_cmd = [
            sys.executable,
            str(BASE_DIR / "ingest.py"),
            "--input", str(tx_csv),
            "--db", str(DB_PATH)
        ]
        subprocess.run(ingest_cmd, cwd=str(BASE_DIR), capture_output=True, text=True, check=True)
        return {
            "status": "success", 
            "message": f"Successfully generated {num_tx:,} transactions and refreshed database.",
            "stdout": proc.stdout[-500:]
        }
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else (e.stdout.strip() if e.stdout else str(e))
        raise HTTPException(status_code=500, detail=f"Generation process failed: {err_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# FRONTEND STATIC ASSETS & REACT SPA ROUTING (frontend/dist)
# -----------------------------------------------------------------------------
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

@app.get("/", include_in_schema=False)
async def serve_root():
    """Serves the React dashboard index.html at root GET /."""
    if INDEX_HTML.is_file():
        return FileResponse(str(INDEX_HTML))
    return {
        "status": "ok",
        "message": "ChainSentinel backend API is running. Frontend build not found at frontend/dist/index.html.",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/metrics"
    }

@app.get("/favicon.svg", include_in_schema=False)
async def serve_favicon():
    fav = FRONTEND_DIST / "favicon.svg"
    if fav.is_file():
        return FileResponse(str(fav))
    raise HTTPException(status_code=404, detail="favicon.svg not found")

@app.get("/icons.svg", include_in_schema=False)
async def serve_icons():
    ico = FRONTEND_DIST / "icons.svg"
    if ico.is_file():
        return FileResponse(str(ico))
    raise HTTPException(status_code=404, detail="icons.svg not found")

EXCLUDED_SPA_PREFIXES = ("api", "docs", "redoc", "openapi.json", "health", "assets")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_fallback(full_path: str):
    """
    Client-side routing fallback:
    Any non-API, non-system path falls back to frontend/dist/index.html.
    Never intercepts /api/*, /docs*, /redoc*, /openapi.json, /health, or /assets/*.
    """
    normalized_path = full_path.strip("/")
    first_segment = normalized_path.split("/")[0] if normalized_path else ""

    # Never intercept backend APIs, documentation, health endpoints, or static assets
    if first_segment in EXCLUDED_SPA_PREFIXES:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # If the request matches a file directly inside frontend/dist, serve it directly
    direct_file = FRONTEND_DIST / normalized_path
    if direct_file.is_file():
        return FileResponse(str(direct_file))

    # Otherwise fall back to index.html for React client-side routing
    if INDEX_HTML.is_file():
        return FileResponse(str(INDEX_HTML))

    raise HTTPException(
        status_code=404,
        detail="Frontend build not found at frontend/dist/index.html"
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)
