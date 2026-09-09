#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // AI-Powered Bitcoin Transaction Intelligence
FORENSIC SURVEILLANCE & INVESTIGATION CONSOLE (SIH26146)
===================================================================================
Features:
- Law Enforcement / FIU Cybersecurity Investigation Platform
- Unified Top-Level Navigation Tabs (No Hidden Sidebar)
- Premium Dark Slate & Bitcoin Gold Styling (.streamlit/config.toml)
- Suspect Wallet Investigation with Dropdown & Click-to-Profile
- Interactive Visual Link-Analysis Network Graph
- Ranked Forensic Alerts with Dynamic Evidence & SHAP Attributions
- Native Ingestion & 1-Click Auto-Dataset Generator
- Full Technical Methodology Write-up for SIH Evaluation
===================================================================================
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

# ===================================================================================
# 1. PAGE CONFIG & STYLING
# ===================================================================================
st.set_page_config(
    page_title="ChainSentinel // Bitcoin Forensics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800;900&display=swap');

    :root {
        --bg-main: #0b0f19;
        --bg-card: #151d2e;
        --bg-hover: #1c263c;
        --border: #243147;
        --amber: #f59e0b;
        --text-bright: #f8fafc;
        --text-sub: #94a3b8;
        --crit: #ef4444;
        --high: #f97316;
        --med: #eab308;
        --low: #10b981;
    }

    .stApp {
        background-color: var(--bg-main);
        color: var(--text-bright);
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* Top Brand Header */
    .brand-bar {
        background: linear-gradient(90deg, #151d2e 0%, #0e1422 100%);
        border: 1px solid var(--border);
        border-left: 5px solid var(--amber);
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.35);
    }

    /* Top Tabs Styling (High Contrast & Glowing) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0e1422;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid var(--border);
        margin-bottom: 22px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #151d2e;
        border: 1px solid var(--border);
        border-radius: 6px;
        color: #cbd5e1 !important;
        padding: 10px 18px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #1e293b;
        color: #ffffff !important;
        border-color: var(--amber);
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(245, 158, 11, 0.18) !important;
        border-color: var(--amber) !important;
        color: #f59e0b !important;
        font-weight: 700;
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);
    }

    /* Metric Cards */
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-top: 3px solid var(--amber);
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 12px;
        transition: transform 0.15s;
    }
    .kpi-card:hover { transform: translateY(-2px); }
    .kpi-card.danger { border-top-color: var(--crit); }
    .kpi-card.info { border-top-color: #38bdf8; }
    .kpi-label {
        font-size: 11px;
        text-transform: uppercase;
        color: var(--text-sub);
        letter-spacing: 0.8px;
        font-weight: 700;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 800;
        color: #ffffff;
        margin-top: 4px;
        font-family: 'IBM Plex Mono', monospace;
    }
    .kpi-sub { font-size: 11px; color: #64748b; margin-top: 2px; }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
        font-family: 'IBM Plex Mono', monospace;
    }
    .badge-crit { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #b91c1c; }
    .badge-high { background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid #c2410c; }
    .badge-med { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid #a16207; }
    .badge-low { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #047857; }

    /* Info Callout */
    .callout {
        background: #151d2e;
        border: 1px solid var(--border);
        border-left: 4px solid var(--amber);
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ===================================================================================
# 2. AUTOMATIC PIPELINE ORCHESTRATION & CACHED LOADERS
# ===================================================================================
def auto_generate_pipeline(count: int = 8000, price_csv: str = "btcusd_1-min_data.csv") -> bool:
    try:
        import generate_dataset
        gen = generate_dataset.BitcoinDatasetGenerator(
            total_txs=count,
            price_csv=price_csv if os.path.exists(price_csv) else "btcusd_1-min_data.csv",
            seed=42
        )
        gen.generate()
        gen.export("transactions.csv", "transactions.json", "ground_truth.csv")

        import ingest
        pipe = ingest.IngestionPipeline(db_path="bitcoin_traffic.db", batch_size=1000)
        pipe.process_file("transactions.csv")
        pipe.finish()

        import graph_builder
        builder = graph_builder.ChainSentinelGraphBuilder(db_path="bitcoin_traffic.db")
        builder.build_graph()
        builder.save("graph.gpickle", "wallet_entities.csv")

        import alert_generator
        ag = alert_generator.AlertGenerator(db_path="bitcoin_traffic.db", graph_path="graph.gpickle")
        ag.generate_alerts(top_n=150)
        ag.export("alerts.csv", "alerts.json")

        return True
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        return False


@st.cache_data
def get_db_stats(db_path: str = "bitcoin_traffic.db"):
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        tx_count = conn.execute("SELECT count(*) FROM transactions;").fetchone()[0]
        if tx_count == 0:
            conn.close()
            return None

        total_vol = conn.execute("SELECT sum(volume_usd) FROM transactions;").fetchone()[0] or 0.0
        distinct_ips = conn.execute("SELECT count(distinct src_ip) FROM transactions;").fetchone()[0]
        distinct_in = conn.execute("SELECT count(distinct address) FROM tx_inputs;").fetchone()[0]
        distinct_out = conn.execute("SELECT count(distinct address) FROM tx_outputs;").fetchone()[0]

        df_patterns = pd.read_sql_query("""
            SELECT pattern_label as "Pattern Typology", count(*) as "Transactions",
                   round(sum(volume_usd), 2) as "Volume (USD)"
            FROM transactions
            GROUP BY pattern_label
            ORDER BY "Transactions" DESC
        """, conn)

        df_asns = pd.read_sql_query("""
            SELECT asn as "Autonomous System (ASN)", count(*) as "Transactions",
                   count(distinct src_ip) as "Unique Nodes",
                   round(sum(volume_usd), 2) as "Total USD Volume"
            FROM transactions
            GROUP BY asn
            ORDER BY "Transactions" DESC
            LIMIT 10
        """, conn)

        df_sample_tx = pd.read_sql_query("""
            SELECT txid as "TXID", datetime_utc as "Timestamp (UTC)", src_ip as "Source IP",
                   geo_country as "Geo", script_type as "Script", fee_btc as "Fee (BTC)",
                   round(volume_usd, 2) as "Volume ($)", pattern_label as "Detected Pattern"
            FROM transactions
            WHERE pattern_label != 'NORMAL'
            ORDER BY timestamp DESC
            LIMIT 12
        """, conn)

        conn.close()
        return {
            "tx_count": tx_count,
            "total_vol": total_vol,
            "distinct_ips": distinct_ips,
            "total_wallets": distinct_in + distinct_out,
            "df_patterns": df_patterns,
            "df_asns": df_asns,
            "df_sample_tx": df_sample_tx
        }
    except Exception:
        return None


@st.cache_data
def load_alerts(alerts_path: str = "alerts.json") -> List[Dict[str, Any]]:
    if not os.path.exists(alerts_path):
        return []
    try:
        with open(alerts_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@st.cache_data
def load_risk_table(csv_path: str = "wallet_risk_scores.csv") -> pd.DataFrame:
    if os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


# Load system data
stats = get_db_stats()
alerts_data = load_alerts()
df_risk = load_risk_table()


# ===================================================================================
# 3. TOP BRANDING BANNER
# ===================================================================================
st.markdown("""
<div class="brand-bar">
    <div style="display:flex; align-items:center; gap:14px;">
        <div style="background:#f59e0b; width:44px; height:44px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#000; font-weight:900; font-size:26px; box-shadow:0 0 14px rgba(245,158,11,0.35);">
            &#8383;
        </div>
        <div>
            <div style="font-size:22px; font-weight:900; color:#fff; letter-spacing:0.5px;">ChainSentinel</div>
            <div style="font-size:11px; color:#f59e0b; font-weight:700; text-transform:uppercase; letter-spacing:0.8px;">AI-Powered Bitcoin Transaction Intelligence & Forensic Surveillance</div>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.35); padding:5px 12px; border-radius:4px; font-size:11px; font-family:'IBM Plex Mono'; font-weight:600;">
            ● CYBER FORENSICS NODE ACTIVE
        </span>
    </div>
</div>
""", unsafe_allow_html=True)


# Auto-initialization check
if not stats:
    st.warning("⚠️ No database detected! Click below to automatically generate 8,000 synthetic transactions and train all AI models:")
    if st.button("🚀 AUTO-GENERATE DATASET & RUN FULL PIPELINE (1-CLICK)", type="primary", use_container_width=True):
        with st.status("Executing End-to-End Pipeline...", expanded=True) as sbox:
            auto_generate_pipeline(count=8000)
            sbox.update(label="Complete! Initializing...", state="complete")
        st.cache_data.clear()
        st.rerun()
    st.stop()


# ===================================================================================
# 4. UNMISSABLE TOP-LEVEL NAVIGATION TABS (All core views directly accessible!)
# ===================================================================================
tab_overview, tab_alerts, tab_graph, tab_wallets, tab_ingest, tab_pipeline, tab_writeup = st.tabs([
    "🛰️ Threat Overview",
    f"🚨 Ranked Forensic Alerts ({len(alerts_data)})",
    "🕸️ Link-Analysis Graph",
    f"🔍 Suspect Wallet Investigation ({len(df_risk):,} Wallets)",
    "📥 Smart Ingestion & Dataset Engine",
    "⚡ Pipeline Control Center",
    "📑 Technical Write-up (SIH Docs)"
])


# ===================================================================================
# TAB 1: THREAT OVERVIEW
# ===================================================================================
with tab_overview:
    st.markdown("### 🛰️ Executive Threat Surveillance")
    st.markdown("Real-time network surveillance correlating UTXO topology, behavioral anomalies, and autonomous system telemetry.")

    # 4 Sleek KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Transactions Profiled</div>
                <div class="kpi-value">{stats['tx_count']:,}</div>
                <div class="kpi-sub">Total Monitored: ${stats['total_vol']/1e6:.2f}M USD</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="kpi-card info">
                <div class="kpi-label">Active Wallet Entities</div>
                <div class="kpi-value" style="color:#38bdf8;">{len(df_risk):,}</div>
                <div class="kpi-sub">Clustered via Common-Input DSU</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        n_crit = sum(1 for a in alerts_data if a.get("risk_tier") == "CRITICAL")
        st.markdown(f"""
            <div class="kpi-card danger">
                <div class="kpi-label">High-Confidence Alerts</div>
                <div class="kpi-value" style="color:#ef4444;">{len(alerts_data):,}</div>
                <div class="kpi-sub">{n_crit} Classified as Critical Risk</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Monitored P2P Relay Nodes</div>
                <div class="kpi-value" style="color:#f59e0b;">{stats['distinct_ips']:,}</div>
                <div class="kpi-sub">Global IP & Autonomous Systems</div>
            </div>
        """, unsafe_allow_html=True)

    # Informational Guide
    st.markdown("""
        <div class="callout">
            <strong style="color:#f59e0b;">🧭 WHAT IS CHAINSENTINEL & HOW IT WORKS:</strong>
            <div style="font-size:12px; color:#cbd5e1; margin-top:6px; line-height:1.6;">
                ChainSentinel is an <strong>AI-Powered Blockchain Intelligence & Forensics Platform</strong> built for law enforcement and cybersecurity analysts. 
                <br/>&bull; You do <strong>NOT connect a personal MetaMask wallet</strong> here. Instead, ChainSentinel monitors public Bitcoin network traffic to detect laundering, peeling chains, mixing pools, and high-risk criminal wallets.
                <br/>&bull; Click the <strong>Tabs at the top</strong> to jump directly into:
                <strong>🚨 Ranked Alerts</strong>, <strong>🕸️ Link-Analysis Graph</strong>, <strong>🔍 Suspect Wallet Investigation</strong>, or <strong>📥 Smart Ingestion</strong>!
            </div>
        </div>
    """, unsafe_allow_html=True)

    c_pat, c_asn = st.columns(2)
    with c_pat:
        st.markdown("#### 📊 Detected Anomaly Typologies in Traffic")
        st.dataframe(stats['df_patterns'], use_container_width=True, hide_index=True)
    with c_asn:
        st.markdown("#### 🌐 Top Autonomous Systems (Relay Concentration)")
        st.dataframe(stats['df_asns'], use_container_width=True, hide_index=True)

    st.markdown("#### 🚨 Latest Detected Suspicious Transactions")
    st.dataframe(stats['df_sample_tx'], use_container_width=True, hide_index=True)


# ===================================================================================
# TAB 2: RANKED FORENSIC ALERTS (150 Incidents with SHAP & Evidence)
# ===================================================================================
with tab_alerts:
    st.markdown("### 🚨 Ranked Forensic Intelligence Alerts")
    st.markdown("Multi-signal ensemble detections combining Isolation Forest, Autoencoders, Peeling Chains, CoinJoin, and Taint Propagation.")

    if not alerts_data:
        st.warning("No alerts loaded. Run the pipeline in the '⚡ Pipeline Control Center' tab.")
    else:
        fc1, fc2, fc3 = st.columns([2, 2, 2])
        with fc1:
            tier_filt = st.selectbox("Filter Risk Tier", ["ALL", "CRITICAL", "HIGH", "MEDIUM"])
        with fc2:
            all_flags = sorted(list({f for a in alerts_data for f in a.get("flags", [])}))
            flag_filt = st.selectbox("Filter Pattern Flag", ["ALL"] + all_flags)
        with fc3:
            min_c = st.slider("Minimum Confidence Score", 0.0, 1.0, 0.45, 0.05)

        filtered_alerts = [
            a for a in alerts_data
            if (tier_filt == "ALL" or a.get("risk_tier") == tier_filt) and
               (flag_filt == "ALL" or flag_filt in a.get("flags", [])) and
               (a.get("confidence_score", 0.0) >= min_c)
        ]

        st.caption(f"Showing **{len(filtered_alerts)}** of {len(alerts_data)} ranked alerts matching filters.")

        for a in filtered_alerts[:60]:
            tier = a.get("risk_tier", "MEDIUM")
            badge_class = "badge-crit" if tier == "CRITICAL" else ("badge-high" if tier == "HIGH" else "badge-med")
            conf_pct = int(a.get("confidence_score", 0.0) * 100)

            with st.expander(f"[{tier}] {a['alert_id']} — {a['primary_flag']} | Confidence: {conf_pct}% | TX: {a['txid'][:16]}..."):
                st.markdown(f"""
                    <div style="background:#151d2e; padding:12px 16px; border-radius:6px; border-left:4px solid #f59e0b; margin-bottom:12px;">
                        <span class="badge {badge_class}">{tier}</span>
                        <strong style="margin-left:8px; color:#fff;">Forensic Evidence & Explanation:</strong>
                        <div style="font-size:12px; color:#e2e8f0; margin-top:6px; line-height:1.6;">{a['explanation']}</div>
                    </div>
                """, unsafe_allow_html=True)

                col_tx, col_w, col_geo = st.columns(3)
                with col_tx:
                    st.markdown("**Transaction ID**")
                    st.code(a['txid'])
                with col_w:
                    st.markdown("**Primary Target Wallet**")
                    st.code(a['primary_wallet'])
                with col_geo:
                    st.markdown("**Relay Node Geo / ASN**")
                    st.write(f"🌍 `{a.get('geo_country', 'UNKNOWN')}` &bull; `{a.get('asn', 'UNKNOWN')}`")

                st.markdown("**Evidence Links & Topology Drilldown**")
                st.json(a.get("evidence_links", {}))


# ===================================================================================
# TAB 3: LINK-ANALYSIS GRAPH EXPLORER (Vis.js Interactive)
# ===================================================================================
with tab_graph:
    st.markdown("### 🕸️ Interactive Link-Analysis Graph Explorer")
    st.markdown("Forensic ego-network tracing multi-hop fund flows, peeling chains, mixing anonymity sets, and IP colocation.")

    if not alerts_data:
        st.warning("Please generate alerts to inspect graph topologies.")
    else:
        alert_choice = st.selectbox(
            "Select Incident to Graph:",
            [f"{a['alert_id']} | {a['primary_flag']} ({int(a['confidence_score']*100)}%) — TX: {a['txid'][:14]}..." for a in alerts_data[:30]]
        )
        sel_idx = [f"{a['alert_id']} | {a['primary_flag']} ({int(a['confidence_score']*100)}%) — TX: {a['txid'][:14]}..." for a in alerts_data[:30]].index(alert_choice)
        sel_alert = alerts_data[sel_idx]

        links = sel_alert.get("evidence_links", {})
        txid = links.get("txid", "TX")
        primary_w = links.get("primary_wallet", "W")
        connected_wallets = links.get("connected_wallets", [])
        connected_ips = links.get("connected_ips", [])

        nodes = [{
            "id": txid,
            "label": f"TX\\n{txid[:8]}...",
            "shape": "box",
            "color": "#f59e0b",
            "font": {"color": "#000", "face": "monospace", "size": 12}
        }]

        edges = []
        for idx, w in enumerate(connected_wallets):
            color = "#ef4444" if w == primary_w else "#38bdf8"
            nodes.append({
                "id": w,
                "label": f"Wallet\\n{w[:8]}...",
                "shape": "ellipse",
                "color": color,
                "font": {"color": "#fff", "face": "monospace", "size": 11}
            })
            if idx % 2 == 0:
                edges.append({"from": w, "to": txid, "label": "INPUT_TO", "color": {"color": "#64748b"}})
            else:
                edges.append({"from": txid, "to": w, "label": "OUTPUT_TO", "color": {"color": "#10b981"}})

        for ip in connected_ips:
            nodes.append({
                "id": ip,
                "label": f"IP\\n{ip}",
                "shape": "diamond",
                "color": "#a855f7",
                "font": {"color": "#fff", "face": "monospace", "size": 11}
            })
            edges.append({"from": txid, "to": ip, "label": "BROADCAST", "color": {"color": "#c084fc"}})

        vis_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
          <style>
            body {{ margin:0; background:#0b0f19; color:#fff; font-family:monospace; }}
            #network {{ width: 100%; height: 500px; border: 1px solid #243147; border-radius: 8px; }}
          </style>
        </head>
        <body>
          <div id="network"></div>
          <script type="text/javascript">
            var nodes = new vis.DataSet({json.dumps(nodes)});
            var edges = new vis.DataSet({json.dumps(edges)});
            var container = document.getElementById('network');
            var data = {{ nodes: nodes, edges: edges }};
            var options = {{
              nodes: {{ borderWidth: 1 }},
              edges: {{ arrows: 'to', font: {{ size: 9, align: 'middle' }} }},
              physics: {{ stabilization: true, barnesHut: {{ springLength: 120 }} }}
            }};
            var network = new vis.Network(container, data, options);
          </script>
        </body>
        </html>
        """
        components.html(vis_html, height=520)
        st.caption("Visual Legend: 🟧 Transaction | 🔴 Suspect Target Wallet | 🔷 Counterparty Wallets | 🟣 Relay IP Node")


# ===================================================================================
# TAB 4: SUSPECT WALLET INVESTIGATION (Clear Explanations & 1-Click Profiler)
# ===================================================================================
with tab_wallets:
    st.markdown("### 🔍 Suspect Wallet Investigation & Taint Profiler")
    st.markdown("Search or select suspect public Bitcoin addresses detected in the transaction traffic to profile graph centrality, taint exposure score, and co-spending clusters.")

    # Educational Disclaimer Box
    st.markdown("""
        <div class="callout">
            <strong style="color:#f59e0b;">ℹ️ ABOUT WALLET INVESTIGATION:</strong>
            <div style="font-size:12px; color:#cbd5e1; margin-top:4px; line-height:1.5;">
                In Bitcoin forensic surveillance (like Chainalysis/Elliptic), investigators do <strong>not</strong> connect a personal Web3 wallet. 
                Instead, you inspect suspect public wallet addresses from the traffic feed. Choose any flagged wallet below or paste a target address to inspect its criminal taint score!
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 1-Click Dropdown of Top Suspicious Wallets
    top_wallets_list = df_risk["wallet_address"].head(40).tolist() if not df_risk.empty else []

    col_sel, col_manual = st.columns([1, 1])
    with col_sel:
        preset_choice = st.selectbox(
            "⚡ Select Suspect Wallet to Profile:",
            top_wallets_list
        )
    with col_manual:
        manual_address = st.text_input("Or Enter Custom Bitcoin Address:", placeholder="Paste any Bitcoin address (1..., 3..., bc1q...)...")

    # Target Address Selection
    target_address = manual_address.strip() if manual_address.strip() else preset_choice

    if target_address:
        matched = df_risk[df_risk["wallet_address"] == target_address]
        if not matched.empty:
            row = matched.iloc[0]
            st.markdown(f"#### 🎯 Forensic Profile for Suspect Address: `{target_address}`")

            w1, w2, w3, w4 = st.columns(4)
            with w1:
                st.metric("Personalized PageRank Taint Score", f"{row['risk_score']:.4f}")
            with w2:
                tier = row['risk_tier']
                badge_class = "badge-crit" if tier == "CRITICAL" else ("badge-high" if tier == "HIGH" else "badge-med")
                st.markdown(f"**Risk Classification:**<br/><span class='badge {badge_class}'>{tier}</span>", unsafe_allow_html=True)
            with w3:
                st.metric("Heuristic Entity Group", row.get('entity_group', 'UNKNOWN'))
            with w4:
                st.metric("Graph Connections (In / Out)", f"{row.get('in_degree', 0)} / {row.get('out_degree', 0)}")

            # Connected transactions from database
            conn = sqlite3.connect("bitcoin_traffic.db")
            df_wallet_txs = pd.read_sql_query("""
                SELECT t.txid as "TXID", t.datetime_utc as "Timestamp", t.src_ip as "Source IP",
                       t.geo_country as "Country", t.fee_btc as "Fee (BTC)",
                       round(t.volume_usd, 2) as "Volume ($)", t.pattern_label as "Pattern"
                FROM transactions t
                WHERE t.txid IN (SELECT txid FROM tx_inputs WHERE address = ?)
                   OR t.txid IN (SELECT txid FROM tx_outputs WHERE address = ?)
                ORDER BY t.timestamp DESC
                LIMIT 10
            """, conn, params=(target_address, target_address))

            # Co-clustered wallets in the same entity group
            eg_id = row.get('entity_group', '')
            df_co_wallets = pd.read_sql_query("""
                SELECT wallet_address as "Co-Clustered Wallet Address"
                FROM wallet_entities
                WHERE entity_group_id = ? AND wallet_address != ?
                LIMIT 10
            """, conn, params=(eg_id, target_address))
            conn.close()

            c_tx_hist, c_cluster = st.columns([2, 1])
            with c_tx_hist:
                st.markdown("##### 📜 Transaction History for this Suspect Wallet:")
                if not df_wallet_txs.empty:
                    st.dataframe(df_wallet_txs, use_container_width=True, hide_index=True)
                else:
                    st.info("No direct transactions found in current window.")

            with c_cluster:
                st.markdown(f"##### 👥 Entity Cluster Members ({eg_id}):")
                if not df_co_wallets.empty:
                    st.dataframe(df_co_wallets, use_container_width=True, hide_index=True)
                else:
                    st.caption("No additional co-spending wallets merged in this entity.")

            # Tied alerts
            tied_alerts = [a for a in alerts_data if a.get("primary_wallet") == target_address or target_address in a.get("evidence_links", {}).get("connected_wallets", [])]
            if tied_alerts:
                st.markdown(f"##### ⚠️ Tied to {len(tied_alerts)} Active Intelligence Alerts:")
                for a in tied_alerts:
                    st.warning(f"**{a['alert_id']} ({a['risk_tier']})**: {a['explanation']}")
        else:
            st.error(f"Address `{target_address}` not found in indexed graph database.")

    st.markdown("---")
    st.markdown("#### 🏆 Top 25 Highest-Risk Tainted Wallets (Ranked by PageRank Taint Score)")
    if not df_risk.empty:
        st.dataframe(df_risk.head(25), use_container_width=True, hide_index=True)


# ===================================================================================
# TAB 5: SMART INGESTION & DATASET ENGINE
# ===================================================================================
with tab_ingest:
    st.markdown("### 📥 Smart Ingestion & Dataset Engine")
    st.markdown("Upload custom transaction files or drop Kaggle 1-minute price CSVs to synthesize transactions.")

    up_col1, up_col2 = st.columns([1, 1])

    with up_col1:
        st.markdown("#### 📁 File Upload")
        uploaded_file = st.file_uploader("Upload CSV, JSON, or XML file", type=["csv", "json", "xml"])
        if uploaded_file:
            save_name = f"uploaded_{uploaded_file.name}"
            with open(save_name, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.success(f"File uploaded: `{uploaded_file.name}` ({len(uploaded_file.getbuffer())/1024:.1f} KB)")

            # Check if Kaggle price CSV
            is_price = False
            if uploaded_file.name.endswith(".csv"):
                try:
                    df_check = pd.read_csv(save_name, nrows=5)
                    cols = [c.lower() for c in df_check.columns]
                    if any(c in cols for c in ['open', 'close', 'price']) and not any(c in cols for c in ['txid', 'input_addresses']):
                        is_price = True
                except Exception:
                    pass

            if is_price:
                st.info("💡 **Detected Kaggle 1-Minute BTC/USD Price File.**")
                if st.button("🚀 Synthesize Transactions from This Price File", type="primary"):
                    with st.spinner("Synthesizing transactions from uploaded prices..."):
                        auto_generate_pipeline(count=8000, price_csv=save_name)
                    st.success("Transactions successfully generated and ingested!")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.info("💡 **Detected Bitcoin Transaction Feed.**")
                if st.button("🚀 Ingest Directly into SQLite Database", type="primary"):
                    with st.spinner("Ingesting into database..."):
                        import ingest
                        p = ingest.IngestionPipeline(db_path="bitcoin_traffic.db")
                        p.process_file(save_name)
                        p.finish()
                    st.success(f"Ingested {p.stats['records_normalized']:,} transactions! Skipped: {p.stats['records_skipped']:,}")
                    st.cache_data.clear()
                    st.rerun()

    with up_col2:
        st.markdown("#### ⚡ 1-Click Auto-Dataset Generator")
        st.write("Generate a fresh 8,000 transaction dataset with peeling chains, mixing pools, and Sybil clusters:")
        if st.button("🎲 Auto-Generate & Ingest 8,000 Transactions Now", use_container_width=True, type="primary"):
            with st.spinner("Executing full pipeline..."):
                auto_generate_pipeline(count=8000)
            st.success("8,000 Transactions Generated and Ingested!")
            st.cache_data.clear()
            st.rerun()


# ===================================================================================
# TAB 6: PIPELINE AUTOMATION HUB
# ===================================================================================
with tab_pipeline:
    st.markdown("### ⚡ Pipeline Automation Hub")
    st.markdown("Trigger or rebuild any individual module or execute the full workflow sequentially.")

    p1, p2 = st.columns(2)
    with p1:
        st.markdown("#### 🔄 Full End-to-End Run")
        if st.button("▶️ Execute Full Pipeline (Steps 1-5)", type="primary", use_container_width=True):
            with st.status("Executing Full ChainSentinel Pipeline...", expanded=True) as status_box:
                auto_generate_pipeline(count=8000)
                status_box.update(label="Pipeline Complete!", state="complete")
            st.success("All models and alerts refreshed!")
            st.cache_data.clear()
            st.rerun()

    with p2:
        st.markdown("#### 🧩 Step-by-Step Re-runs")
        if st.button("Rebuild Graph MultiDiGraph (Step 3)", use_container_width=True):
            import graph_builder
            b = graph_builder.ChainSentinelGraphBuilder()
            b.build_graph()
            b.save()
            st.success("Graph Rebuilt!")
            st.cache_data.clear()
        if st.button("Re-run AI/ML Models & Alerts (Steps 4-5)", use_container_width=True):
            import alert_generator
            g = alert_generator.AlertGenerator()
            g.generate_alerts(top_n=150)
            g.export()
            st.success("Alerts Re-generated!")
            st.cache_data.clear()
            st.rerun()


# ===================================================================================
# TAB 7: TECHNICAL WRITE-UP (SIH Submission Documentation Viewer)
# ===================================================================================
with tab_writeup:
    st.markdown("### 📑 ChainSentinel Technical Architecture & Methodology Write-up")
    st.markdown("Submission document detailing problem understanding, system architecture, mathematical models, XAI methodology, and empirical metrics.")

    if os.path.exists("TECHNICAL_WRITEUP.md"):
        with open("TECHNICAL_WRITEUP.md", "r", encoding="utf-8") as f:
            writeup_content = f.read()
        st.markdown(writeup_content)
    else:
        st.info("TECHNICAL_WRITEUP.md not found.")
