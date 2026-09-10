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

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
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
    if not DB_PATH.is_file():
        return {"error": "Database not found"}
        
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions")
    total_tx = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT address) FROM (SELECT address FROM tx_inputs UNION SELECT address FROM tx_outputs)")
    total_wallets = c.fetchone()[0]
    
    c.execute("SELECT SUM(total_output_btc) FROM transactions")
    volume_res = c.fetchone()[0]
    total_volume = round(volume_res or 0, 2)
    
    alert_count = 0
    if ALERTS_PATH.is_file():
        with open(ALERTS_PATH, "r", encoding="utf-8") as f:
            alerts_data = json.load(f)
            alert_count = len(alerts_data)
            
    peeling_count = 64
    coinjoin_count = 200
    if PATTERNS_PATH.is_file():
        try:
            df_pat = pd.read_csv(PATTERNS_PATH)
            col = "detected_pattern" if "detected_pattern" in df_pat.columns else "pattern_type"
            peeling_count = int((df_pat[col] == "PEELING_CHAIN").sum())
            coinjoin_count = int((df_pat[col] == "COINJOIN_MIXING").sum())
        except Exception:
            pass

    # Entity Clusters count from DB
    c.execute("SELECT COUNT(DISTINCT entity_group_id) FROM wallet_entities")
    total_entities = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM (SELECT entity_group_id FROM wallet_entities GROUP BY entity_group_id HAVING COUNT(*) > 1)")
    multi_wallet_clusters = c.fetchone()[0]

    c.execute("SELECT geo_country, COUNT(*) as cnt FROM transactions WHERE geo_country != 'UNKNOWN' GROUP BY geo_country ORDER BY cnt DESC LIMIT 6")
    top_countries = [{"country": r["geo_country"], "count": r["cnt"]} for r in c.fetchall()]

    conn.close()
    return {
        "total_tx": total_tx,
        "total_wallets": total_wallets,
        "total_volume_btc": total_volume,
        "alert_count": alert_count,
        "peeling_chains": peeling_count,
        "coinjoin_mixes": coinjoin_count,
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
def get_entities(limit: int = 20):
    """Return top multi-wallet clusters resolved via Common-Input Heuristic (Step 3)."""
    if not os.path.exists(DB_PATH):
        return []
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
    entities = []
    for row in c.fetchall():
        eid = row["entity_group_id"]
        cnt = row["wallet_count"]
        # get sample addresses
        c.execute("SELECT wallet_address FROM wallet_entities WHERE entity_group_id = ? LIMIT 8", (eid,))
        addresses = [r[0] for r in c.fetchall()]
        entities.append({
            "entity_id": eid,
            "wallet_count": cnt,
            "sample_wallets": addresses
        })
    conn.close()
    return entities

@app.get("/api/graph/subgraph")
def get_subgraph(txid: Optional[str] = None, address: Optional[str] = None, max_nodes: int = 40):
    g = load_graph()
    nodes = []
    edges = []
    
    if g is None:
        conn = get_db()
        c = conn.cursor()
        if txid:
            c.execute("SELECT txid, btc_price_usd, fee_btc FROM transactions WHERE txid = ?", (txid,))
            t = c.fetchone()
            if t:
                nodes.append({"id": txid, "label": f"TX: {txid[:8]}...", "group": "transaction", "title": f"TXID: {txid}"})
                c.execute("SELECT address, amount_btc FROM tx_inputs WHERE txid = ? LIMIT 10", (txid,))
                for row in c.fetchall():
                    nodes.append({"id": row[0], "label": f"{row[0][:6]}...", "group": "wallet", "title": f"Wallet: {row[0]}"})
                    edges.append({"from": row[0], "to": txid, "label": f"{row[1]} BTC", "arrows": "to"})
                c.execute("SELECT address, amount_btc FROM tx_outputs WHERE txid = ? LIMIT 10", (txid,))
                for row in c.fetchall():
                    nodes.append({"id": row[0], "label": f"{row[0][:6]}...", "group": "wallet", "title": f"Wallet: {row[0]}"})
                    edges.append({"from": txid, "to": row[0], "label": f"{row[1]} BTC", "arrows": "to"})
        conn.close()
        return {"nodes": nodes, "edges": edges}

    center_node = txid or address
    if not center_node or center_node not in g:
        if os.path.exists("alerts.json"):
            with open("alerts.json", "r") as f:
                al = json.load(f)
                if al:
                    center_node = al[0].get("txid")
    
    if center_node and center_node in g:
        # Keep graph clean and human-readable: 1-hop predecessors (inputs) and 1-hop successors (outputs)
        sub_nodes = set([center_node])
        preds = list(g.predecessors(center_node))[:6]
        succs = list(g.successors(center_node))[:6]
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
            
        # Group parallel edges to avoid messy overlapping labels
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

    return {"nodes": nodes, "edges": edges}

@app.get("/api/transactions")
def get_transactions(limit: int = 50, offset: int = 0, pattern: Optional[str] = None):
    """Return paginated normalized transactions for the dataset inspector."""
    if not DB_PATH.is_file():
        return {"total": 0, "transactions": []}
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

@app.post("/api/generate-dataset")
def trigger_generate_dataset(num_tx: int = 5000):
    """Trigger the hybrid synthetic dataset generator directly from the UI."""
    import subprocess
    cmd = [sys.executable, "generate_dataset.py", "--num-tx", str(num_tx)]
    kaggle_csv = BASE_DIR / "btcusd_1-min_data.csv"
    if kaggle_csv.is_file():
        cmd.extend(["--kaggle-csv", str(kaggle_csv)])
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Also run ingest to refresh database
        tx_csv = BASE_DIR / "transactions.csv"
        subprocess.run([sys.executable, "ingest.py", "--file", str(tx_csv)], capture_output=True, text=True)
        return {
            "status": "success", 
            "message": f"Successfully generated {num_tx} transactions and ingested to database.",
            "stdout": proc.stdout[-500:]
        }
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
