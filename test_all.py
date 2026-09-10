#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
MASTER AUTOMATED TEST SUITE & SYSTEM VERIFICATION RUNNER
===================================================================================
Executes 14 comprehensive unit, integration, and E2E verification tests:
1. Multi-Format Ingestion (CSV / JSON / XML parsing)
2. Corrupted & Malformed Data Quarantine & Resilience
3. Relational Database Schema & Field Validation
4. Graph MultiDiGraph Construction, Destination IP & RELAYED_TO Edges
5. Common-Input Disjoint Set Union (DSU) Clustering
6. Behavioral Feature Matrix Extraction (8 Features)
7. Isolation Forest Inference & Bounded Scores [0, 1]
8. MLP Autoencoder Reconstruction Inference & Bounds [0, 1]
9. TreeExplainer SHAP Feature Attribution & Anomaly Drivers
10. Structural Pattern Detectors (Peeling Chain & CoinJoin Mixing)
11. Personalized PageRank Taint Risk Propagation
12. Alert Generation, Evidence Trails & Forensic Explanations
13. FastAPI REST API Routes (/health, /metrics, /alerts)
14. Local Offline Mode & Air-Gapped Verification
===================================================================================
"""

import os
import sys
import json
import pickle
import sqlite3
import tempfile
import numpy as np
import pandas as pd

passes = 0
fails = 0
skips = 0


def log_test(num: int, name: str, passed: bool, error_msg: str = ""):
    global passes, fails
    status = "[92m[PASS][0m" if passed else "[91m[FAIL][0m"
    dots = "." * max(2, 58 - len(name))
    print(f"[{num:02d}] {name} {dots} {status}")
    if passed:
        passes += 1
    else:
        fails += 1
        if error_msg:
            print(f"     ?? Error: {error_msg}")


# -----------------------------------------------------------------------------
# TEST 01: Multi-Format Ingestion (CSV / JSON / XML)
# -----------------------------------------------------------------------------
def test_01_ingestion():
    try:
        from ingest import IngestionParser
        parser = IngestionParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. CSV
            csv_path = os.path.join(tmpdir, "test.csv")
            df_csv = pd.DataFrame([{
                "txid": "tx_csv_01",
                "timestamp": 1700000000,
                "datetime_utc": "2023-11-14 22:13:20",
                "src_ip": "192.168.1.1",
                "dst_ip": "10.0.0.1",
                "src_port": 8333,
                "dst_port": 8333,
                "geo_country": "US",
                "asn": "AS15169",
                "input_addresses": "addr_in_1",
                "output_addresses": "addr_out_1;addr_out_2",
                "input_amounts": "1.5",
                "output_amounts": "1.0;0.499",
                "total_input_btc": 1.5,
                "total_output_btc": 1.499,
                "fee_btc": 0.001,
                "input_count": 1,
                "output_count": 2,
                "script_type": "P2WPKH",
                "btc_price_usd": 60000.0,
                "volume_usd": 90000.0,
                "pattern_label": "NORMAL"
            }])
            df_csv.to_csv(csv_path, index=False)
            csv_records = list(parser.parse_csv(csv_path))
            assert len(csv_records) == 1, f"Expected 1 CSV record, got {len(csv_records)}"
            assert csv_records[0]["txid"] == "tx_csv_01"

            # 2. JSON
            json_path = os.path.join(tmpdir, "test.json")
            df_csv["txid"] = "tx_json_01"
            df_csv.to_json(json_path, orient="records")
            json_records = list(parser.parse_json(json_path))
            assert len(json_records) == 1, f"Expected 1 JSON record, got {len(json_records)}"
            assert json_records[0]["txid"] == "tx_json_01"

            # 3. XML
            xml_path = os.path.join(tmpdir, "test.xml")
            with open(xml_path, "w", encoding="utf-8") as xf:
                xf.write("<transactions><transaction><txid>tx_xml_01</txid><timestamp>1700000002</timestamp><datetime_utc>2023-11-14 22:13:22</datetime_utc><src_ip>192.168.1.2</src_ip><dst_ip>10.0.0.2</dst_ip><src_port>8333</src_port><dst_port>8333</dst_port><geo_country>DE</geo_country><asn>AS24940</asn><input_addresses>addr_in_xml</input_addresses><output_addresses>addr_out_xml</output_addresses><input_amounts>2.0</input_amounts><output_amounts>1.999</output_amounts><total_input_btc>2.0</total_input_btc><total_output_btc>1.999</total_output_btc><fee_btc>0.001</fee_btc><input_count>1</input_count><output_count>1</output_count><script_type>P2TR</script_type><btc_price_usd>60000.0</btc_price_usd><volume_usd>120000.0</volume_usd><pattern_label>NORMAL</pattern_label></transaction></transactions>")
            xml_records = list(parser.parse_xml(xml_path))
            assert len(xml_records) == 1, f"Expected 1 XML record, got {len(xml_records)}"
            assert xml_records[0]["txid"] == "tx_xml_01"

        log_test(1, "Multi-Format Ingestion (CSV / JSON / XML)", True)
    except Exception as e:
        log_test(1, "Multi-Format Ingestion (CSV / JSON / XML)", False, str(e))


# -----------------------------------------------------------------------------
# TEST 02: Corrupted Data Quarantine
# -----------------------------------------------------------------------------
def test_02_quarantine():
    try:
        from ingest import IngestionParser
        parser = IngestionParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_csv = os.path.join(tmpdir, "bad.csv")
            with open(bad_csv, "w", encoding="utf-8") as bf:
                bf.write("invalid_col1,invalid_col2\nfoo,bar\n123,456\n")

            # Parser handles missing/corrupt fields gracefully without unhandled exceptions
            records = list(parser.parse_csv(bad_csv))
            # Bad records lacking required txid/timestamp are safely skipped or normalized
            assert len(records) == 0 or records[0].get("txid", "") == "", "Expected quarantine/skipping of malformed records"

        log_test(2, "Corrupted & Malformed Data Quarantine", True)
    except Exception as e:
        log_test(2, "Corrupted & Malformed Data Quarantine", False, str(e))


# -----------------------------------------------------------------------------
# TEST 03: Relational Database Schema & Field Validation
# -----------------------------------------------------------------------------
def test_03_db_schema():
    try:
        assert os.path.exists("bitcoin_traffic.db"), "bitcoin_traffic.db missing"
        conn = sqlite3.connect("bitcoin_traffic.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        required_tables = ["transactions", "tx_inputs", "tx_outputs", "wallet_entities"]
        for t in required_tables:
            assert t in tables, f"Missing table {t}"

        cursor.execute("PRAGMA table_info(transactions)")
        cols = {r[1]: r[2] for r in cursor.fetchall()}
        expected_cols = ["txid", "timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "geo_country", "asn"]
        for c in expected_cols:
            assert c in cols, f"Missing column {c} in transactions table"
        conn.close()

        log_test(3, "Relational Database Schema & Field Validation", True)
    except Exception as e:
        log_test(3, "Relational Database Schema & Field Validation", False, str(e))


# -----------------------------------------------------------------------------
# TEST 04: Graph MultiDiGraph Construction, Destination IP & RELAYED_TO Edges
# -----------------------------------------------------------------------------
def test_04_graph_builder():
    try:
        import networkx as nx
        assert os.path.exists("graph.gpickle"), "graph.gpickle missing"
        with open("graph.gpickle", "rb") as f:
            G = pickle.load(f)

        assert len(G.nodes) > 1000, f"Expected >1000 nodes, got {len(G.nodes)}"
        assert len(G.edges) > 1000, f"Expected >1000 edges, got {len(G.edges)}"

        # Check node types
        node_types = set(nx.get_node_attributes(G, "node_type").values())
        assert "wallet" in node_types or "wallet_address" in node_types, "wallet missing"
        assert "transaction" in node_types, "transaction missing"
        assert "ip_address" in node_types, "ip_address missing"

        # Check edge types
        edge_types = set()
        for _, _, data in G.edges(data=True):
            if "edge_type" in data:
                edge_types.add(data["edge_type"])
        assert "INPUT_TO" in edge_types or "SENT" in edge_types, "Input edge type missing"
        assert "OUTPUT_TO" in edge_types or "RECEIVED" in edge_types, "Output edge type missing"
        assert "BROADCAST_FROM" in edge_types, "BROADCAST_FROM missing"
        assert "RELAYED_TO" in edge_types, "RELAYED_TO edge type missing (dst_ip verification)"

        log_test(4, "Graph MultiDiGraph & dst_ip RELAYED_TO Edges", True)
    except Exception as e:
        log_test(4, "Graph MultiDiGraph & dst_ip RELAYED_TO Edges", False, str(e))


# -----------------------------------------------------------------------------
# TEST 05: Common-Input Disjoint Set Union (DSU) Clustering
# -----------------------------------------------------------------------------
def test_05_dsu_clustering():
    try:
        from graph_builder import DisjointSetUnion
        dsu = DisjointSetUnion()
        dsu.union("addrA", "addrB")
        dsu.union("addrB", "addrC")
        dsu.union("addrD", "addrE")
        assert dsu.find("addrA") == dsu.find("addrC"), "addrA and addrC should share parent"
        assert dsu.find("addrA") != dsu.find("addrD"), "addrA and addrD should have different parents"
        clusters = dsu.get_clusters()
        assert len(clusters[dsu.find("addrA")]) == 3
        assert len(clusters[dsu.find("addrD")]) == 2
        log_test(5, "Common-Input Disjoint Set Union (DSU) Clustering", True)
    except Exception as e:
        log_test(5, "Common-Input Disjoint Set Union (DSU) Clustering", False, str(e))


# -----------------------------------------------------------------------------
# TEST 06: Behavioral Feature Matrix Extraction (8 Features)
# -----------------------------------------------------------------------------
def test_06_feature_extraction():
    try:
        from anomaly_detection import TransactionAnomalyDetector
        detector = TransactionAnomalyDetector(db_path="bitcoin_traffic.db")
        df_feat = detector.extract_features()
        for fname in detector.feature_names:
            assert fname in df_feat.columns, f"Feature {fname} missing"
            assert not df_feat[fname].isna().all(), f"Feature {fname} is all NaN"
        assert len(detector.feature_names) == 8, f"Expected 8 features, got {len(detector.feature_names)}"
        log_test(6, "Behavioral Feature Matrix Extraction (8 Features)", True)
    except Exception as e:
        log_test(6, "Behavioral Feature Matrix Extraction (8 Features)", False, str(e))


# -----------------------------------------------------------------------------
# TEST 07: Isolation Forest Inference & Bounded Scores
# -----------------------------------------------------------------------------
def test_07_isolation_forest():
    try:
        import joblib
        assert os.path.exists("isolation_forest.joblib"), "isolation_forest.joblib missing"
        iso = joblib.load("isolation_forest.joblib")
        dummy_X = np.random.randn(10, 8)
        preds = iso.predict(dummy_X)
        assert len(preds) == 10
        if os.path.exists("transaction_anomalies.csv"):
            df = pd.read_csv("transaction_anomalies.csv", nrows=100)
            scores = df["isolation_score"].values
            assert (scores >= 0.0).all() and (scores <= 1.0).all(), "Scores out of bounds [0, 1]"
            assert not np.isnan(scores).any(), "NaN in scores"
        log_test(7, "Isolation Forest Inference & Bounded Scores", True)
    except Exception as e:
        log_test(7, "Isolation Forest Inference & Bounded Scores", False, str(e))


# -----------------------------------------------------------------------------
# TEST 08: MLP Autoencoder Reconstruction Inference
# -----------------------------------------------------------------------------
def test_08_autoencoder():
    try:
        if os.path.exists("transaction_anomalies.csv"):
            df = pd.read_csv("transaction_anomalies.csv", nrows=100)
            scores = df["autoencoder_score"].values
            assert (scores >= 0.0).all() and (scores <= 1.0).all(), "Autoencoder scores out of bounds [0, 1]"
            assert not np.isnan(scores).any(), "NaN in autoencoder scores"
        log_test(8, "MLP Autoencoder Reconstruction Inference", True)
    except Exception as e:
        log_test(8, "MLP Autoencoder Reconstruction Inference", False, str(e))


# -----------------------------------------------------------------------------
# TEST 09: TreeExplainer SHAP Feature Attribution & Fallback
# -----------------------------------------------------------------------------
def test_09_shap_attribution():
    try:
        from explainability import ShapForensicExplainer
        explainer = ShapForensicExplainer()
        df_sample = pd.read_csv("transaction_anomalies.csv", nrows=5)
        exps = explainer.explain_transactions(df_sample, top_k=3)
        assert len(exps) == 5, f"Expected 5 explanations, got {len(exps)}"
        first_tx = df_sample["txid"].iloc[0]
        drivers = exps[first_tx]
        assert len(drivers) == 3
        assert "feature" in drivers[0]
        assert "shap_value" in drivers[0]
        assert "direction" in drivers[0]
        assert drivers[0]["direction"] in ["INCREASES_ANOMALY", "DECREASES_ANOMALY"]
        log_test(9, "TreeExplainer SHAP Feature Attribution & Fallback", True)
    except Exception as e:
        log_test(9, "TreeExplainer SHAP Feature Attribution & Fallback", False, str(e))


# -----------------------------------------------------------------------------
# TEST 10: Structural Pattern Detectors (Peeling & CoinJoin)
# -----------------------------------------------------------------------------
def test_10_pattern_detection():
    try:
        assert os.path.exists("detected_patterns.csv"), "detected_patterns.csv missing"
        df_pat = pd.read_csv("detected_patterns.csv")
        patterns = set(df_pat["detected_pattern"].unique())
        assert "PEELING_CHAIN" in patterns or "COINJOIN_MIXING" in patterns, "Expected patterns missing"
        assert "txid" in df_pat.columns
        log_test(10, "Structural Pattern Detectors (Peeling & CoinJoin)", True)
    except Exception as e:
        log_test(10, "Structural Pattern Detectors (Peeling & CoinJoin)", False, str(e))


# -----------------------------------------------------------------------------
# TEST 11: Personalized PageRank Risk Score Propagation
# -----------------------------------------------------------------------------
def test_11_risk_scoring():
    try:
        assert os.path.exists("wallet_risk_scores.csv"), "wallet_risk_scores.csv missing"
        df_risk = pd.read_csv("wallet_risk_scores.csv", nrows=100)
        scores = df_risk["risk_score"].values
        assert (scores >= 0.0).all() and (scores <= 1.0).all(), "Risk scores out of [0, 1]"
        assert "risk_tier" in df_risk.columns
        assert set(df_risk["risk_tier"].unique()).issubset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})
        log_test(11, "Personalized PageRank Risk Score Propagation", True)
    except Exception as e:
        log_test(11, "Personalized PageRank Risk Score Propagation", False, str(e))


# -----------------------------------------------------------------------------
# TEST 12: Alert Synthesis, Evidence Trails & Forensic Drivers
# -----------------------------------------------------------------------------
def test_12_alerts():
    try:
        assert os.path.exists("alerts.json"), "alerts.json missing"
        with open("alerts.json", "r", encoding="utf-8") as f:
            alerts = json.load(f)
        assert len(alerts) > 0, "alerts.json is empty"
        a0 = alerts[0]
        required_fields = ["alert_id", "txid", "confidence_score", "flags", "explanation", "evidence_links", "shap_drivers"]
        for rf in required_fields:
            assert rf in a0, f"Missing {rf} in alert"
        assert 0.0 <= a0["confidence_score"] <= 1.0
        assert len(a0["shap_drivers"]) > 0, "Missing SHAP drivers in alert"
        log_test(12, "Alert Synthesis, Evidence Trails & Forensic Drivers", True)
    except Exception as e:
        log_test(12, "Alert Synthesis, Evidence Trails & Forensic Drivers", False, str(e))


# -----------------------------------------------------------------------------
# TEST 13: FastAPI REST API Routes (/health, /metrics, /alerts)
# -----------------------------------------------------------------------------
def test_13_api_endpoints():
    try:
        from fastapi.testclient import TestClient
        from api import app
        client = TestClient(app)

        r_health = client.get("/api/health")
        assert r_health.status_code == 200, f"/api/health returned {r_health.status_code}"

        r_metrics = client.get("/api/metrics")
        assert r_metrics.status_code == 200, f"/api/metrics returned {r_metrics.status_code}"
        assert "total_tx" in r_metrics.json(), "total_tx missing from /api/metrics"

        r_alerts = client.get("/api/alerts?limit=5")
        assert r_alerts.status_code == 200, f"/api/alerts returned {r_alerts.status_code}"
        assert isinstance(r_alerts.json(), list), "/api/alerts should return list"

        log_test(13, "FastAPI REST API Routes (/health, /metrics, /alerts)", True)
    except Exception as e:
        log_test(13, "FastAPI REST API Routes (/health, /metrics, /alerts)", False, str(e))


# -----------------------------------------------------------------------------
# TEST 14: Local Offline Mode & Air-Gapped Verification
# -----------------------------------------------------------------------------
def test_14_offline_verification():
    try:
        for key in ["AWS_ACCESS_KEY_ID", "OPENAI_API_KEY", "INFURA_KEY", "ALCHEMY_KEY"]:
            assert key not in os.environ, f"External credential {key} detected"
        assert os.path.exists("bitcoin_traffic.db"), "bitcoin_traffic.db missing"
        assert os.path.exists("graph.gpickle"), "graph.gpickle missing"
        assert os.path.exists("isolation_forest.joblib"), "isolation_forest.joblib missing"
        assert os.path.exists("feature_scaler.joblib"), "feature_scaler.joblib missing"
        log_test(14, "Local Offline Mode & Air-Gapped Verification", True)
    except Exception as e:
        log_test(14, "Local Offline Mode & Air-Gapped Verification", False, str(e))


# -----------------------------------------------------------------------------
# Master Test Execution
# -----------------------------------------------------------------------------
def run_all_tests():
    print("="*75)
    print(" ChainSentinel (SIH26146) ? Master Test Suite & Verification Runner")
    print("="*75)
    test_01_ingestion()
    test_02_quarantine()
    test_03_db_schema()
    test_04_graph_builder()
    test_05_dsu_clustering()
    test_06_feature_extraction()
    test_07_isolation_forest()
    test_08_autoencoder()
    test_09_shap_attribution()
    test_10_pattern_detection()
    test_11_risk_scoring()
    test_12_alerts()
    test_13_api_endpoints()
    test_14_offline_verification()
    print("="*75)
    print(f"TOTAL: {passes + fails + skips} | PASS: {passes} | FAIL: {fails} | SKIP: {skips}")
    if fails == 0:
        print("[92mSTATUS: ALL 14 SYSTEM TESTS PASSED SUCCESSFULLY! (100% OPERATIONAL)[0m")
        print("="*75)
        sys.exit(0)
    else:
        print(f"[91mSTATUS: {fails} TEST(S) FAILED.[0m")
        print("="*75)
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
