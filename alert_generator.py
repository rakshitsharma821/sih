#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
STEP 5 — ALERT GENERATION & FORENSIC EXPLAINABILITY (SHAP + Dynamic Evidence Trails)
===================================================================================
1. Ensembles signals from:
   - Module A: Entity Clustering (wallet_clusters.csv)
   - Module B: Transaction Anomaly Detection (transaction_anomalies.csv)
   - Module C: Peeling-Chain & CoinJoin Detection (detected_patterns.csv)
   - Module D: Graph Risk Scoring / Taint Propagation (wallet_risk_scores.csv)
2. Weighted Confidence Formulation:
   confidence = w1*anomaly_score + w2*risk_score + w3*(pattern_detected) + w4*(cluster_factor)
3. Explainability Layer:
   - Feature attribution / SHAP ranking for transaction behavior.
   - Dynamic natural-language forensic explanation strings detailing hop counts,
     source IPs, ASNs, fee discrepancies, and co-clustering.
4. Exports:
   - alerts.csv
   - alerts.json (structured with 'evidence_links' for link-analysis drilldown)
===================================================================================
"""

import os
import sys
import json
import math
import sqlite3
import pickle
import argparse
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

# Import step 4 modules if called programmatically
import entity_clustering
import anomaly_detection
import pattern_detection
import risk_scoring
from explainability import ShapForensicExplainer


class AlertGenerator:
    """Combines all ML signals and generates explainable intelligence alerts."""

    def __init__(self,
                 db_path: str = "bitcoin_traffic.db",
                 graph_path: str = "graph.gpickle",
                 w1: float = 0.35,  # Anomaly score weight
                 w2: float = 0.30,  # Risk propagation weight
                 w3: float = 0.25,  # Structural pattern weight
                 w4: float = 0.10): # Entity cluster size weight
        self.db_path = db_path
        self.graph_path = graph_path
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4

        self.df_clusters = None
        self.df_anomalies = None
        self.df_patterns = None
        self.df_risk = None
        self.alerts: List[Dict[str, Any]] = []

    def load_or_run_modules(self):
        """Loads existing Step 4 CSVs or executes the modules if not yet generated."""
        print("\n[*] Assembling intelligence signals from Step 4 modules...")

        # 1. Module A: Entity Clustering
        if os.path.exists("wallet_clusters.csv"):
            self.df_clusters = pd.read_csv("wallet_clusters.csv")
        else:
            self.df_clusters = entity_clustering.run_entity_clustering(self.graph_path, self.db_path)

        # 2. Module B: Anomaly Detection
        if os.path.exists("transaction_anomalies.csv"):
            self.df_anomalies = pd.read_csv("transaction_anomalies.csv")
        else:
            self.df_anomalies = anomaly_detection.run_anomaly_detection(self.db_path)

        # 3. Module C: Pattern Detection
        if os.path.exists("detected_patterns.csv"):
            self.df_patterns = pd.read_csv("detected_patterns.csv")
        else:
            self.df_patterns = pattern_detection.run_pattern_detection(self.db_path, self.graph_path)

        # 4. Module D: Risk Scoring
        if os.path.exists("wallet_risk_scores.csv"):
            self.df_risk = pd.read_csv("wallet_risk_scores.csv")
        else:
            self.df_risk = risk_scoring.run_risk_scoring(self.db_path, self.graph_path)

        print("[+] All Step 4 analytical feeds loaded successfully.")

    def generate_alerts(self, top_n: int = 150) -> List[Dict[str, Any]]:
        """Synthesizes signals, calculates confidence, and creates dynamic explanations."""
        self.load_or_run_modules()

        print(f"[*] Correlating forensic signals across transactions and wallets...")
        conn = sqlite3.connect(self.db_path)
        df_inputs = pd.read_sql_query("SELECT txid, address, amount_btc FROM tx_inputs", conn)
        df_outputs = pd.read_sql_query("SELECT txid, address, amount_btc FROM tx_outputs", conn)
        conn.close()

        # Build fast lookup indexes
        risk_map = dict(zip(self.df_risk["wallet_address"], self.df_risk["risk_score"]))
        cluster_map = dict(zip(self.df_clusters["wallet_address"], self.df_clusters["final_cluster_id"]))
        cluster_sizes = self.df_clusters["final_cluster_id"].value_counts().to_dict()

        tx_inputs_map = df_inputs.groupby("txid")["address"].apply(list).to_dict()
        tx_outputs_map = df_outputs.groupby("txid")["address"].apply(list).to_dict()

        pattern_map = self.df_patterns.set_index("txid").to_dict("index")
        anomaly_map = self.df_anomalies.set_index("txid").to_dict("index")

        mean_network_fee = self.df_anomalies["fee_btc"].mean()
        mean_network_vol = self.df_anomalies["volume_usd"].mean()

        compiled_alerts = []

        # Iterate over all transactions and evaluate alert triggers
        for txid, anom_row in anomaly_map.items():
            anom_score = float(anom_row.get("anomaly_score", 0.0))
            pat_row = pattern_map.get(txid, {})
            pat_label = pat_row.get("detected_pattern", "NONE")
            pat_flag = 1.0 if pat_label != "NONE" else 0.0

            # Get participating wallets
            in_addrs = tx_inputs_map.get(txid, [])
            out_addrs = tx_outputs_map.get(txid, [])
            all_tx_wallets = in_addrs + out_addrs

            # Wallet risk aggregation (max risk among participants)
            if all_tx_wallets:
                max_risk = max(risk_map.get(w, 0.0) for w in all_tx_wallets)
                primary_wallet = in_addrs[0] if in_addrs else all_tx_wallets[0]
            else:
                max_risk = 0.0
                primary_wallet = "UNKNOWN"

            # Cluster size factor
            c_id = cluster_map.get(primary_wallet, "UNKNOWN")
            c_size = cluster_sizes.get(c_id, 1)
            cluster_factor = min(1.0, math.log1p(c_size) / math.log1p(15))

            # Calculate Weighted Confidence Score
            confidence = (
                self.w1 * anom_score +
                self.w2 * max_risk +
                self.w3 * pat_flag +
                self.w4 * cluster_factor
            )
            confidence = float(np.clip(confidence, 0.0, 0.99))

            # Filter for notable incidents (confidence threshold >= 0.40 or pattern detected)
            if confidence >= 0.40 or pat_flag == 1.0 or anom_score >= 0.70:
                flags = []
                explanations = []

                # Dynamic Explanation Generator
                if pat_label == "PEELING_CHAIN":
                    chain_hops = pat_row.get("chain_hops", 4)
                    flags.append("PEELING_CHAIN")
                    explanations.append(
                        f"Part of a {chain_hops}-hop peeling chain layering structure peeling incremental funds to change hops."
                    )
                elif pat_label == "COINJOIN_MIXING":
                    mix_pool = pat_row.get("mix_pool_size", 3)
                    flags.append("COINJOIN_MIXING")
                    explanations.append(
                        f"CoinJoin privacy mixer signature: {len(in_addrs)} inputs unified into {len(out_addrs)} outputs with {mix_pool} equal denominations."
                    )

                if anom_score >= 0.65:
                    flags.append("STATISTICAL_ANOMALY")
                    fee_btc = float(anom_row.get("fee_btc", 0.0))
                    vol_usd = float(anom_row.get("volume_usd", 0.0))
                    if fee_btc > (mean_network_fee * 2.5):
                        pct_above = int(((fee_btc - mean_network_fee) / mean_network_fee) * 100)
                        explanations.append(f"Transaction fee ({fee_btc:.6f} BTC) is {pct_above}% above the network baseline.")
                    if vol_usd > (mean_network_vol * 4.0):
                        explanations.append(f"Abnormally high transfer volume of ${vol_usd:,.2f} USD.")

                if max_risk >= 0.60:
                    flags.append("TAINTED_PROPAGATION")
                    explanations.append(f"Personalized PageRank detected close topological affinity (risk: {max_risk:.2f}) to known illicit seed entities.")

                if c_size >= 3:
                    flags.append("COMMON_INPUT_CLUSTER")
                    explanations.append(f"Primary wallet is co-clustered with {c_size} addresses within entity {c_id}.")

                # IP Colocation details
                src_ip = anom_row.get("src_ip", "0.0.0.0")
                country = anom_row.get("geo_country", "UNKNOWN")
                asn = anom_row.get("asn", "UNKNOWN")
                if src_ip != "0.0.0.0":
                    explanations.append(f"Broadcast from source node {src_ip} ({country}, {asn}).")

                # Format complete narrative
                if not flags:
                    flags.append("ELEVATED_RISK")
                if not explanations:
                    explanations.append("Elevated multivariate statistical divergence across graph structural embeddings.")

                narrative_body = " ".join([f"({i+1}) {exp}" for i, exp in enumerate(explanations)])
                full_explanation = f"Flagged with {int(confidence * 100)}% confidence: {narrative_body}"

                # Construct Evidence Links for Visual Drilldown in Step 6 Dashboard
                evidence_links = {
                    "txid": txid,
                    "primary_wallet": primary_wallet,
                    "connected_wallets": all_tx_wallets[:10],
                    "connected_ips": [src_ip] if src_ip != "0.0.0.0" else [],
                    "entity_group": c_id,
                    "volume_usd": float(anom_row.get("volume_usd", 0.0)),
                    "fee_btc": float(anom_row.get("fee_btc", 0.0)),
                    "datetime_utc": anom_row.get("datetime_utc", "")
                }

                compiled_alerts.append({
                    "alert_id": f"ALT_{len(compiled_alerts)+1:05d}",
                    "txid": txid,
                    "primary_wallet": primary_wallet,
                    "confidence_score": round(confidence, 3),
                    "risk_tier": "CRITICAL" if confidence >= 0.75 else ("HIGH" if confidence >= 0.55 else "MEDIUM"),
                    "flags": flags,
                    "primary_flag": flags[0],
                    "explanation": full_explanation,
                    "evidence_links": evidence_links,
                    "geo_country": country,
                    "asn": asn,
                    "datetime_utc": anom_row.get("datetime_utc", "")
                })

        # Sort descending by confidence score
        compiled_alerts.sort(key=lambda x: x["confidence_score"], reverse=True)
        top_alerts = compiled_alerts[:top_n]

        # Compute genuine SHAP feature attributions for top alerts
        print(f"[*] Generating SHAP feature attributions for top {len(top_alerts)} alerts...")
        try:
            explainer = ShapForensicExplainer()
            top_txids = [a["txid"] for a in top_alerts]
            df_alert_txs = self.df_anomalies[self.df_anomalies["txid"].isin(top_txids)]
            shap_exps = explainer.explain_transactions(df_alert_txs, top_k=3)

            for a in top_alerts:
                tx_shap = shap_exps.get(a["txid"], [])
                a["shap_drivers"] = tx_shap
                a["evidence_links"]["shap_drivers"] = tx_shap
                if tx_shap:
                    drivers_str = ", ".join([f"{d['label']} ({d['shap_value']:+.3f})" for d in tx_shap])
                    a["explanation"] += f" | Key Anomaly Drivers (SHAP TreeExplainer): {drivers_str}."
            print(f"[+] Successfully computed SHAP explanations for {len(shap_exps)} alerted transactions.")
        except Exception as e:
            print(f"[!] Warning: SHAP computation encountered an issue ({e}); alerts retained without SHAP.")

        self.alerts = top_alerts
        print(f"\n[+] Generated {len(self.alerts):,} high-priority intelligence alerts (Top {top_n}).")
        return self.alerts

    def export(self, out_csv: str = "alerts.csv", out_json: str = "alerts.json"):
        """Exports alerts to CSV and JSON formats."""
        if not self.alerts:
            self.generate_alerts()

        print(f"[*] Exporting alerts to disk...")

        # 1. JSON Export (with nested evidence links and SHAP explanations)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(self.alerts, f, indent=2)
        print(f"    [1/2] Exported JSON: {out_json} ({len(self.alerts)} structured alerts)")

        # 2. CSV Export
        csv_rows = []
        for a in self.alerts:
            shap_str = "; ".join([f"{d['label']} ({d['shap_value']:+.3f})" for d in a.get("shap_drivers", [])])
            csv_rows.append({
                "alert_id": a["alert_id"],
                "txid": a["txid"],
                "primary_wallet": a["primary_wallet"],
                "confidence_score": a["confidence_score"],
                "risk_tier": a["risk_tier"],
                "flags": ";".join(a["flags"]),
                "geo_country": a["geo_country"],
                "asn": a["asn"],
                "datetime_utc": a["datetime_utc"],
                "explanation": a["explanation"],
                "shap_drivers": shap_str,
                "evidence_json": json.dumps(a["evidence_links"])
            })

        df_csv = pd.DataFrame(csv_rows)
        df_csv.to_csv(out_csv, index=False)
        print(f"    [2/2] Exported CSV: {out_csv}")
        print("\n[OK] Alert Generation & Forensic Explainability module completed successfully!")


def main():
    parser = argparse.ArgumentParser(description="ChainSentinel // Step 5: Alert Generation & Explainability")
    parser.add_argument("--db", type=str, default="bitcoin_traffic.db", help="Path to SQLite database")
    parser.add_argument("--graph", type=str, default="graph.gpickle", help="Path to graph.gpickle")
    parser.add_argument("--out", type=str, default="alerts.json", help="Path to output alerts JSON")
    parser.add_argument("--out-csv", type=str, default="alerts.csv", help="Path to output alerts CSV")
    parser.add_argument("--top-n", type=int, default=150, help="Number of top alerts to retain (default: 150)")
    args = parser.parse_args()

    generator = AlertGenerator(db_path=args.db, graph_path=args.graph)
    generator.generate_alerts(top_n=args.top_n)
    generator.export(out_csv=args.out_csv, out_json=args.out)


if __name__ == "__main__":
    main()
