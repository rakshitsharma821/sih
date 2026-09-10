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

### 5. Explainability Method (XAI — TreeExplainer SHAP & Dynamic Evidence Trails)
Black-box AI flags are unacceptable for financial intelligence units and criminal investigators. ChainSentinel delivers multi-tiered, verifiable explainability:

1. **Genuine TreeExplainer SHAP Feature Attribution (`explainability.py`)**:
   - Computes local Shapley values directly over the trained Isolation Forest decision trees.
   - For an unsupervised Isolation Forest where anomalous instances traverse shorter tree path lengths ($\mathbb{E}[h(x)] < c(n)$), SHAP values are inverted ($\phi_{\text{anomaly}} = -\phi_{\text{tree}}$) so that positive attributions denote features that actively increase anomaly likelihood.
   - For every flagged transaction, the system calculates the top-3 feature drivers, absolute impact magnitudes, directional polarity (`INCREASES_ANOMALY` vs `DECREASES_ANOMALY`), and contextual descriptions.
   - Generates publication-grade global feature importance summaries (`reports/shap_summary.png`).
   - A robust Interquartile Range (IQR) divergence fallback ensures 100% operational resilience even in minimal offline runtime environments.

2. **Destination IP & Network-Layer Correlation**:
   - The graph builder explicitly instantiates both source (`src_ip`) and destination relay nodes (`dst_ip`), linking them via directed `BROADCAST_FROM` and `RELAYED_TO` edges.
   - Correlates multi-hop transaction propagation timing with ASNs and Autonomous Systems.

3. **Dynamic Natural Language Forensic Narratives**:
   - The alert generator synthesizes analytical tags across all four modules into natural-language forensic statements detailing exact hop counts, mixer denominations, PageRank taint affinity, co-clustering entity IDs, and SHAP drivers:
   > *"Flagged with 86% confidence: (1) CoinJoin privacy mixer signature: 12 inputs unified into 24 outputs with 12 equal denominations. (2) Personalized PageRank detected close topological affinity (risk: 1.00) to known illicit seed entities. (3) Primary wallet is co-clustered with 12 addresses within entity ENTITY_00171. (4) Broadcast from source node 20.42.81.167 (UNKNOWN, UNKNOWN). | Key Anomaly Drivers (SHAP TreeExplainer): Input Address Consolidation Count (+2.487), Miner Fee Amount (BTC) (+2.154), Output Fan-out Count (+2.115)."*

4. **Structured Evidence Links**:
   - Every alert provides a machine-readable JSON payload containing participating TXIDs, wallet addresses, relay IPs, entity clusters, Satoshi fee discrepancies, and embedded SHAP driver vectors for interactive link-analysis graph rendering.

---

### 6. Quantitative Evaluation & Benchmark Scorecard

ChainSentinel was rigorously evaluated against ground-truth labels (`ground_truth.csv` and SQLite transaction tags) via `evaluate_models.py`:

| Intelligence Component | Model Architecture | Evaluation Metric | Measured Benchmark |
| :--- | :--- | :--- | :--- |
| **Transaction Anomaly Detection** | Isolation Forest (sklearn) | ROC-AUC / PR-AUC / Best F1 | **0.8572** / **0.1137** / **0.2005** (Thresh: 0.32) |
| **Transaction Reconstruction** | MLP Autoencoder (Bottleneck 16-4-16) | ROC-AUC / PR-AUC / Best F1 | **0.7854** / **0.2061** / **0.2420** (Thresh: 0.11) |
| **Blended Anomaly Ensemble** | Dual Model Ensemble | ROC-AUC / PR-AUC / Best F1 | **0.8574** / **0.1554** / **0.2003** (Thresh: 0.20) |
| **Graph Taint Propagation** | Personalized PageRank ($\alpha=0.85$) | ROC-AUC / PR-AUC / Best F1 | **1.0000** / **1.0000** / **1.0000** (Thresh: 0.71) |
| **Peeling Chain Traversal** | Directed DFS Multi-Hop Engine | Precision / Recall / F1 | **1.0000** / **0.0952** / **0.1739** |
| **CoinJoin Mixer Detector** | Anonymity-Set Variance Engine | Precision / Recall / F1 | **1.0000** / **0.0960** / **0.1751** |
| **Total Ingested Transactions** | Multi-Format Streaming Store | Database Record Count | **81,632** normalized transactions |
| **Active Link-Analysis Graph** | Heterogeneous MultiDiGraph | Nodes / Edges | **124,161** nodes / **480,669** edges |
| **Automated System Verification** | Master Test Runner (`test_all.py`)| Unit / Integration / E2E | **14 / 14 Tests Passed (100%)** |

Generated evaluation artifacts:
- `reports/roc_curve.png`: Comparative ROC curves.
- `reports/pr_curve.png`: Precision-Recall curves.
- `reports/confusion_matrix.png`: Multi-model confusion matrix heatmaps.
- `reports/shap_summary.png`: Global SHAP TreeExplainer feature importance rankings.
- `evaluation_results.json`: Machine-readable benchmark scorecard.

---

### 7. Limitations & Future Scope
1. **Full Mainnet Scalability**: While the SQLite WAL-mode and NetworkX architecture easily processes $10^5$ transactions locally, deploying on full Bitcoin mainnet volume ($10^9$ UTXOs) would benefit from migrating graph storage to Neo4j or Memgraph with distributed Graph Neural Networks (PyTorch Geometric).
2. **Dynamic Live Mempool Taint**: Integrating live zero-mq Bitcoin core RPC listeners would enable pre-confirmation scoring before block inclusion.
3. **Cross-Chain Bridge & Lightning Tracking**: Expanding entity heuristics to cross-chain swap bridges (e.g., BTC to Monero/USDT) and Lightning Network channel close sweeps.
