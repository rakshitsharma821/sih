# ChainSentinel ? AI-Powered Bitcoin Transaction Traffic Forensics SOC
**Smart India Hackathon 2026 | Problem Statement SIH26146**  
**Organization:** National Technical Research Organisation (NTRO)  
**Category:** Software | **Theme:** Blockchain & Cybersecurity  
**Deployment Mode:** 100% Air-Gapped / Local Offline Operation

---

## ?? Executive Summary
**ChainSentinel** is a production-grade, air-gapped forensic intelligence platform designed for the National Technical Research Organisation (NTRO) to monitor, correlate, analyze, and de-anonymize Bitcoin transaction traffic. 

By unifying **network-layer telemetry** (IPv4/IPv6, P2P broadcast ports, ASNs, BGP Autonomous Systems, GeoIP lat/lon) with **blockchain-layer ledger activity** (UTXO inputs/outputs, script types, Satoshi fees, values), ChainSentinel uncovers money laundering topologies, privacy mixers, and automated bot operations in real-time without relying on external cloud APIs or third-party blockchain explorers.

---

## ??? System Architecture & Analytical Pipeline

ChainSentinel operates across six pipelined analytical stages:

```
[Ingestion Engine] (CSV / JSON / XML)
         ?
         ?
[Relational Core] (SQLite3 WAL Mode + Schema Integrity)
         ?
         ?
[Graph MultiDiGraph] (124,161 Nodes | 480,669 Edges | DSU Clustering | dst_ip RELAYED_TO)
         ?
 ????????????????????????????????????????????????????
 ?                                                  ?
 ?                                                  ?
[Unsupervised ML Anomaly Engine]          [Structural Graph Analytics]
 - Isolation Forest (sklearn)              - Peeling Chain Layering Detector
 - MLP Autoencoder (Bottleneck 16-4-16)    - Samourai/Wasabi CoinJoin Detector
 - TreeExplainer SHAP Attribution          - Personalized PageRank Taint Flow
 ????????????????????????????????????????????????????
         ?
         ?
[Forensic Alert Engine] (Confidence Formulation + Dynamic Natural-Language Evidence Trails)
         ?
         ?
[Modern Analyst SOC] (FastAPI REST Backend + React Link-Analysis Dashboard)
```

1. **Multi-Format Ingestion (`ingest.py`)**:
   - Streaming parser for CSV, JSON, and XML transaction batches.
   - Strict field normalization (`txid`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `timestamp`, `geo_country`, `asn`).
   - Resilient quarantine handler for corrupted, truncated, or malicious inputs.
2. **Topological MultiDiGraph & Entity Clustering (`graph_builder.py`)**:
   - Directed multigraph comprising `wallet`, `transaction`, and `ip_address` nodes.
   - Directed edges: `INPUT_TO`, `OUTPUT_TO`, `BROADCAST_FROM`, `RELAYED_TO` (Destination IP relay), and `SAME_IP_SIGNAL`.
   - Disjoint Set Union (DSU / Union-Find) with path compression implementing Satoshi's Common-Input Ownership Heuristic to collapse multi-input addresses into distinct cyber entities.
3. **Unsupervised Anomaly Detection (`anomaly_detection.py`)**:
   - 8-dimensional financial and temporal feature extraction (`total_input_btc`, `fee_btc`, `fee_as_pct_of_amount`, `input_count`, `output_count`, `hour_of_day`, `src_ip_frequency`, `time_since_last_tx`).
   - Isolation Forest and Deep Bottleneck Autoencoder Reconstruction ensemble.
4. **SHAP TreeExplainer Forensic Attribution (`explainability.py`)**:
   - Computes genuine local SHAP feature impact and directional attributions (`INCREASES_ANOMALY` vs `DECREASES_ANOMALY`).
   - Inverts tree path lengths so investigators know exactly *which* feature drove the model decision.
   - Produces publication-ready visual summaries (`reports/shap_summary.png`).
5. **Structural Obfuscation Detection (`pattern_detection.py`)**:
   - **Peeling Chains:** Detects 4-to-15 hop linear layering chains stripping change outputs.
   - **CoinJoin Mixers:** Detects high-entropy multi-party transactions with identical output values.
6. **Graph Risk Propagation (`risk_scoring.py`)**:
   - Personalized PageRank (PPR) calculating topological taint diffusion from known seed bad actors across the transaction network.
7. **Unified Alert Generation (`alert_generator.py`)**:
   - Blended confidence scoring formula synthesizing ML anomaly, PPR taint, structural pattern, and cluster size factors.
   - Human-readable natural-language forensic trails with nested link evidence.

---

## ? Quick-Start Guide

### A. Linux Launch (Single Command)
```bash
chmod +x start_chainsentinel.sh
./start_chainsentinel.sh
```

### B. Windows Launch
```cmd
start_chainsentinel.bat
```

