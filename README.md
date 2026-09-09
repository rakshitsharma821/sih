# SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
## Hybrid Synthetic Dataset Generator (Blockchain + P2P Network Metadata)

### 📌 Overview
This repository provides a modular, production-ready Python script to generate a **hybrid synthetic Bitcoin transaction and network traffic dataset** designed for AI/ML anomaly detection, clustering, and graph analysis in the **SIH26146** problem statement.

---

### 🚀 Key Capabilities
1. **Real Price Grounding (Kaggle Dataset)**:
   - Reads `btcusd_1-min_data.csv` (1-minute timestamped BTC/USD OHLCV price series).
   - Fast binary-search nearest-minute interpolation to calculate real USD equivalents and fee values.
   - Built-in automatic fallback curve if the Kaggle CSV is not present.

2. **Realistic Bitcoin Formats**:
   - Addresses: Legacy P2PKH (`1...`), Script Hash P2SH (`3...`), Native SegWit P2WPKH/P2WSH (`bc1q...`), Taproot (`bc1p...`).
   - Transaction IDs: 64-character double-SHA256 hex strings.

3. **P2P Network Metadata & GeoIP**:
   - `src_ip`, `dst_ip`, `src_port`, `dst_port` (default Bitcoin P2P port `8333` + testnet/RPC/ephemeral ports).
   - `geo_country` and `asn` with realistic ASNs (Amazon AWS, Hetzner, OVH, DigitalOcean, Cloudflare, Google Cloud, Jio, Airtel, etc.).
   - Supports **MaxMind GeoLite2** (`.mmdb`) with a high-accuracy offline fallback database.

4. **Injected Labeled Anomaly Patterns**:
   - **Peeling Chains**: Illicit money laundering hops where a fixed small amount is peeled off and the rest is forwarded through 5–15 chained change addresses.
   - **CoinJoin / Mixing**: Multi-input, multi-output privacy transactions with identical output denominations (Wasabi / Samourai model).
   - **Common-Input Ownership Clusters**: Entity wallet clusters that appear together as multi-inputs and share the same 1–2 originating IPs.
   - **Statistical Anomalies**: Whale movements (150–3500 BTC), fat-finger fee errors (>0.5 BTC fee), dust spam attacks (1 sat fee), and sub-second rapid transaction bursts.

---

### 📂 Output & Pipeline Files
- **`generate_dataset.py`**: Step 1 synthetic hybrid dataset generator.
- **`transactions.csv` & `transactions.json`**: Generated transaction feeds.
- **`ground_truth.csv`**: Labeled entity groups and anomaly tags.
- **`ingest.py`**: Step 2 Multi-format (CSV/JSON/XML) ingestion pipeline into SQLite.
- **`test_ingestion.py`**: Verification test suite demonstrating error handling and DB queries.
- **`ingest_console.html`**: Bitcoin-themed analyst console running 100% in-browser offline.
- **`bitcoin_traffic.db`**: Relational SQLite database with indexed tables (`transactions`, `tx_inputs`, `tx_outputs`).

---

### 📥 Step 2: Ingestion Pipeline Usage (`ingest.py`)

#### Run Ingestion on multiple files:
```bash
python ingest.py --input transactions.csv transactions.json --db bitcoin_traffic.db
```

#### Run Verification Test Suite:
```bash
python test_ingestion.py
```

#### Open Ingestion Analyst Console:
Simply double-click [`ingest_console.html`](file:///d:/bitcoinsihproject/ingest_console.html) in your browser or run:
```bash
# On Windows:
start ingest_console.html
# On Linux:
xdg-open ingest_console.html
```

---

### 📦 Installation

```bash
# Optional but recommended packages for faster processing and MaxMind GeoIP
pip install pandas numpy geoip2
```

---

### 🛠️ MaxMind GeoLite2 Setup (Optional)
If you want to use the official MaxMind GeoLite2 databases:
1. Create a free account at [MaxMind](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data).
2. Download `GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb`.
3. Place them in this directory (`d:\bitcoinsihproject\`).
4. The script will automatically detect them, or you can specify `--geolite-city` and `--geolite-asn`.
*(If not downloaded, the script automatically uses the built-in offline IP-to-ASN mapping without any errors).*

---

### 💻 Usage

#### 1. Default Run (8,000 transactions)
```bash
python generate_dataset.py
```

#### 2. Run with Kaggle 1-minute Price CSV
```bash
python generate_dataset.py --price-csv btcusd_1-min_data.csv --count 10000
```

#### 3. Custom Arguments
```bash
python generate_dataset.py \
  --count 10000 \
  --price-csv "btcusd_1-min_data.csv" \
  --out-csv "transactions.csv" \
  --out-json "transactions.json" \
  --out-gt "ground_truth.csv" \
  --seed 42
```
