#!/usr/bin/env python3
"""
===================================================================================
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
STEP 2 — MULTI-FORMAT INGESTION & NORMALIZATION PIPELINE
===================================================================================
Supported Formats: CSV, JSON, XML (Auto-detected via file extension / content)
Normalized Schema: UnifiedTransaction
Destination: SQLite3 Relational Database (transactions, tx_inputs, tx_outputs)
Validation: Schema enforcement, type casting, error-tolerant bad-row skipping.
===================================================================================
"""

import os
import sys
import json
import csv
import sqlite3
import argparse
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any, Union, Generator

# Set up logging with console styling
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("IngestPipeline")


# ===================================================================================
# 1. UNIFIED TRANSACTION DATA SCHEMA
# ===================================================================================
@dataclass
class TxInput:
    address: str
    amount_btc: float


@dataclass
class TxOutput:
    address: str
    amount_btc: float


@dataclass
class UnifiedTransaction:
    txid: str
    timestamp: int
    datetime_utc: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    geo_country: str
    asn: str
    script_type: str
    inputs: List[TxInput]
    outputs: List[TxOutput]
    fee_btc: float
    btc_price_usd: float
    volume_usd: float
    fee_usd: float
    pattern_label: str

    @property
    def input_count(self) -> int:
        return len(self.inputs)

    @property
    def output_count(self) -> int:
        return len(self.outputs)

    @property
    def total_input_btc(self) -> float:
        return round(sum(inp.amount_btc for inp in self.inputs), 8)

    @property
    def total_output_btc(self) -> float:
        return round(sum(out.amount_btc for out in self.outputs), 8)


# ===================================================================================
# 2. DATA NORMALIZATION & VALIDATION ENGINE
# ===================================================================================
class NormalizationError(Exception):
    """Custom exception raised when a transaction row violates schema rules."""
    pass


def parse_array_field(val: Any) -> List[Any]:
    """
    Robustly parses an array field whether it is:
    - Already a Python list (from JSON)
    - A JSON-encoded string (e.g. '["1A...", "1B..."]' from CSV)
    - A comma-separated string (e.g. "1A..., 1B...")
    - Single primitive value
    """
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, (int, float)):
        return [val]
    
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return []
        # Check if JSON array string
        if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("(") and val_str.endswith(")")):
            try:
                parsed = json.loads(val_str)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                # If json.loads fails (e.g. single quotes in string), fallback to literal eval or strip
                cleaned = val_str.strip("[]() ")
                parts = [p.strip().strip("'\"") for p in cleaned.split(",") if p.strip()]
                return parts
        # If comma-separated
        if "," in val_str:
            return [p.strip().strip("'\"") for p in val_str.split(",") if p.strip()]
        return [val_str]
    
    return [val]