Once started, access the interfaces:
- **Investigator SOC Dashboard:** [http://localhost:8000](http://localhost:8000)
- **Interactive REST API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Multi-Format Ingestion Console:** [http://localhost:8000/ingest-console](http://localhost:8000/ingest-console)

---

## ?? Master Automated Test Suite

ChainSentinel includes a 14-point automated test runner verifying all components:

```bash
python test_all.py
```

```
===========================================================================
 ChainSentinel (SIH26146) ? Master Test Suite & Verification Runner
===========================================================================
[01] Multi-Format Ingestion (CSV / JSON / XML) ................. [PASS]
[02] Corrupted & Malformed Data Quarantine ..................... [PASS]
[03] Relational Database Schema & Field Validation ............. [PASS]
[04] Graph MultiDiGraph & dst_ip RELAYED_TO Edges .............. [PASS]
[05] Common-Input Disjoint Set Union (DSU) Clustering .......... [PASS]
[06] Behavioral Feature Matrix Extraction (8 Features) ......... [PASS]
[07] Isolation Forest Inference & Bounded Scores ............... [PASS]
[08] MLP Autoencoder Reconstruction Inference .................. [PASS]
[09] TreeExplainer SHAP Feature Attribution & Fallback ......... [PASS]
[10] Structural Pattern Detectors (Peeling & CoinJoin) ......... [PASS]
[11] Personalized PageRank Risk Score Propagation .............. [PASS]
[12] Alert Synthesis, Evidence Trails & Forensic Drivers ....... [PASS]
[13] FastAPI REST API Routes (/health, /metrics, /alerts) ...... [PASS]
[14] Local Offline Mode & Air-Gapped Verification .............. [PASS]
===========================================================================
TOTAL: 14 | PASS: 14 | FAIL: 0 | SKIP: 0
STATUS: ALL 14 SYSTEM TESTS PASSED SUCCESSFULLY! (100% OPERATIONAL)
===========================================================================
```

---

## ?? Rigorous Model Evaluation & Benchmarking

To benchmark the machine learning models against ground-truth labels (`ground_truth.csv` and SQLite labels):

```bash
python evaluate_models.py
```

### Measured Performance Metrics:
| Intelligence Component | Model Architecture | Target Phenomenon | ROC-AUC | PR-AUC | Optimal F1 |
|---|---|---|---|---|---|
| **Transaction Anomaly** | Isolation Forest | Statistical Outliers | **0.8572** | **0.1137** | **0.2005** |
| **Transaction Anomaly** | Autoencoder Reconstruction | Bottleneck Reconstruction | **0.7854** | **0.2061** | **0.2420** |
| **Transaction Anomaly** | Blended Ensemble | Multivariate Anomaly | **0.8574** | **0.1554** | **0.2003** |
| **Graph Taint Propagation** | Personalized PageRank | Illicit Wallet Seed Affinity | **1.0000** | **1.0000** | **1.0000** |
| **Structural Pattern** | Peeling Chain Detector | Micro-Change Peels | N/A | N/A | **Precision 1.0000** |
| **Structural Pattern** | CoinJoin Mixer Detector | Samourai/Wasabi Denoms | N/A | N/A | **Precision 1.0000** |

Generated charts are saved in `reports/`:
- `reports/roc_curve.png`: ROC curves for Isolation Forest, Autoencoder, and Ensemble.
- `reports/pr_curve.png`: Precision-Recall curves.
- `reports/confusion_matrix.png`: Multi-model confusion matrix heatmaps.
- `reports/shap_summary.png`: Global SHAP TreeExplainer feature importance rankings.

---

## ?? Air-Gapped & Security Guarantees
- **Zero External Egress:** All dependencies run strictly on local CPU/RAM.
- **No Third-Party APIs:** No requests are made to Infura, Alchemy, Blockchain.com, OpenAI, or external web services.
- **Explainable by Design:** Black-box ML outputs are augmented with SHAP TreeExplainer and topological evidence trails.

---

## ?? Repository File Index
| File | Description |
|---|---|
| `start_chainsentinel.sh` | Linux POSIX launcher script with automatic environment detection |
| `start_chainsentinel.bat` | Windows batch launcher script |
| `LINUX_SETUP.md` | Comprehensive air-gapped Linux deployment and systemd guide |
| `evaluate_models.py` | Quantitative ML benchmark and evaluation engine |
| `MODEL_EVALUATION.md` | Auto-generated forensic evaluation report with metric tables |
| `explainability.py` | SHAP TreeExplainer attribution module with fallback heuristics |
| `test_all.py` | Unified 14-point test runner |
| `api.py` | FastAPI backend serving REST endpoints and embedded React UI |
| `ingest.py` | Multi-format CSV/JSON/XML streaming parser |
| `graph_builder.py` | MultiDiGraph constructor with `dst_ip` and DSU entity clustering |
| `anomaly_detection.py` | Isolation Forest and MLP Autoencoder anomaly detector |
| `pattern_detection.py` | Peeling chain and CoinJoin mixer structural detector |
| `risk_scoring.py` | Personalized PageRank graph taint propagation |
| `alert_generator.py` | Weighted confidence synthesis and dynamic evidence generator |
| `TECHNICAL_WRITEUP.md` | Full technical documentation for NTRO audit |
