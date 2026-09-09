# ChainSentinel: AI-Powered Bitcoin Transaction Intelligence
## Technical Architecture & Methodology Write-up (SIH26146)

---

### 1. Problem Understanding
Public blockchain transparency is fundamentally challenged by pseudonymous layering techniques—specifically peeling chains, multi-party CoinJoin mixers, and Sybil wallet clusters—which obscure transactional lineage. Traditional block explorers lack contextual network-layer visibility, while rule-based heuristic monitoring triggers unmanageable false-positive rates. **ChainSentinel** resolves this by fusing on-chain Bitcoin UTXO transaction graphs with P2P network telemetry (relay IPs, Autonomous Systems, and temporal bursts) into an unsupervised, graph-native intelligence pipeline that detects, explains, and ranks illicit transaction flows in near-real-time.

---

### 2. End-to-End System Architecture

ChainSentinel operates as a five-stage modular pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & NORMALIZATION (ingest.py)                                     │
│    • Multi-Format Reader (CSV, JSON, XML) with auto-detection                │
│    • Schema Normalizer: UnifiedTransaction dataclass                         │
│    • SQLite Persistent Store: indexed transactions, tx_inputs, tx_outputs    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. TOPOLOGICAL GRAPH CONSTRUCTION (graph_builder.py)                         │
│    • Heterogeneous MultiDiGraph (NetworkX): Wallets, Transactions, IPs      │
│    • Common-Input-Ownership Heuristic via Disjoint Set Union (Union-Find)   │
│    • IP Colocation & Multi-Temporal Relay Signals (SAME_IP_SIGNAL)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. FOUR SPECIALIZED AI/ML DETECTION MODULES (Step 4)                        │
│  ┌────────────────────────┐  ┌────────────────────────┐                     │
│  │ Module A: Clustering   │  │ Module B: Anomalies    │                     │
│  │ Node2Vec Embeddings    │  │ Isolation Forest +     │                     │
│  │ + K-Means Spectral DSU │  │ Bottleneck Autoencoder │                     │
│  └────────────────────────┘  └────────────────────────┘                     │
│  ┌────────────────────────┐  ┌────────────────────────┐                     │
│  │ Module C: Patterns     │  │ Module D: Risk Scoring │                     │
│  │ Peeling-Chain Traversal│  │ Personalized PageRank  │                     │
│  │ + CoinJoin Mix Detector│  │ Taint Propagation      │                     │
│  └────────────────────────┘  └────────────────────────┘                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. ALERT GENERATION & EXPLAINABILITY (alert_generator.py)                    │
│    • Multi-Signal Weighted Confidence Fusion                                │
│    • Dynamic Forensic Narratives & Structured Evidence Links                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. INVESTIGATOR CONSOLE & LINK ANALYSIS (dashboard.py)                       │
│    • Streamlit Dark SOC Interface & Interactive Vis.js Ego-Network Explorer │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **Ingestion & Normalization**: Auto-detects input formats, handles stringified/native nested arrays, validates structural integrity without pipeline termination on corrupt records, and commits records into an indexed SQLite store.
2. **Graph Construction**: Builds an in-memory heterogeneous directed multigraph mapping wallet-to-transaction inputs (`INPUT_TO`), transaction-to-wallet outputs (`OUTPUT_TO`), and transaction-to-relay IP edges (`BROADCAST_FROM`).
3. **Four AI/ML Focus Modules**: Independent machine learning and topological algorithms extract localized structural and statistical features.
4. **Alert Generation & Explainability**: Formulates an ensemble confidence score and synthesizes contextual evidence into human-readable narratives.
5. **Investigator Console**: Single-pane interactive SOC web dashboard providing drilldown link analysis and entity tracing.

---

### 3. Dataset Approach & Synthetic Ground Truth
- **Motivation**: Real-world cryptocurrency fraud data suffers from extreme class imbalance, confidential law enforcement tagging, and absent network-layer telemetry. To benchmark machine learning models across deterministic attack vectors, ChainSentinel incorporates a hybrid synthetic dataset grounded in historical 1-minute BTC/USD OHLCV market pricing (2012–2026).
- **Modeled Typologies**:
  1. **Peeling Chains**: Algorithmic funding layering where an illicit wallet strips off a small payment (0.05–0.35 BTC) while cascading the remainder change address across 5–15 sequential hops.
  2. **CoinJoin / Mixing Pools**: Anonymization rounds matching 5–12 independent inputs into identical output denominations (e.g., 0.05 BTC or 0.1 BTC) simulating Wasabi/Whirlpool protocols.
  3. **Common-Input Clusters**: Sybil wallet entities (5–9 addresses) co-spending together across repeated consolidation sweeps broadcast from static relay IPs.
  4. **Statistical Anomalies**: Whale treasury transfers (>150 BTC), fat-finger transaction fee errors (>0.25 BTC), dust spam attacks (1-satoshi fees), and sub-second transaction bursts.
- **Validation**: Every generated wallet and transaction is cross-referenced against a separate `ground_truth.csv` mapping `wallet_id -> (entity_group, is_suspicious, pattern_type)` for empirical verification.

