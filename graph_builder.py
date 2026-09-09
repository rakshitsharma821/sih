#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
STEP 3 — ENTITY & TRANSACTION GRAPH BUILDER
===================================================================================
Constructs a heterogeneous Directed Multigraph (NetworkX):
- Nodes: Wallet Addresses, Transactions (TXID), IP Addresses (with node_type)
- Edges: INPUT_TO, OUTPUT_TO, BROADCAST_FROM, SAME_IP_SIGNAL
- Heuristics:
  1. Common-Input-Ownership Heuristic via Union-Find (Disjoint Set Union)
  2. Multi-temporal IP Colocation Signal
Persists graph to disk and exports wallet -> entity_group mapping table.
===================================================================================
"""

import os
import sys
import time
import pickle
import sqlite3
import argparse
import pandas as pd
import networkx as nx
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional


# ===================================================================================
# 1. UNION-FIND (DISJOINT SET UNION) DATA STRUCTURE
# ===================================================================================
class DisjointSetUnion:
    """Efficient Union-Find with path compression and union by rank."""

    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            return item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])  # Path compression
        return self.parent[item]

    def union(self, item1: str, item2: str):
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 != root2:
            # Union by rank
            if self.rank[root1] < self.rank[root2]:
                self.parent[root1] = root2
            elif self.rank[root1] > self.rank[root2]:
                self.parent[root2] = root1
            else:
                self.parent[root2] = root1
                self.rank[root1] += 1

    def get_clusters(self) -> Dict[str, List[str]]:
        clusters = defaultdict(list)
        for item in list(self.parent.keys()):
            root = self.find(item)
            clusters[root].append(item)
        return dict(clusters)


# ===================================================================================
# 2. GRAPH BUILDER & QUERY ENGINE
# ===================================================================================
class ChainSentinelGraphBuilder:
    """Builds, persists, and queries the Bitcoin transaction-entity graph."""

    def __init__(self, db_path: str = "bitcoin_traffic.db"):
        self.db_path = db_path
        self.graph = nx.MultiDiGraph()
        self.dsu = DisjointSetUnion()
        self.entity_map: Dict[str, str] = {}  # wallet_address -> entity_group_id
        self.entity_clusters: Dict[str, List[str]] = {}  # entity_group_id -> [wallets]

    def build_graph(self) -> nx.MultiDiGraph:
        """Loads data from SQLite and populates nodes, edges, and entity heuristics."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}. Please run ingest.py first.")

        conn = sqlite3.connect(self.db_path)
        print(f"[*] Connecting to SQLite DB: {self.db_path}")

        # 1. Load Transactions
        print("[+] Loading transactions...")
        df_tx = pd.read_sql_query("""
            SELECT txid, timestamp, datetime_utc, src_ip, dst_ip, src_port, dst_port,
                   geo_country, asn, script_type, fee_btc, btc_price_usd, volume_usd, pattern_label
            FROM transactions
        """, conn)

        # 2. Load Inputs
        print("[+] Loading transaction inputs...")
        df_inputs = pd.read_sql_query("SELECT txid, address, amount_btc FROM tx_inputs", conn)

        # 3. Load Outputs
        print("[+] Loading transaction outputs...")
        df_outputs = pd.read_sql_query("SELECT txid, address, amount_btc FROM tx_outputs", conn)

        conn.close()

        # Add Transaction Nodes
        print(f"[+] Adding {len(df_tx):,} transaction nodes...")
        for _, row in df_tx.iterrows():
            self.graph.add_node(
                row['txid'],
                node_type="transaction",
                timestamp=row['timestamp'],
                datetime_utc=row['datetime_utc'],
                fee_btc=row['fee_btc'],
                volume_usd=row['volume_usd'],
                script_type=row['script_type'],
                pattern_label=row['pattern_label']
            )

            # Add IP node and BROADCAST_FROM edge
            src_ip = row['src_ip']
            if src_ip and src_ip != "0.0.0.0":
                if not self.graph.has_node(src_ip):
                    self.graph.add_node(
                        src_ip,
                        node_type="ip_address",
                        geo_country=row['geo_country'],
                        asn=row['asn']
                    )
                self.graph.add_edge(
                    row['txid'],
                    src_ip,
                    edge_type="BROADCAST_FROM",
                    timestamp=row['timestamp']
                )

        # Group inputs by txid for Common-Input-Ownership Heuristic
        tx_to_inputs = defaultdict(list)
        print(f"[+] Processing {len(df_inputs):,} input edges & applying Common-Input Heuristic...")
        for _, row in df_inputs.iterrows():
            txid = row['txid']
            addr = row['address']
            amt = row['amount_btc']

            tx_to_inputs[txid].append(addr)

            # Add Wallet Node
            if not self.graph.has_node(addr):
                self.graph.add_node(addr, node_type="wallet", entity_group=None)

            # Add INPUT_TO edge
            self.graph.add_edge(
                addr,
                txid,
                edge_type="INPUT_TO",
                amount_btc=amt
            )

        # Apply Union-Find on Common Inputs
        multi_input_tx_count = 0
        for txid, addrs in tx_to_inputs.items():
            if len(addrs) > 1:
                multi_input_tx_count += 1
                base_addr = addrs[0]
                for other_addr in addrs[1:]:
                    self.dsu.union(base_addr, other_addr)

        # Process Outputs
        print(f"[+] Processing {len(df_outputs):,} output edges...")
        for _, row in df_outputs.iterrows():
            txid = row['txid']
            addr = row['address']
            amt = row['amount_btc']

            if not self.graph.has_node(addr):
                self.graph.add_node(addr, node_type="wallet", entity_group=None)

            self.graph.add_edge(
                txid,
                addr,
                edge_type="OUTPUT_TO",
                amount_btc=amt
            )

        # Assign entity group IDs to all wallets
        print("[+] Finalizing Entity Groups (Common-Input Ownership)...")
        raw_clusters = self.dsu.get_clusters()
        group_idx = 1
        for root, wallet_list in raw_clusters.items():
            entity_id = f"ENTITY_{group_idx:05d}"
            self.entity_clusters[entity_id] = wallet_list
            for w in wallet_list:
                self.entity_map[w] = entity_id
                if self.graph.has_node(w):
                    self.graph.nodes[w]['entity_group'] = entity_id
            group_idx += 1

        # Also assign singleton entity IDs to any wallet that wasn't multi-input
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'wallet' and data.get('entity_group') is None:
                entity_id = f"ENTITY_{group_idx:05d}"
                self.entity_map[node] = entity_id
                self.entity_clusters[entity_id] = [node]
                self.graph.nodes[node]['entity_group'] = entity_id
                group_idx += 1

        # Add IP-Based Clustering Signal (wallets appearing repeatedly from the exact same source IP)
        print("[+] Computing IP-based colocation signals across wallets...")
        ip_to_wallets = defaultdict(set)
        for txid, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'transaction':
                # find broadcast IP
                ip_neighbors = [
                    v for u, v, k, d in self.graph.out_edges(txid, data=True, keys=True)
                    if d.get('edge_type') == 'BROADCAST_FROM'
                ]
                # find input wallets
                in_wallets = [
                    u for u, v, k, d in self.graph.in_edges(txid, data=True, keys=True)
                    if d.get('edge_type') == 'INPUT_TO'
                ]
                for ip in ip_neighbors:
                    for w in in_wallets:
                        ip_to_wallets[ip].add(w)

        # Add SAME_IP_SIGNAL edges for wallets sharing the same IP
        same_ip_edges_added = 0
        for ip, wallets in ip_to_wallets.items():
            if 1 < len(wallets) <= 30:  # limit clique explosion on super-popular IPs
                w_list = list(wallets)
                for i in range(len(w_list)):
                    for j in range(i + 1, min(i + 6, len(w_list))):
                        self.graph.add_edge(
                            w_list[i],
                            w_list[j],
                            edge_type="SAME_IP_SIGNAL",
                            shared_ip=ip
                        )
                        same_ip_edges_added += 1

        print(f"    Added {same_ip_edges_added:,} SAME_IP_SIGNAL relational edges.")
        return self.graph

    # -------------------------------------------------------------------------------
    # 3. QUERY API FUNCTIONS
    # -------------------------------------------------------------------------------
    def get_entity_wallets(self, entity_group_id: str) -> List[str]:
        """Returns all wallet addresses belonging to an entity group."""
        return self.entity_clusters.get(entity_group_id, [])

    def get_wallet_neighbors(self, address: str, hops: int = 1) -> Dict[str, Any]:
        """Returns all connected transactions, peer wallets, and broadcast IPs within k hops."""
        if not self.graph.has_node(address):
            return {"error": f"Address {address} not in graph"}

        nodes_at_hops = {0: {address}}
        visited = {address}

        for h in range(1, hops + 1):
            current_layer = set()
            for n in nodes_at_hops[h - 1]:
                # In and out neighbors
                neighbors = set(self.graph.predecessors(n)) | set(self.graph.successors(n))
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        current_layer.add(neighbor)
            nodes_at_hops[h] = current_layer

        connected_data = []
        for n in visited:
            if n != address:
                d = dict(self.graph.nodes[n])
                d['node_id'] = n
                connected_data.append(d)

        return {
            "root_wallet": address,
            "entity_group": self.entity_map.get(address, "UNKNOWN"),
            "total_connected": len(connected_data),
            "neighbors": connected_data
        }

    def get_transaction_path(self, txid: str) -> Dict[str, Any]:
        """Returns the full input and output topology + network metadata for a transaction."""
        if not self.graph.has_node(txid):
            return {"error": f"Transaction {txid} not found in graph"}

        tx_data = dict(self.graph.nodes[txid])

        # Inputs: in-edges with INPUT_TO
        inputs = []
        for u, v, k, d in self.graph.in_edges(txid, data=True, keys=True):
            if d.get('edge_type') == 'INPUT_TO':
                inputs.append({
                    "address": u,
                    "amount_btc": d.get('amount_btc', 0.0),
                    "entity_group": self.entity_map.get(u, "UNKNOWN")
                })

        # Outputs: out-edges with OUTPUT_TO
        outputs = []
        broadcast_ips = []
        for u, v, k, d in self.graph.out_edges(txid, data=True, keys=True):
            if d.get('edge_type') == 'OUTPUT_TO':
                outputs.append({
                    "address": v,
                    "amount_btc": d.get('amount_btc', 0.0),
                    "entity_group": self.entity_map.get(v, "UNKNOWN")
                })
            elif d.get('edge_type') == 'BROADCAST_FROM':
                broadcast_ips.append(v)

        return {
            "txid": txid,
            "metadata": tx_data,
            "inputs": inputs,
            "outputs": outputs,
            "broadcast_ips": broadcast_ips
        }

    # -------------------------------------------------------------------------------
    # 4. PERSISTENCE & STATS EXPORTER
    # -------------------------------------------------------------------------------
    def save(self, out_path: str = "graph.gpickle", csv_entity_path: str = "wallet_entities.csv"):
        """Saves graph using standard pickle serialization and exports wallet entity CSV."""
        print(f"\n[*] Persisting graph to: {out_path}...")
        with open(out_path, "wb") as f:
            pickle.dump(self.graph, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"[+] Graph saved successfully ({os.path.getsize(out_path) / (1024*1024):.2f} MB).")

        # Export wallet entity mapping table
        print(f"[*] Exporting wallet entity mapping to: {csv_entity_path}...")
        rows = [
            {"wallet_address": addr, "entity_group_id": eg_id}
            for addr, eg_id in self.entity_map.items()
        ]
        df_entities = pd.DataFrame(rows)
        df_entities.to_csv(csv_entity_path, index=False)
        print(f"[+] Exported {len(df_entities):,} entity mappings.")

        # Also store to SQLite if possible
        try:
            conn = sqlite3.connect(self.db_path)
            df_entities.to_sql("wallet_entities", conn, if_exists="replace", index=False)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_wallet ON wallet_entities(wallet_address);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_group ON wallet_entities(entity_group_id);")
            conn.close()
            print("[+] Saved wallet_entities table in SQLite database.")
        except Exception as e:
            print(f"[!] Note: Could not update SQLite wallet_entities: {e}")

    def print_summary(self):
        """Prints comprehensive topological and entity clustering statistics."""
        nodes_by_type = defaultdict(int)
        for _, d in self.graph.nodes(data=True):
            nodes_by_type[d.get('node_type', 'unknown')] += 1

        edges_by_type = defaultdict(int)
        for _, _, d in self.graph.edges(data=True):
            edges_by_type[d.get('edge_type', 'unknown')] += 1

        cluster_sizes = [len(v) for v in self.entity_clusters.values()]
        multi_wallet_clusters = [s for s in cluster_sizes if s > 1]
        max_size = max(cluster_sizes) if cluster_sizes else 0
        avg_size = sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0.0

        print("\n" + "=" * 65)
        print("CHAINSENTINEL // GRAPH TOPOLOGY & ENTITY SUMMARY")
        print("=" * 65)
        print(f"Total Nodes In Graph           : {self.graph.number_of_nodes():,}")
        for ntype, count in sorted(nodes_by_type.items()):
            print(f"  - {ntype.capitalize():<22} : {count:,}")
        print("-" * 65)
        print(f"Total Edges In Graph           : {self.graph.number_of_edges():,}")
        for etype, count in sorted(edges_by_type.items()):
            print(f"  - {etype:<22} : {count:,}")
        print("-" * 65)
        print(f"Total Entity Groups Found      : {len(self.entity_clusters):,}")
        print(f"Multi-Wallet Merged Clusters   : {len(multi_wallet_clusters):,}")
        print(f"Largest Entity Cluster Size    : {max_size:,} wallets")
        print(f"Average Wallets / Entity Group : {avg_size:.2f}")
        print("=" * 65 + "\n")


# ===================================================================================
# 5. CLI INTERFACE
# ===================================================================================
def main():
    parser = argparse.ArgumentParser(
        description="ChainSentinel // Step 3: Entity/Transaction Graph Builder"
    )
    parser.add_argument(
        "--db", type=str, default="bitcoin_traffic.db",
        help="Path to SQLite database (default: bitcoin_traffic.db)"
    )
    parser.add_argument(
        "--out", type=str, default="graph.gpickle",
        help="Path to output serialized graph (default: graph.gpickle)"
    )
    parser.add_argument(
        "--entities-csv", type=str, default="wallet_entities.csv",
        help="Path to output wallet-to-entity mapping CSV (default: wallet_entities.csv)"
    )

    args = parser.parse_args()

    builder = ChainSentinelGraphBuilder(db_path=args.db)
    builder.build_graph()
    builder.print_summary()
    builder.save(out_path=args.out, csv_entity_path=args.entities_csv)


if __name__ == "__main__":
    main()