def normalize_record(raw: Dict[str, Any], row_id: Union[int, str] = "?") -> UnifiedTransaction:
    """
    Validates and normalizes raw dictionary into a UnifiedTransaction instance.
    Raises NormalizationError on missing critical fields or unrecoverable bad types.
    """
    # 1. Validate TXID
    txid = str(raw.get("txid", "")).strip().lower()
    if not txid or len(txid) < 10:
        raise NormalizationError(f"Missing or malformed 'txid': {txid}")

    # 2. Validate Timestamp
    raw_ts = raw.get("timestamp")
    if raw_ts is None:
        raise NormalizationError("Missing required field 'timestamp'")
    try:
        timestamp = int(float(raw_ts))
        if timestamp <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise NormalizationError(f"Invalid timestamp value: {raw_ts}")

    # Datetime string
    dt_utc = raw.get("datetime_utc")
    if not dt_utc:
        try:
            dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            dt_utc = "1970-01-01 00:00:00"

    # 3. Network Metadata
    src_ip = str(raw.get("src_ip", "0.0.0.0")).strip()
    dst_ip = str(raw.get("dst_ip", "0.0.0.0")).strip()
    
    try:
        src_port = int(float(raw.get("src_port", 8333)))
    except (ValueError, TypeError):
        src_port = 8333
        
    try:
        dst_port = int(float(raw.get("dst_port", 8333)))
    except (ValueError, TypeError):
        dst_port = 8333

    geo_country = str(raw.get("geo_country", "UNKNOWN")).strip().upper()
    asn = str(raw.get("asn", "UNKNOWN")).strip()
    script_type = str(raw.get("script_type", "P2WPKH")).strip().upper()

    # 4. Inputs & Outputs (Arrays)
    raw_in_addrs = parse_array_field(raw.get("input_addresses", []))
    raw_in_amts = parse_array_field(raw.get("input_amounts", []))
    raw_out_addrs = parse_array_field(raw.get("output_addresses", []))
    raw_out_amts = parse_array_field(raw.get("output_amounts", []))

    if not raw_in_addrs:
        raise NormalizationError("Transaction has 0 input addresses")
    if not raw_out_addrs:
        raise NormalizationError("Transaction has 0 output addresses")

    # Match inputs
    inputs: List[TxInput] = []
    for idx, addr in enumerate(raw_in_addrs):
        addr_str = str(addr).strip()
        amt = 0.0
        if idx < len(raw_in_amts):
            try:
                amt = float(raw_in_amts[idx])
            except (ValueError, TypeError):
                amt = 0.0
        inputs.append(TxInput(address=addr_str, amount_btc=amt))

    # Match outputs
    outputs: List[TxOutput] = []
    for idx, addr in enumerate(raw_out_addrs):
        addr_str = str(addr).strip()
        amt = 0.0
        if idx < len(raw_out_amts):
            try:
                amt = float(raw_out_amts[idx])
            except (ValueError, TypeError):
                amt = 0.0
        outputs.append(TxOutput(address=addr_str, amount_btc=amt))

    # 5. Financial & Anomaly Metrics
    try:
        fee_btc = max(0.0, float(raw.get("fee_btc", 0.0)))
    except (ValueError, TypeError):
        fee_btc = 0.0

    try:
        btc_price_usd = max(0.0, float(raw.get("btc_price_usd", 60000.0)))
    except (ValueError, TypeError):
        btc_price_usd = 60000.0

    total_out = sum(out.amount_btc for out in outputs)
    try:
        volume_usd = float(raw.get("volume_usd", round(total_out * btc_price_usd, 2)))
    except (ValueError, TypeError):
        volume_usd = round(total_out * btc_price_usd, 2)

    try:
        fee_usd = float(raw.get("fee_usd", round(fee_btc * btc_price_usd, 4)))
    except (ValueError, TypeError):
        fee_usd = round(fee_btc * btc_price_usd, 4)

    pattern_label = str(raw.get("pattern_label", "NORMAL")).strip()

    return UnifiedTransaction(
        txid=txid,
        timestamp=timestamp,
        datetime_utc=dt_utc,
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        geo_country=geo_country,
        asn=asn,
        script_type=script_type,
        inputs=inputs,
        outputs=outputs,
        fee_btc=fee_btc,
        btc_price_usd=btc_price_usd,
        volume_usd=volume_usd,
        fee_usd=fee_usd,
        pattern_label=pattern_label
    )


