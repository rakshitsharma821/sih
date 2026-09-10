# ChainSentinel ? Linux Deployment & Air-Gapped Setup Guide
**SIH 2026 Problem Statement:** SIH26146  
**Organization:** National Technical Research Organisation (NTRO)  
**Classification:** Restricted / Law Enforcement & Intelligence SOC

---

## 1. Overview & System Requirements
ChainSentinel is engineered for 100% offline, air-gapped operation on Linux workstations and server environments (Ubuntu 22.04/24.04 LTS, Debian 12, RHEL 9, Rocky Linux). No live internet connection, cloud API, or external RPC nodes are required during execution.

### Hardware Prerequisites:
- **CPU:** 4+ Cores (x86_64 or aarch64)
- **RAM:** 8 GB minimum (16 GB recommended for 100k+ transaction link graphs)
- **Storage:** 2 GB free SSD storage
- **OS:** Linux Kernel 5.15+ (glibc 2.35+)

---

## 2. Fast-Start Execution (Single Script)

The repository provides an automated POSIX shell script that checks the environment, verifies dependencies, checks forensic caches, and starts the unified REST API + React SOC dashboard.

```bash
# Make script executable
chmod +x start_chainsentinel.sh

# Run offline SOC launcher
./start_chainsentinel.sh
```

The system automatically detects:
- Available Python binary (`python3` or `python`)
- Active virtual environment (`./venv` or `./.venv`)
- Core forensic packages (`fastapi`, `uvicorn`, `networkx`, `sklearn`, `pandas`, `numpy`, `shap`)
- Forensic databases (`bitcoin_traffic.db`, `graph.gpickle`)

Once running, access the SOC portal:
- **Interactive SOC Dashboard:** `http://localhost:8000`
- **Interactive Swagger REST API:** `http://localhost:8000/docs`
- **Multi-Format Ingestion Console:** `http://localhost:8000/ingest-console`

---

## 3. Air-Gapped / Offline Installation Steps

If setting up on a completely air-gapped machine without internet access:

### Step A: Download Wheels on an Internet-Connected Staging Machine
```bash
mkdir -p chainsentinel_wheels
pip download -r requirements.txt -d ./chainsentinel_wheels/
tar -czvf chainsentinel_wheels.tar.gz ./chainsentinel_wheels
```

### Step B: Transfer and Install on Air-Gapped Linux Node
```bash
# 1. Unpack wheels
tar -xzvf chainsentinel_wheels.tar.gz

# 2. Create isolated virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install packages strictly offline
pip install --no-index --find-links=./chainsentinel_wheels -r requirements.txt
```

---

## 4. Headless Pipeline Execution (CLI Mode)

To execute the entire 5-stage forensics pipeline from the command line:

```bash
# 1. Ingest multi-format transaction batch (CSV / JSON / XML)
python3 ingest.py --input transactions.csv --db bitcoin_traffic.db

# 2. Construct transaction graph & execute Union-Find clustering
python3 graph_builder.py --db bitcoin_traffic.db --out graph.gpickle

# 3. Run unsupervised ML anomaly detection & export models
python3 anomaly_detection.py --db bitcoin_traffic.db --out transaction_anomalies.csv

# 4. Detect structural peeling chains and CoinJoin mixers
python3 pattern_detection.py --db bitcoin_traffic.db --graph graph.gpickle --out detected_patterns.csv

# 5. Execute Personalized PageRank risk propagation
python3 risk_scoring.py --db bitcoin_traffic.db --graph graph.gpickle --out wallet_risk_scores.csv

# 6. Synthesize alerts with SHAP feature attribution
python3 alert_generator.py --db bitcoin_traffic.db --graph graph.gpickle --out alerts.json --top-n 150

# 7. Evaluate models against Ground Truth
python3 evaluate_models.py
```

Or run all steps automatically:
```bash
python3 run_pipeline.py
```

---

## 5. Linux systemd Service Configuration (Optional Daemon Mode)

To run ChainSentinel as a persistent daemon on a server:

Create `/etc/systemd/system/chainsentinel.service`:
```ini
[Unit]
Description=ChainSentinel Bitcoin Forensics SOC Engine
After=network.target

[Service]
Type=simple
User=chainsentinel
WorkingDirectory=/opt/chainsentinel
ExecStart=/opt/chainsentinel/venv/bin/python /opt/chainsentinel/api.py --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable chainsentinel
sudo systemctl start chainsentinel
sudo systemctl status chainsentinel
```

---

## 6. Offline Verification Checklist
- [x] Zero external network requests during ingestion, inference, and graph queries.
- [x] Models run purely on CPU via Scikit-Learn and SHAP TreeExplainer.
- [x] React static build embedded in FastAPI; no internet CDN needed.
- [x] SQLite database with WAL mode handles concurrent forensic queries.
