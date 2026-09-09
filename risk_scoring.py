#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
STEP 4 (MODULE D) — RISK SCORING (Personalized PageRank / Taint Propagation)
===================================================================================
1. Defines initial tainted seed wallets:
   - Ground Truth labeled suspicious wallets (is_suspicious=1)
   - Origin wallets of detected Peeling Chains & Mixing pools
2. Implements Personalized PageRank (Random Walk with Restart) over the
   directed multigraph topology to compute multi-hop risk dissipation.
3. Normalizes and ranks all wallets by risk exposure score [0.0 - 1.0].
===================================================================================
"""

import os
import sys
import pickle
import sqlite3
import argparse
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Set, Tuple, Any, Optional


class RiskScorer:
    """Computes graph-wide taint and risk propagation using Personalized PageRank."""

    def __init__(self, db_path: str = "bitcoin_traffic.db", graph_path: str = "graph.gpickle",
                 ground_truth_path: str = "ground_truth.csv", alpha: float = 0.85):
        self.db_path = db_path
        self.graph_path = graph_path
        self.ground_truth_path = ground_truth_path
        self.alpha = alpha
        self.graph: Optional[nx.MultiDiGraph] = None
        self.seed_wallets: Set[str] = set()
        self.df_risk: Optional[pd.DataFrame] = None

    def load_graph_and_seeds(self):
        """Loads graph and identifies ground-truth or heuristic seed wallets."""
        if not os.path.exists(self.graph_path):
            raise FileNotFoundError(f"Graph file {self.graph_path} not found.")

        print(f"[*] Loading graph from: {self.graph_path}...")
        with open(self.graph_path, "rb") as f:
            self.graph = pickle.load(f)

        # 1. Check ground truth file for seeds
        if os.path.exists(self.ground_truth_path):
            df_gt = pd.read_csv(self.ground_truth_path)
            if "is_suspicious" in df_gt.columns and "wallet_id" in df_gt.columns:
                suspicious_seeds = set(df_gt[df_gt["is_suspicious"] == 1]["wallet_id"])
                self.seed_wallets.update(suspicious_seeds)
                print(f"[+] Loaded {len(suspicious_seeds):,} suspicious seed wallets from ground_truth.csv.")

        # 2. Also incorporate anomaly/pattern labels from graph if ground truth is empty
        if len(self.seed_wallets) < 10:
            for txid, d in self.graph.nodes(data=True):
                if d.get("node_type") == "transaction" and d.get("pattern_label") not in ("NORMAL", None):
                    for u, _, _, in_d in self.graph.in_edges(txid, data=True, keys=True):
                        if in_d.get("edge_type") == "INPUT_TO":
                            self.seed_wallets.add(u)
            print(f"[+] Total seed wallets compiled: {len(self.seed_wallets):,}")

    def compute_risk_propagation(self) -> pd.DataFrame:
        """Runs Personalized PageRank on the graph topology."""
        if self.graph is None:
            self.load_graph_and_seeds()

        all_wallets = [
            n for n, d in self.graph.nodes(data=True)
            if d.get("node_type") == "wallet"
        ]
        wallet_set = set(all_wallets)

        # Intersect seeds with wallets present in graph
        valid_seeds = [w for w in self.seed_wallets if w in wallet_set]
        if not valid_seeds:
            print("[!] Warning: No matching seed wallets found in graph. Using top in-degree nodes as surrogate.")
            valid_seeds = sorted(all_wallets, key=lambda w: self.graph.in_degree(w), reverse=True)[:50]

        print(f"[*] Executing Personalized PageRank with {len(valid_seeds):,} tainted seed nodes (alpha={self.alpha})...")

        # Construct personalization dictionary
        seed_weight = 1.0 / len(valid_seeds)
        personalization = {node: 0.0 for node in self.graph.nodes()}
        for s in valid_seeds:
            personalization[s] = seed_weight

        # Run PageRank (PPR)
        # Note: NetworkX handles directed multigraphs or we can project to weighted DiGraph
        try:
            # MultiDiGraph pagerank
            raw_scores = nx.pagerank(
                self.graph,
                alpha=self.alpha,
                personalization=personalization,
                max_iter=100,
                tol=1e-6
            )
        except Exception as e:
            print(f"[!] Falling back to DiGraph projection for PageRank: {e}")
            simple_dg = nx.DiGraph(self.graph)
            raw_scores = nx.pagerank(
                simple_dg,
                alpha=self.alpha,
                personalization=personalization,
                max_iter=100,
                tol=1e-6
            )

        # Filter only wallet nodes and normalize scores to [0.0 - 1.0]
        wallet_scores = {w: raw_scores.get(w, 0.0) for w in all_wallets}
        max_val = max(wallet_scores.values()) if wallet_scores else 1.0
        min_val = min(wallet_scores.values()) if wallet_scores else 0.0
        denominator = (max_val - min_val) if max_val > min_val else 1.0

        records = []
        for w in all_wallets:
            raw_s = wallet_scores[w]
            # Use non-linear scaling (square root) to widen separation among low-to-mid risk wallets
            normalized_score = float(np.sqrt((raw_s - min_val) / denominator))
            normalized_score = min(1.0, max(0.0, normalized_score))

            is_seed = 1 if w in valid_seeds else 0
            if is_seed:
                normalized_score = max(0.92, normalized_score)  # Direct seeds maintain near-max risk

            # Categorize Risk Tier
            if normalized_score >= 0.75:
                tier = "CRITICAL"
            elif normalized_score >= 0.45:
                tier = "HIGH"
            elif normalized_score >= 0.20:
                tier = "MEDIUM"
            else:
                tier = "LOW"

            records.append({
                "wallet_address": w,
                "risk_score": round(normalized_score, 4),
                "risk_tier": tier,
                "is_taint_seed": is_seed,
                "entity_group": self.graph.nodes[w].get("entity_group", "UNKNOWN"),
                "in_degree": self.graph.in_degree(w),
                "out_degree": self.graph.out_degree(w)
            })

        df_out = pd.DataFrame(records).sort_values("risk_score", ascending=False)
        self.df_risk = df_out

        print(f"[+] Risk Scoring complete. Processed {len(df_out):,} wallets.")
        print(f"    - Critical Risk Wallets (>= 0.75) : {(df_out['risk_score'] >= 0.75).sum():,}")
        print(f"    - High Risk Wallets (0.45 - 0.75)  : {((df_out['risk_score'] >= 0.45) & (df_out['risk_score'] < 0.75)).sum():,}")
        print(f"    - Medium Risk Wallets (0.20 - 0.45): {((df_out['risk_score'] >= 0.20) & (df_out['risk_score'] < 0.45)).sum():,}")
        print(f"    - Low Risk Wallets (< 0.20)        : {(df_out['risk_score'] < 0.20).sum():,}")

        return df_out

    def save_results(self, out_csv: str = "wallet_risk_scores.csv"):
        """Exports risk scoring results to CSV."""
        if self.df_risk is not None:
            self.df_risk.to_csv(out_csv, index=False)
            print(f"[+] Saved wallet risk scores to: {out_csv}")


def run_risk_scoring(db_path: str = "bitcoin_traffic.db",
                     graph_path: str = "graph.gpickle",
                     ground_truth_path: str = "ground_truth.csv",
                     out_csv: str = "wallet_risk_scores.csv") -> pd.DataFrame:
    """Convenience functional API for Step 5 integration."""
    scorer = RiskScorer(db_path=db_path, graph_path=graph_path, ground_truth_path=ground_truth_path)
    df = scorer.compute_risk_propagation()
    scorer.save_results(out_csv)
    return df


def main():
    parser = argparse.ArgumentParser(description="ChainSentinel // Step 4 (Module D): Graph Risk Scoring")
    parser.add_argument("--db", type=str, default="bitcoin_traffic.db", help="Path to SQLite database")
    parser.add_argument("--graph", type=str, default="graph.gpickle", help="Path to graph.gpickle")
    parser.add_argument("--seeds", type=str, default="ground_truth.csv", help="Path to ground truth seed CSV")
    parser.add_argument("--out", type=str, default="wallet_risk_scores.csv", help="Output CSV path")
    args = parser.parse_args()

    run_risk_scoring(db_path=args.db, graph_path=args.graph, ground_truth_path=args.seeds, out_csv=args.out)


if __name__ == "__main__":
    main()