# ===================================================================================
# 3. FORMAT-SPECIFIC INGESTION PARSERS (CSV, JSON, XML)
# ===================================================================================
class IngestionParser:
    """Parses files across multiple formats yielding raw dictionaries."""

    @staticmethod
    def parse_csv(filepath: str) -> Generator[Dict[str, Any], None, None]:
        """Reads CSV rows as dictionaries."""
        with open(filepath, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row

    @staticmethod
    def parse_json(filepath: str) -> Generator[Dict[str, Any], None, None]:
        """Reads JSON files (supports either a root array of objects or JSON lines)."""
        with open(filepath, mode="r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
            if not content:
                return

            if content.startswith("["):
                # Standard JSON array of objects
                data = json.loads(content)
                for item in data:
                    if isinstance(item, dict):
                        yield item
            else:
                # JSON Lines format (one JSON object per line)
                f.seek(0)
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        try:
                            parsed = json.loads(line_str)
                            if isinstance(parsed, dict):
                                yield parsed
                        except Exception:
                            continue

    @staticmethod
    def parse_xml(filepath: str) -> Generator[Dict[str, Any], None, None]:
        """
        Parses XML transaction feeds.
        Supported Structure:
        <transactions>
          <transaction>
             <txid>...</txid>
             <timestamp>...</timestamp>
             <inputs>
               <input address="..." amount="..."/>
             </inputs>
             <outputs>
               <output address="..." amount="..."/>
             </outputs>
             ...
          </transaction>
        </transactions>
        """
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Look for elements named 'transaction', 'tx', or direct children
        tx_nodes = root.findall(".//transaction") or root.findall(".//tx") or list(root)

        for node in tx_nodes:
            rec: Dict[str, Any] = {}
            for child in node:
                tag = child.tag.lower()
                
                # Nested inputs
                if tag in ("inputs", "input_addresses"):
                    in_addrs = []
                    in_amts = []
                    for in_item in child:
                        addr = in_item.attrib.get("address") or in_item.findtext("address") or in_item.text
                        amt = in_item.attrib.get("amount") or in_item.findtext("amount") or "0.0"
                        if addr:
                            in_addrs.append(addr.strip())
                            in_amts.append(float(amt) if amt else 0.0)
                    rec["input_addresses"] = in_addrs
                    rec["input_amounts"] = in_amts
                
                # Nested outputs
                elif tag in ("outputs", "output_addresses"):
                    out_addrs = []
                    out_amts = []
                    for out_item in child:
                        addr = out_item.attrib.get("address") or out_item.findtext("address") or out_item.text
                        amt = out_item.attrib.get("amount") or out_item.findtext("amount") or "0.0"
                        if addr:
                            out_addrs.append(addr.strip())
                            out_amts.append(float(amt) if amt else 0.0)
                    rec["output_addresses"] = out_addrs
                    rec["output_amounts"] = out_amts
                else:
                    rec[child.tag] = child.text

            # Merge attributes if any exist on the transaction node itself
            for attr_key, attr_val in node.attrib.items():
                if attr_key not in rec:
                    rec[attr_key] = attr_val

            yield rec


# ===================================================================================
# 4. DATABASE MANAGER (SQLite Schema for Step 3 Graph Analysis)
# ===================================================================================
class DatabaseManager:
    """Manages SQLite connection, normalized tables, indexing, and batch inserts."""

    def __init__(self, db_path: str = "bitcoin_traffic.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initializes tables and high-performance indexes."""
        self.conn = sqlite3.connect(self.db_path)
        # Enable Write-Ahead-Logging for high throughput
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self.conn.execute("PRAGMA foreign_keys = ON;")

        with self.conn:
            # 1. Main Transactions table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    txid TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    datetime_utc TEXT,
                    src_ip TEXT,
                    dst_ip TEXT,
                    src_port INTEGER,
                    dst_port INTEGER,
                    geo_country TEXT,
                    asn TEXT,
                    script_type TEXT,
                    input_count INTEGER,
                    output_count INTEGER,
                    total_input_btc REAL,
                    total_output_btc REAL,
                    fee_btc REAL,
                    btc_price_usd REAL,
                    volume_usd REAL,
                    fee_usd REAL,
                    pattern_label TEXT
                );
            """)

            # 2. Relational Transaction Inputs table (For Wallet Clustering & Graph)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tx_inputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txid TEXT NOT NULL,
                    address TEXT NOT NULL,
                    amount_btc REAL,
                    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
                );
            """)

            # 3. Relational Transaction Outputs table (For Flow Tracking & Graph)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tx_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txid TEXT NOT NULL,
                    address TEXT NOT NULL,
                    amount_btc REAL,
                    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
                );
            """)

            # 4. Indexes for fast graph queries in Step 3 & instant foreign key cascading
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_inputs_txid ON tx_inputs(txid);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_outputs_txid ON tx_outputs(txid);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_inputs_addr ON tx_inputs(address);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_outputs_addr ON tx_outputs(address);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_src_ip ON transactions(src_ip);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_pattern ON transactions(pattern_label);")

    def insert_batch(self, batch: List[UnifiedTransaction]):
        """Inserts a normalized batch using atomic transactions with conflict replacement."""
        if not batch:
            return

        tx_rows = []
        input_rows = []
        output_rows = []

        for tx in batch:
            tx_rows.append((
                tx.txid,
                tx.timestamp,
                tx.datetime_utc,
                tx.src_ip,
                tx.dst_ip,
                tx.src_port,
                tx.dst_port,
                tx.geo_country,
                tx.asn,
                tx.script_type,
                tx.input_count,
                tx.output_count,
                tx.total_input_btc,
                tx.total_output_btc,
                tx.fee_btc,
                tx.btc_price_usd,
                tx.volume_usd,
                tx.fee_usd,
                tx.pattern_label
            ))

            for inp in tx.inputs:
                input_rows.append((tx.txid, inp.address, inp.amount_btc))

            for out in tx.outputs:
                output_rows.append((tx.txid, out.address, out.amount_btc))

        with self.conn:
            # Upsert into transactions table
            self.conn.executemany("""
                INSERT OR REPLACE INTO transactions (
                    txid, timestamp, datetime_utc, src_ip, dst_ip, src_port, dst_port,
                    geo_country, asn, script_type, input_count, output_count,
                    total_input_btc, total_output_btc, fee_btc, btc_price_usd,
                    volume_usd, fee_usd, pattern_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, tx_rows)

            # Insert inputs & outputs
            self.conn.executemany("""
                INSERT INTO tx_inputs (txid, address, amount_btc) VALUES (?, ?, ?);
            """, input_rows)

            self.conn.executemany("""
                INSERT INTO tx_outputs (txid, address, amount_btc) VALUES (?, ?, ?);
            """, output_rows)

    def close(self):
        if self.conn:
            self.conn.close()


