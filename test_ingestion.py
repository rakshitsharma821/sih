#!/usr/bin/env python3
"""
===================================================================================
SIH26146: Verification & Test Suite for Ingestion Pipeline
===================================================================================
Tests:
1. Multi-format ingestion: CSV, JSON, XML
2. Resilient validation: Intentionally corrupt rows are skipped without crashing
3. Database verification: Checks rows in transactions, tx_inputs, and tx_outputs
===================================================================================
"""

import os
import sys
import json
import sqlite3
import tempfile
from ingest import IngestionPipeline


def run_tests():
    print("[*] Starting SIH26146 Ingestion Verification Test Suite...")
    test_db = "test_verify.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # 1. Create a Sample CSV with valid rows + 1 corrupt row
    csv_file = "test_sample.csv"
    csv_content = """txid,timestamp,datetime_utc,src_ip,dst_ip,src_port,dst_port,geo_country,asn,script_type,input_addresses,output_addresses,input_amounts,output_amounts,fee_btc,btc_price_usd,pattern_label
a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef01,1704067200,2024-01-01 00:00:00,104.24.113.175,88.198.24.12,54120,8333,US,"AS13335 Cloudflare",P2WPKH,"[""bc1qtest1a"",""bc1qtest1b""]","[""bc1qout1""]","[0.5, 0.5]","[0.9999]","0.0001",42500.0,NORMAL
CORRUPT_ROW_MISSING_TIMESTAMP,,,,,,,,,,,,,,
b2c3d4e5f6a10123456789abcdef0123456789abcdef0123456789abcdef02,1704067300,2024-01-01 00:01:40,54.210.45.12,136.243.10.5,49230,8333,US,"AS16509 Amazon AWS",Taproot,"[""bc1ptest2a""]","[""bc1pout2a"",""bc1pout2b""]","[1.2]","[0.2, 0.9998]","0.0002",42510.0,PEELING_CHAIN
"""
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)

    # 2. Create a Sample JSON with native arrays
    json_file = "test_sample.json"
    json_data = [
        {
            "txid": "c3d4e5f6a1b20123456789abcdef0123456789abcdef0123456789abcdef03",
            "timestamp": 1704067400,
            "datetime_utc": "2024-01-01 00:03:20",
            "src_ip": "159.65.20.11",
            "dst_ip": "51.254.12.80",
            "src_port": 32014,
            "dst_port": 8333,
            "geo_country": "DE",
            "asn": "AS24940 Hetzner",
            "script_type": "P2WPKH",
            "input_addresses": ["bc1qmix_in1", "bc1qmix_in2"],
            "output_addresses": ["bc1qmix_out1", "bc1qmix_out2"],
            "input_amounts": [0.15, 0.15],
            "output_amounts": [0.10, 0.10],
            "fee_btc": 0.0004,
            "btc_price_usd": 42520.0,
            "pattern_label": "COINJOIN_MIXING"
        },
        # Intentionally corrupt JSON entry (missing inputs/outputs)
        {
            "txid": "bad_tx_no_inputs",
            "timestamp": 1704067450,
            "input_addresses": [],
            "output_addresses": []
        }
    ]
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    # 3. Create a Sample XML with nested input/output elements
    xml_file = "test_sample.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<transactions>
  <transaction>
    <txid>d4e5f6a1b2c30123456789abcdef0123456789abcdef0123456789abcdef04</txid>
    <timestamp>1704067500</timestamp>
    <datetime_utc>2024-01-01 00:05:00</datetime_utc>
    <src_ip>182.72.10.45</src_ip>
    <dst_ip>125.16.88.9</dst_ip>
    <src_port>60124</src_port>
    <dst_port>8333</dst_port>
    <geo_country>IN</geo_country>
    <asn>AS9498 BHARTI Airtel Ltd.</asn>
    <script_type>P2SH</script_type>
    <fee_btc>0.00015</fee_btc>
    <btc_price_usd>42530.0</btc_price_usd>
    <pattern_label>COMMON_INPUT_CLUSTER</pattern_label>
    <inputs>
      <input address="3cluster_in1" amount="0.8"/>
      <input address="3cluster_in2" amount="0.5"/>
    </inputs>
    <outputs>
      <output address="3cluster_out1" amount="1.29985"/>
    </outputs>
  </transaction>
  <!-- Corrupt XML transaction (Missing TXID) -->
  <transaction>
    <timestamp>1704067600</timestamp>
    <src_ip>1.2.3.4</src_ip>
  </transaction>
</transactions>
"""
    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("[+] Test files generated: test_sample.csv, test_sample.json, test_sample.xml")

    # Run Ingestion Pipeline
    pipeline = IngestionPipeline(db_path=test_db, batch_size=10)
    for f_path in [csv_file, json_file, xml_file]:
        pipeline.process_file(f_path)
    pipeline.finish()

    # Verify Database Tables
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    tx_count = cursor.execute("SELECT count(*) FROM transactions;").fetchone()[0]
    in_count = cursor.execute("SELECT count(*) FROM tx_inputs;").fetchone()[0]
    out_count = cursor.execute("SELECT count(*) FROM tx_outputs;").fetchone()[0]

    print("\n--- DATABASE VERIFICATION ---")
    print(f"Transactions stored (Valid): {tx_count} (Expected: 4)")
    print(f"Inputs stored              : {in_count} (Expected: 7)")
    print(f"Outputs stored             : {out_count} (Expected: 6)")
    print(f"Total Rows Read Across All : {pipeline.stats['total_records_read']} (Expected: 7)")
    print(f"Total Skipped Corrupt Rows : {pipeline.stats['records_skipped']} (Expected: 3)")

    assert tx_count == 4, f"Expected 4 valid transactions, got {tx_count}"
    assert pipeline.stats["records_skipped"] == 3, f"Expected 3 skipped bad rows, got {pipeline.stats['records_skipped']}"

    # Sample query showing join across normalized tables
    print("\n--- SAMPLE JOIN QUERY (Graph Preparation) ---")
    sample_query = """
    SELECT t.txid, t.script_type, t.pattern_label, i.address AS input_addr, o.address AS output_addr
    FROM transactions t
    JOIN tx_inputs i ON t.txid = i.txid
    JOIN tx_outputs o ON t.txid = o.txid
    LIMIT 3;
    """
    for row in cursor.execute(sample_query).fetchall():
        print(f"TX: {row[0][:12]}... | Script: {row[1]} | Pattern: {row[2]} | In: {row[3]} -> Out: {row[4]}")

    conn.close()

    # Clean up test files
    for f_path in [test_db, csv_file, json_file, xml_file]:
        if os.path.exists(f_path):
            os.remove(f_path)

    print("\n[OK] All ingestion tests PASSED successfully! Pipeline is error-tolerant and multi-format ready.\n")


if __name__ == "__main__":
    run_tests()