---

### 4. Model Choices & Technical Justifications

#### Module A: Entity Clustering (`entity_clustering.py`)
- **Algorithm**: Biased Random-Walk Graph Embeddings (Node2Vec principles) compressed via Truncated Singular Value Decomposition (SVD), paired with K-Means clustering and Union-Find Disjoint Set Union (DSU).
- **Justification**: Pure heuristic multi-input clustering misses entities that deliberately avoid co-spending in the same transaction. Graph embeddings encode second-order topological proximity and shared counterparty behaviors into a continuous 32-dimensional metric space, allowing detection of unlinked wallets belonging to the same criminal infrastructure.

#### Module B: Behavioral Anomaly Detection (`anomaly_detection.py`)
- **Algorithm**: Dual-Model Ensemble comprising **Isolation Forest** ($n=150$) and a 3-layer **Bottleneck Reconstruction Autoencoder** (MLP: 8 $\rightarrow$ 4 $\rightarrow$ 8).
- **Justification**: Isolation Forest handles non-linear, multi-modal financial distributions without requiring labeled fraud data by isolating tree anomalies via short path lengths. The Autoencoder complements this by penalizing reconstruction loss on rare multivariate feature correlations (e.g., disproportionate fee-to-volume ratios combined with anomalous midnight broadcast hours).

#### Module C: Peeling-Chain & Privacy Mixing Traversal (`pattern_detection.py`)
- **Algorithm**: Directed Graph Forward-Chaining & Anonymity-Set Combinatorial Matching.
- **Justification**: Statistical anomaly detectors often miss laundering chains because individual peeling transactions look like standard payments. Deterministic graph traversal traces change-address reuse across four or more continuous hops, while output denomination variance analysis isolates CoinJoin mixing pools with 100% precision.

#### Module D: Risk Scoring & Taint Propagation (`risk_scoring.py`)
- **Algorithm**: Personalized PageRank (PPR) / Random Walk with Restart (damping factor $\alpha = 0.85$).
- **Justification**: Criminal funds dissipate across intermediary hops. Personalized PageRank models the mathematical likelihood of a random surfer originating from a confirmed illicit seed wallet reaching any given node, naturally factoring in multi-hop path distances, graph density, and transaction dilution.

---

### 5. Explainability Method (XAI)
Black-box AI flags are unacceptable for financial intelligence units and criminal investigators. ChainSentinel delivers multi-tiered explainability:
1. **Feature Attribution (SHAP Principles)**: For each statistical outlier, normalized z-score discrepancies highlight the specific dimensions driving the anomaly score (e.g., *"Fee is 340% above network baseline"*).
2. **Dynamic Natural Language Forensic Narratives**: The alert generator correlates output tags from all four models and dynamically populates verified forensic facts:
   > *"Flagged with 85% confidence: (1) CoinJoin privacy mixer signature: 12 inputs unified into 24 outputs with 12 equal denominations. (2) Personalized PageRank detected close topological affinity (risk: 0.99) to known illicit seed entities. (3) Primary wallet is co-clustered with 12 addresses within entity ENTITY_00590. (4) Broadcast from source node 8.219.112.24 (Alibaba Cloud)."*
3. **Structured Evidence Links**: Every alert provides a machine-readable JSON dictionary containing active TXIDs, connected wallet addresses, relay IPs, and entity identifiers for instant visualization in the Link-Analysis Graph.

---

### 6. Results Snapshot & Performance Metrics

| Metric | Measured Value |
| :--- | :--- |
| **Total Ingested Transactions** | 7,862 records (15,724 deduplicated reads) |
| **Total Active Graph Nodes** | 42,707 nodes (27,772 Wallets, 7,862 TXIDs, 7,073 IPs) |
| **Total Graph Edges** | 48,105 directed relational edges |
| **Disjoint Entity Clusters Discovered** | 23,756 entity groups (2,125 multi-wallet clusters) |
| **Peeling Chains Traced** | 64 distinct chains (645 individual transaction hops) |
| **CoinJoin Mixer Transactions Isolated** | 200 high-anonymity mixing events |
| **Tainted Seed Propagation (Critical Risk)** | 7,651 wallets prioritized |
| **High-Confidence Intelligence Alerts** | 150 top-tier ranked alerts exported |
| **End-to-End Pipeline Execution Time** | < 35 seconds (from raw SQLite to ML inference) |

---

### 7. Limitations & Future Scope
1. **Full Mainnet Scalability**: While the SQLite WAL-mode and NetworkX architecture easily processes $10^5$ transactions locally, deploying on full Bitcoin mainnet volume ($10^9$ UTXOs) would benefit from migrating graph storage to Neo4j or Memgraph with distributed Graph Neural Networks (PyTorch Geometric).
2. **Dynamic Live Mempool Taint**: Integrating live zero-mq Bitcoin core RPC listeners would enable pre-confirmation scoring before block inclusion.
3. **Cross-Chain Bridge & Lightning Tracking**: Expanding entity heuristics to cross-chain swap bridges (e.g., BTC to Monero/USDT) and Lightning Network channel close sweeps.