# ===================================================================================
# 5. PIPELINE CONTROLLER
# ===================================================================================
class IngestionPipeline:
    """Orchestrates format detection, parsing, validation, and database ingestion."""

    def __init__(self, db_path: str = "bitcoin_traffic.db", batch_size: int = 1000):
        self.db = DatabaseManager(db_path)
        self.batch_size = batch_size
        self.stats = {
            "files_processed": 0,
            "total_records_read": 0,
            "records_normalized": 0,
            "records_skipped": 0,
            "errors": []
        }

    def detect_format(self, filepath: str) -> str:
        """Determines format via extension with content sniffing fallback."""
        _, ext = os.path.splitext(filepath)
        ext = ext.lower().lstrip(".")
        if ext in ("csv", "json", "xml"):
            return ext

        # Sniff content
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(512).strip()
                if head.startswith("<"):
                    return "xml"
                if head.startswith("[") or head.startswith("{"):
                    return "json"
                if "," in head:
                    return "csv"
        except Exception:
            pass
        return "csv"

    def process_file(self, filepath: str) -> Dict[str, Any]:
        """Ingests a single file."""
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return self.stats

        fmt = self.detect_format(filepath)
        logger.info(f"==> Ingesting '{os.path.basename(filepath)}' [Detected Format: {fmt.upper()}]")

        if fmt == "csv":
            record_gen = IngestionParser.parse_csv(filepath)
        elif fmt == "json":
            record_gen = IngestionParser.parse_json(filepath)
        elif fmt == "xml":
            record_gen = IngestionParser.parse_xml(filepath)
        else:
            logger.error(f"Unsupported format '{fmt}' for file: {filepath}")
            return self.stats

        batch: List[UnifiedTransaction] = []
        file_read = 0
        file_valid = 0
        file_skipped = 0

        for row_idx, raw_rec in enumerate(record_gen, start=1):
            file_read += 1
            self.stats["total_records_read"] += 1
            try:
                normalized = normalize_record(raw_rec, row_id=row_idx)
                batch.append(normalized)
                file_valid += 1
                self.stats["records_normalized"] += 1

                if len(batch) >= self.batch_size:
                    self.db.insert_batch(batch)
                    batch.clear()

            except NormalizationError as ne:
                file_skipped += 1
                self.stats["records_skipped"] += 1
                err_msg = f"Row {row_idx} skipped in {os.path.basename(filepath)}: {ne}"
                self.stats["errors"].append(err_msg)
                if len(self.stats["errors"]) <= 10:
                    logger.warning(err_msg)
            except Exception as ex:
                file_skipped += 1
                self.stats["records_skipped"] += 1
                err_msg = f"Row {row_idx} unexpected error in {os.path.basename(filepath)}: {ex}"
                self.stats["errors"].append(err_msg)
                if len(self.stats["errors"]) <= 10:
                    logger.error(err_msg)

        # Flush remaining batch
        if batch:
            self.db.insert_batch(batch)
            batch.clear()

        self.stats["files_processed"] += 1
        logger.info(f"    Completed '{os.path.basename(filepath)}': Read={file_read:,}, Ingested={file_valid:,}, Skipped={file_skipped:,}")
        return self.stats

    def finish(self):
        self.db.close()


# ===================================================================================
# 6. CLI ENTRY POINT
# ===================================================================================
def main():
    parser = argparse.ArgumentParser(
        description="SIH26146: Multi-format Bitcoin Traffic Ingestion Pipeline"
    )
    parser.add_argument(
        "--input", nargs="+", required=True,
        help="One or more input files to ingest (.csv, .json, .xml)"
    )
    parser.add_argument(
        "--db", type=str, default="bitcoin_traffic.db",
        help="Path to target SQLite database (default: bitcoin_traffic.db)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Batch size for database inserts (default: 1000)"
    )

    args = parser.parse_args()

    pipeline = IngestionPipeline(db_path=args.db, batch_size=args.batch_size)

    start_time = datetime.now()
    logger.info(f"Starting ingestion into SQLite database: {args.db}")

    for file_path in args.input:
        pipeline.process_file(file_path)

    pipeline.finish()
    duration = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("INGESTION PIPELINE SUMMARY REPORT")
    print("=" * 60)
    print(f"Files Processed        : {pipeline.stats['files_processed']}")
    print(f"Total Rows Read        : {pipeline.stats['total_records_read']:,}")
    print(f"Normalized & Inserted  : {pipeline.stats['records_normalized']:,}")
    print(f"Skipped Corrupt Rows   : {pipeline.stats['records_skipped']:,}")
    print(f"Time Taken             : {duration:.2f} seconds")
    print(f"Target Database        : {os.path.abspath(args.db)}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
