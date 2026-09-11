#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
STEP 4 (MODULE C) — PEELING-CHAIN & COINJOIN/MIXING DETECTION
===================================================================================
Algorithmic & Graph Traversal Detectors:
1. Peeling-Chain Detector:
   - Identifies structural layering/smurfing chains (hops >= 4).
   - Traces 1-in-2-out topologies where a small payment is peeled off and
     the remainder change output is successively forwarded to subsequent hops.
2. CoinJoin / Mixing Detector:
   - Identifies multi-party privacy mixing transactions (inputs >= 3, outputs >= 3).
   - Detects equal/near-equal output denominations forming an anonymity set.
3. Outputs a unified forensics report linking TXIDs, pattern classifications,
   and dynamic evidence strings.
===================================================================================
"""

import os
import sys
import json
import sqlite3
import pickle
import argparse
import numpy as np
import pandas as pd
import networkx as nx
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional


class PatternDetector:
    """Detects structural Peeling Chains and CoinJoin / Mixing transactions."""

    def __init__(self, db_path: str = "bitcoin_traffic.db", graph_path: Optional[str] = "graph.gpickle"):
        self.db_path = db_path
        self.graph_path = graph_path
        self.df_tx = None
        self.df_inputs = None
        self.df_outputs = None
        self.detected_records: List[Dict[str, Any]] = []

    def load_data(self):
        """Loads transaction, input, and output tables from SQLite."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        print(f"[*] Loading data from SQLite database: {self.db_path}...")
        conn = sqlite3.connect(self.db_path)
        self.df_tx = pd.read_sql_query("""
            SELECT txid, timestamp, datetime_utc, src_ip, dst_ip, src_port, dst_port,
                   geo_country, asn, script_type, fee_btc, btc_price_usd, volume_usd, pattern_label
            FROM transactions
            ORDER BY timestamp ASC
        """, conn)

        self.df_inputs = pd.read_sql_query("SELECT txid, address, amount_btc FROM tx_inputs", conn)
        self.df_outputs = pd.read_sql_query("SELECT txid, address, amount_btc FROM tx_outputs", conn)
        conn.close()
        print(f"[+] Loaded {len(self.df_tx):,} transactions, {len(self.df_inputs):,} inputs, {len(self.df_outputs):,} outputs.")

    def detect_coinjoin_mixing(self) -> List[Dict[str, Any]]:
        """
        Detects CoinJoin / Wasabi / Whirlpool transactions:
        - input_count >= 3
        - output_count >= 3
        - Multiple outputs (>= 3) share identical or near-identical BTC values (anonymity set).
        """
        print("[*] Scanning for CoinJoin / Privacy Mixing patterns...")
        results = []

        # Group outputs by txid
        tx_outputs = defaultdict(list)
        for _, row in self.df_outputs.iterrows():
            tx_outputs[row['txid']].append(round(float(row['amount_btc']), 5))

        # Group inputs by txid
        tx_input_counts = self.df_inputs.groupby('txid')['address'].count().to_dict()

        for txid, out_amts in tx_outputs.items():
            in_count = tx_input_counts.get(txid, 0)
            out_count = len(out_amts)

            if in_count >= 3 and out_count >= 3:
                # Count frequency of each output denomination
                denom_counts = defaultdict(int)
                for amt in out_amts:
                    denom_counts[amt] += 1

                # Find dominant equal denomination
                max_equal_count = 0
                equal_denom = 0.0
                for amt, count in denom_counts.items():
                    if count > max_equal_count:
                        max_equal_count = count
                        equal_denom = amt

                # CoinJoin criteria: At least 3 equal denomination outputs
                if max_equal_count >= 3:
                    evidence = (
                        f"CoinJoin/Mixing detected: {in_count} inputs mixed into {out_count} outputs. "
                        f"Anonymity set of {max_equal_count} participants with equal denomination of {equal_denom} BTC."
                    )
                    results.append({
                        "txid": txid,
                        "detected_pattern": "COINJOIN_MIXING",
                        "confidence_score": 0.95,
                        "chain_hops": 1,
                        "mix_pool_size": max_equal_count,
                        "evidence_details": evidence
                    })

        print(f"[+] Found {len(results):,} CoinJoin / Mixing transactions.")
        return results

    def detect_peeling_chains(self, min_hops: int = 4) -> List[Dict[str, Any]]:
        """
        Detects Peeling Chains:
        Traverses forwarding graph where an output address from one tx becomes the single
        input of a subsequent tx, with 1 small peel output and 1 large change forward.
        """
        print(f"[*] Tracing Peeling Chains (minimum depth: {min_hops} hops)...")
        results = []

        # Map wallet -> txids where it is spent as input
        input_spenders = defaultdict(list)
        for _, row in self.df_inputs.iterrows():
            input_spenders[row['address']].append(row['txid'])

        # Map txid -> list of outputs (address, amount)
        tx_to_outs = defaultdict(list)
        for _, row in self.df_outputs.iterrows():
            tx_to_outs[row['txid']].append((row['address'], float(row['amount_btc'])))

        # Map txid -> list of inputs (address, amount)
        tx_to_ins = defaultdict(list)
        for _, row in self.df_inputs.iterrows():
            tx_to_ins[row['txid']].append((row['address'], float(row['amount_btc'])))

        # Find potential chain candidates: transactions with 1 input and 2 outputs
        visited_txs: Set[str] = set()
        chains: List[List[str]] = []

        for txid, outs in tx_to_outs.items():
            if txid in visited_txs:
                continue

            ins = tx_to_ins.get(txid, [])
            if len(ins) == 1 and len(outs) == 2:
                # Potential start or middle of a peeling chain
                chain = [txid]
                curr_tx = txid

                while True:
                    curr_outs = tx_to_outs.get(curr_tx, [])
                    if len(curr_outs) != 2:
                        break

                    # Identify change output (usually the significantly larger output)
                    out1, out2 = curr_outs[0], curr_outs[1]
                    larger_out = out1 if out1[1] >= out2[1] else out2
                    change_addr = larger_out[0]

                    # Check if this change address is spent in a subsequent transaction
                    next_txs = input_spenders.get(change_addr, [])
                    if len(next_txs) == 1:
                        next_tx = next_txs[0]
                        if next_tx not in chain and len(tx_to_ins.get(next_tx, [])) == 1 and len(tx_to_outs.get(next_tx, [])) == 2:
                            chain.append(next_tx)
                            curr_tx = next_tx
                            continue
                    break

                if len(chain) >= min_hops:
                    chains.append(chain)
                    for t in chain:
                        visited_txs.add(t)

        # Generate evidence for each transaction in the discovered chains
        for chain_idx, chain in enumerate(chains, start=1):
            chain_len = len(chain)
            start_tx = chain[0]
            end_tx = chain[-1]
            origin_wallet = tx_to_ins[start_tx][0][0] if tx_to_ins[start_tx] else "UNKNOWN"

            for hop_num, tx in enumerate(chain, start=1):
                evidence = (
                    f"Peeling Chain detected: Hop {hop_num} of {chain_len}-hop continuous layering chain. "
                    f"Originated at wallet {origin_wallet[:12]}..., routing funds through change hops."
                )
                results.append({
                    "txid": tx,
                    "detected_pattern": "PEELING_CHAIN",
                    "confidence_score": min(0.99, 0.85 + (0.02 * chain_len)),
                    "chain_hops": chain_len,
                    "mix_pool_size": 0,
                    "evidence_details": evidence
                })

        print(f"[+] Found {len(chains):,} Peeling Chains encompassing {len(results):,} individual transactions.")
        return results

    def detect_ip_hopping(self, min_distinct_ips: int = 2) -> List[Dict[str, Any]]:
        """
        Detects IP Hopping & Proxy/VPN Rotation:
        Flags wallets that broadcast transactions across multiple distinct IP addresses
        or countries, indicating automated proxy rotation, Tor routing, or VPN churn.
        """
        print(f"[*] Scanning for IP Hopping / Proxy Rotation (min distinct IPs: {min_distinct_ips})...")
        results = []

        # Join inputs with transactions to find src_ip and geo_country per wallet
        df_wallet_tx = pd.merge(
            self.df_inputs[["txid", "address"]],
            self.df_tx[["txid", "src_ip", "geo_country", "asn", "timestamp"]],
            on="txid",
            how="inner"
        )
        df_wallet_tx = df_wallet_tx[df_wallet_tx["src_ip"] != "0.0.0.0"]

        # Group by wallet address
        for wallet, group in df_wallet_tx.groupby("address"):
            distinct_ips = [ip for ip in group["src_ip"].unique() if ip and ip != "0.0.0.0"]
            distinct_countries = [c for c in group["geo_country"].unique() if c and c != "UNKNOWN"]
            
            if len(distinct_ips) >= min_distinct_ips:
                top_ips_str = ", ".join(list(distinct_ips)[:4])
                country_str = ", ".join(distinct_countries[:3]) if distinct_countries else "Multiple Locations"
                evidence = (
                    f"IP Hopping / Proxy Churn detected: Wallet {wallet[:12]}... transacted across "
                    f"{len(distinct_ips)} distinct IPs ({top_ips_str}) spanning {len(distinct_countries) or 1} country regions ({country_str}), "
                    f"indicating automated proxy rotation, VPN server switching, or Tor exit node routing."
                )
                
                # Flag all associated transactions for this wallet
                for txid in group["txid"].unique():
                    results.append({
                        "txid": txid,
                        "detected_pattern": "IP_HOPPING_SUSPECT",
                        "confidence_score": min(0.95, 0.70 + 0.05 * len(distinct_ips)),
                        "chain_hops": len(distinct_ips),
                        "mix_pool_size": len(distinct_countries),
                        "evidence_details": evidence
                    })

        print(f"[+] Found {len(results):,} transactions linked to IP Hopping / Proxy Churn actors.")
        return results

    def run_detection(self) -> pd.DataFrame:
        """Executes all pattern detectors and merges into unified DataFrame."""
        if self.df_tx is None:
            self.load_data()

        cj_results = self.detect_coinjoin_mixing()
        peel_results = self.detect_peeling_chains()
        ip_results = self.detect_ip_hopping()

        all_results = cj_results + peel_results + ip_results

        if all_results:
            df_patterns = pd.DataFrame(all_results)
            # Remove any duplicates if a tx met multiple rules
            df_patterns = df_patterns.drop_duplicates(subset=["txid"], keep="first")
        else:
            df_patterns = pd.DataFrame(columns=[
                "txid", "detected_pattern", "confidence_score", "chain_hops", "mix_pool_size", "evidence_details"
            ])

        # Merge with overall transaction table so every transaction has a record
        df_merged = pd.merge(
            self.df_tx[["txid", "timestamp", "datetime_utc", "src_ip", "geo_country", "asn", "volume_usd", "fee_btc"]],
            df_patterns,
            on="txid",
            how="left"
        )
        df_merged["detected_pattern"] = df_merged["detected_pattern"].fillna("NONE")
        df_merged["confidence_score"] = df_merged["confidence_score"].fillna(0.0)
        df_merged["chain_hops"] = df_merged["chain_hops"].fillna(0).astype(int)
        df_merged["mix_pool_size"] = df_merged["mix_pool_size"].fillna(0).astype(int)
        df_merged["evidence_details"] = df_merged["evidence_details"].fillna("No overt structural laundering pattern observed.")

        self.detected_records = df_merged
        return df_merged

    def save_results(self, out_csv: str = "detected_patterns.csv"):
        if self.detected_records is not None:
            self.detected_records.to_csv(out_csv, index=False)
            print(f"[+] Saved pattern detection results to: {out_csv}")


def run_pattern_detection(db_path: str = "bitcoin_traffic.db",
                          graph_path: Optional[str] = "graph.gpickle",
                          out_csv: str = "detected_patterns.csv") -> pd.DataFrame:
    """Convenience functional API for Step 5 integration."""
    detector = PatternDetector(db_path=db_path, graph_path=graph_path)
    df = detector.run_detection()
    detector.save_results(out_csv)
    return df


def main():
    parser = argparse.ArgumentParser(description="ChainSentinel // Step 4 (Module C): Pattern Detection")
    parser.add_argument("--db", type=str, default="bitcoin_traffic.db", help="Path to SQLite database")
    parser.add_argument("--graph", type=str, default="graph.gpickle", help="Path to graph.gpickle")
    parser.add_argument("--out", type=str, default="detected_patterns.csv", help="Output CSV path")
    args = parser.parse_args()

    run_pattern_detection(db_path=args.db, graph_path=args.graph, out_csv=args.out)


if __name__ == "__main__":
    main()
