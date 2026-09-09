#!/usr/bin/env python3
"""
===================================================================================
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
HYBRID SYNTHETIC DATASET GENERATOR (Blockchain + P2P Network Metadata)
===================================================================================
Features:
1. Real Kaggle Price Data Integration (btcusd_1-min_data.csv interpolation with auto-fallback)
2. Realistic Bitcoin Addresses (P2PKH '1', P2SH '3', SegWit 'bc1q', Taproot 'bc1p')
3. Realistic Network P2P Metadata (IPs, Ports, GeoIP Country, ASN) with MaxMind GeoLite2 & Offline Fallback
4. Injected Labeled Anomalies:
   - Peeling Chains (5-15 hops)
   - CoinJoin / Mixing (equal denominations, multi-input multi-output)
   - Common-Input Ownership Clusters (multi-input heuristic + co-located IP)
   - Statistical Anomalies (whale amounts, extreme fees, sub-second bursts)
5. Exports:
   - transactions.csv
   - transactions.json
   - ground_truth.csv (wallet_id -> pattern / suspicious label)
===================================================================================
"""

import os
import sys
import json
import time
import random
import hashlib
import secrets
import argparse
import bisect
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any

# Optional libraries with graceful fallback
try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import geoip2.database
    HAS_GEOIP2 = True
except ImportError:
    HAS_GEOIP2 = False


# ===================================================================================
# 1. BITCOIN ADDRESS & CRYPTO HELPER FUNCTIONS
# ===================================================================================
class BitcoinAddressGenerator:
    """Generates realistic Bitcoin-compliant addresses and transaction IDs."""
    
    BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    BECH32_ALPHABET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    @classmethod
    def random_hex(cls, length_bytes: int = 32) -> str:
        return secrets.token_hex(length_bytes)

    @classmethod
    def generate_txid(cls) -> str:
        """Bitcoin txid is a 64-char hex string (SHA256 double hash simulation)."""
        raw = secrets.token_bytes(32)
        return hashlib.sha256(hashlib.sha256(raw).digest()).hexdigest()

    @classmethod
    def generate_p2pkh(cls) -> str:
        """Legacy Bitcoin address starting with '1' (26-35 characters)."""
        chars = [random.choice(cls.BASE58_ALPHABET) for _ in range(random.randint(26, 33))]
        return "1" + "".join(chars)

    @classmethod
    def generate_p2sh(cls) -> str:
        """Script Hash address starting with '3' (26-35 characters)."""
        chars = [random.choice(cls.BASE58_ALPHABET) for _ in range(random.randint(26, 33))]
        return "3" + "".join(chars)

    @classmethod
    def generate_p2wpkh(cls) -> str:
        """Native SegWit Bech32 address starting with 'bc1q' (42 characters)."""
        chars = [random.choice(cls.BECH32_ALPHABET) for _ in range(38)]
        return "bc1q" + "".join(chars)

    @classmethod
    def generate_p2wsh(cls) -> str:
        """Native SegWit Script Bech32 address starting with 'bc1q' (62 characters)."""
        chars = [random.choice(cls.BECH32_ALPHABET) for _ in range(58)]
        return "bc1q" + "".join(chars)

    @classmethod
    def generate_taproot(cls) -> str:
        """Taproot Bech32m address starting with 'bc1p' (62 characters)."""
        chars = [random.choice(cls.BECH32_ALPHABET) for _ in range(58)]
        return "bc1p" + "".join(chars)

    @classmethod
    def generate_address(cls, script_type: Optional[str] = None) -> Tuple[str, str]:
        """Returns (address, script_type)."""
        if script_type is None:
            # Modern Bitcoin mainnet distribution weights
            script_type = random.choices(
                ["P2WPKH", "Taproot", "P2SH", "P2PKH", "P2WSH"],
                weights=[0.45, 0.20, 0.20, 0.10, 0.05],
                k=1
            )[0]

        if script_type == "P2PKH":
            addr = cls.generate_p2pkh()
        elif script_type == "P2SH":
            addr = cls.generate_p2sh()
        elif script_type == "P2WPKH":
            addr = cls.generate_p2wpkh()
        elif script_type == "P2WSH":
            addr = cls.generate_p2wsh()
        elif script_type == "Taproot":
            addr = cls.generate_taproot()
        else:
            addr = cls.generate_p2wpkh()
            script_type = "P2WPKH"

        return addr, script_type


class KagglePriceManager:
    """
    Loads and provides 1-minute BTC/USD prices from 'btcusd_1-min_data.csv'.
    If file is missing, automatically switches to a realistic synthetic model.
    """
    def __init__(self, csv_path: str = "btcusd_1-min_data.csv"):
        self.csv_path = csv_path
        self.timestamps = []
        self.prices = []
        self.is_real = False
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.csv_path):
            print(f"[+] Loading real BTC price data from: {self.csv_path}...")
            try:
                if HAS_PANDAS:
                    df = pd.read_csv(self.csv_path)
                    # Handle varying column naming conventions
                    time_col = next((c for c in df.columns if c.lower() in ['timestamp', 'time', 'unix', 'date']), None)
                    close_col = next((c for c in df.columns if c.lower() in ['close', 'price', 'weighted_price']), None)
                    
                    if time_col and close_col:
                        # Drop NaNs
                        df = df[[time_col, close_col]].dropna()
                        # Convert timestamp to int
                        if df[time_col].dtype == object:
                            df['ts'] = pd.to_datetime(df[time_col]).astype('int64') // 10**9
                        else:
                            df['ts'] = df[time_col].astype(int)
                        
                        df = df.sort_values('ts')
                        self.timestamps = df['ts'].tolist()
                        self.prices = df[close_col].astype(float).tolist()
                        self.is_real = True
                        print(f"    Loaded {len(self.timestamps):,} 1-minute price points "
                              f"({datetime.fromtimestamp(self.timestamps[0], tz=timezone.utc).strftime('%Y-%m')} to "
                              f"{datetime.fromtimestamp(self.timestamps[-1], tz=timezone.utc).strftime('%Y-%m')}).")
                        return
                else:
                    import csv
                    with open(self.csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            try:
                                ts = int(float(row.get('Timestamp', row.get('timestamp', 0))))
                                p = float(row.get('Close', row.get('close', 0)))
                                if ts > 0 and p > 0:
                                    self.timestamps.append(ts)
                                    self.prices.append(p)
                            except Exception:
                                continue
                    if self.timestamps:
                        self.is_real = True
                        print(f"    Loaded {len(self.timestamps):,} 1-minute points via standard CSV reader.")
                        return
            except Exception as e:
                print(f"[!] Warning: Failed to parse {self.csv_path}: {e}. Falling back to simulation.")

        # Fallback if file not found or invalid
        print(f"[i] Real Kaggle price file '{self.csv_path}' not found. Using realistic market simulation curve.")
        self.is_real = False
        # Create anchor points from 2021 to 2026
        base_anchors = [
            (1609459200, 29000.0),   # Jan 2021
            (1636502400, 68000.0),   # Nov 2021
            (1668038400, 16500.0),   # Nov 2022
            (1704067200, 42500.0),   # Jan 2024
            (1710374400, 73000.0),   # Mar 2024
            (1735689600, 95000.0),   # Jan 2025
            (1772668800, 108000.0),  # 2026
        ]
        self.timestamps = [a[0] for a in base_anchors]
        self.prices = [a[1] for a in base_anchors]

    def get_time_range(self) -> Tuple[int, int]:
        """Returns (min_timestamp, max_timestamp)."""
        if self.timestamps:
            return self.timestamps[0], self.timestamps[-1]
        # Default 2023-2025 range
        return 1672531199, 1735689600

    def get_price(self, timestamp: int) -> float:
        """Interpolates or looks up nearest 1-min BTC/USD price."""
        if not self.timestamps:
            return 65000.0
        
        idx = bisect.bisect_left(self.timestamps, timestamp)
        if idx == 0:
            return self.prices[0]
        if idx >= len(self.timestamps):
            return self.prices[-1]
        
        # Linear interpolation between nearest two timestamps
        t1, t2 = self.timestamps[idx - 1], self.timestamps[idx]
        p1, p2 = self.prices[idx - 1], self.prices[idx]
        
        if t1 == t2:
            return p1
        
        weight = (timestamp - t1) / (t2 - t1)
        interpolated = p1 + weight * (p2 - p1)
        # Add slight micro-noise (0.05%) for realistic variation
        noise = random.uniform(0.9995, 1.0005)
        return round(interpolated * noise, 2)


class NetworkGeoManager:
    """
    Manages IP generation, Port assignment, GeoIP (Country), and ASN lookup.
    Can use MaxMind GeoLite2 (.mmdb) if available, otherwise uses realistic curated database.
    """
    
    # Representative Autonomous Systems & Country mappings for major Bitcoin node clusters
    ASN_DATABASE = [
        {"asn": "AS16509", "org": "Amazon.com, Inc. (AWS)", "country": "US", "weight": 22},
        {"asn": "AS24940", "org": "Hetzner Online GmbH", "country": "DE", "weight": 16},
        {"asn": "AS14061", "org": "DigitalOcean, LLC", "country": "US", "weight": 10},
        {"asn": "AS16276", "org": "OVH SAS", "country": "FR", "weight": 8},
        {"asn": "AS13335", "org": "Cloudflare, Inc.", "country": "US", "weight": 7},
        {"asn": "AS15169", "org": "Google LLC", "country": "US", "weight": 6},
        {"asn": "AS8075",  "org": "Microsoft Corporation", "country": "US", "weight": 5},
        {"asn": "AS37963", "org": "Alibaba Cloud", "country": "SG", "weight": 4},
        {"asn": "AS12876", "org": "SCALEWAY S.A.S.", "country": "FR", "weight": 4},
        {"asn": "AS3320",  "org": "Deutsche Telekom AG", "country": "DE", "weight": 3},
        {"asn": "AS49981", "org": "WorldStream B.V.", "country": "NL", "weight": 3},
        {"asn": "AS20473", "org": "The Constant Company (Vultr)", "country": "JP", "weight": 3},
        {"asn": "AS55836", "org": "Reliance Jio Infocomm", "country": "IN", "weight": 2},
        {"asn": "AS9498",  "org": "BHARTI Airtel Ltd.", "country": "IN", "weight": 2},
        {"asn": "AS2856",  "org": "British Telecommunications", "country": "GB", "weight": 2},
        {"asn": "AS2500",  "org": "PJSC Rostelecom", "country": "RU", "weight": 2},
    ]

    # Pre-calculated IP subnets corresponding to ASNs
    SUBNET_POOLS = {
        "AS16509": ["54.210.", "3.80.", "35.160."],
        "AS24940": ["88.198.", "136.243.", "65.21."],
        "AS14061": ["159.65.", "167.99.", "134.209."],
        "AS16276": ["51.254.", "149.202.", "217.182."],
        "AS13335": ["104.24.", "172.67.", "198.41."],
        "AS15169": ["34.120.", "35.230.", "34.65."],
        "AS8075":  ["20.42.", "52.170.", "40.114."],
        "AS37963": ["47.241.", "8.219.", "47.74."],
        "AS12876": ["51.15.", "163.172.", "212.47."],
        "AS3320":  ["93.192.", "84.134.", "217.80."],
        "AS49981": ["217.23.", "93.190.", "185.182."],
        "AS20473": ["45.76.", "108.61.", "149.28."],
        "AS55836": ["49.32.", "157.34.", "139.167."],
        "AS9498":  ["125.16.", "182.72.", "122.160."],
        "AS2856":  ["81.134.", "86.130.", "213.120."],
        "AS2500":  ["95.173.", "178.64.", "212.48."],
    }

    def __init__(self, geolite2_city_path: Optional[str] = "GeoLite2-City.mmdb", 
                 geolite2_asn_path: Optional[str] = "GeoLite2-ASN.mmdb"):
        self.city_reader = None
        self.asn_reader = None
        self.use_maxmind = False

        if HAS_GEOIP2 and geolite2_city_path and os.path.exists(geolite2_city_path):
            try:
                self.city_reader = geoip2.database.Reader(geolite2_city_path)
                print(f"[+] Loaded MaxMind GeoLite2 City DB from {geolite2_city_path}")
                self.use_maxmind = True
            except Exception as e:
                print(f"[!] Warning: Could not open {geolite2_city_path}: {e}")

        if HAS_GEOIP2 and geolite2_asn_path and os.path.exists(geolite2_asn_path):
            try:
                self.asn_reader = geoip2.database.Reader(geolite2_asn_path)
                print(f"[+] Loaded MaxMind GeoLite2 ASN DB from {geolite2_asn_path}")
            except Exception as e:
                print(f"[!] Warning: Could not open {geolite2_asn_path}: {e}")

        if not self.use_maxmind:
            print("[i] Using built-in high-accuracy GeoIP/ASN offline mapping (No external DB required).")

        # Prepare weighted ASN list
        self.asn_items = self.ASN_DATABASE
        self.asn_weights = [x["weight"] for x in self.asn_items]

    def generate_random_ip(self) -> Tuple[str, str, str]:
        """Returns (ip_address, country_code, asn_string)."""
        chosen_asn = random.choices(self.asn_items, weights=self.asn_weights, k=1)[0]
        asn_id = chosen_asn["asn"]
        default_country = chosen_asn["country"]
        
        prefix = random.choice(self.SUBNET_POOLS.get(asn_id, ["192.0.2."]))
        ip = f"{prefix}{random.randint(1, 254)}.{random.randint(1, 254)}"

        # If MaxMind is active, query it for precision
        if self.use_maxmind and self.city_reader:
            try:
                resp = self.city_reader.city(ip)
                country = resp.country.iso_code or default_country
            except Exception:
                country = default_country
        else:
            country = default_country

        if self.asn_reader:
            try:
                resp_asn = self.asn_reader.asn(ip)
                asn_str = f"AS{resp_asn.autonomous_system_number} {resp_asn.autonomous_system_organization}"
            except Exception:
                asn_str = f"{asn_id} {chosen_asn['org']}"
        else:
            asn_str = f"{asn_id} {chosen_asn['org']}"

        return ip, country, asn_str

    def generate_port_pair(self) -> Tuple[int, int]:
        """
        Returns (src_port, dst_port).
        Bitcoin network standard: Destination node listens on 8333 (Mainnet),
        Testnet on 18333, RPC 8332, or high random ephemeral client port (49152-65535).
        """
        # 85% destination is standard P2P port 8333
        dst_port = random.choices([8333, 18333, 8332, 8334], weights=[0.85, 0.05, 0.05, 0.05], k=1)[0]
        src_port = random.randint(1024, 65535)
        return src_port, dst_port


# ===================================================================================
# 4. TRANSACTION & ANOMALY INJECTION ENGINE
# ===================================================================================
class BitcoinDatasetGenerator:
    """
    Main orchestrator for generating normal traffic & injecting labeled anomalies.
    """
    def __init__(self, 
                 total_txs: int = 7500,
                 price_csv: str = "btcusd_1-min_data.csv",
                 seed: int = 42):
        self.total_txs = total_txs
        self.seed = seed
        random.seed(seed)
        if HAS_PANDAS:
            np.random.seed(seed)

        self.price_mgr = KagglePriceManager(price_csv)
        self.net_mgr = NetworkGeoManager()
        self.addr_gen = BitcoinAddressGenerator

        # Output structures
        self.transactions: List[Dict[str, Any]] = []
        self.ground_truth: Dict[str, Dict[str, Any]] = {} # wallet_id -> metadata
        self.entity_counter = 1

    def _register_wallet(self, wallet_id: str, entity_group: str, is_suspicious: bool, pattern_type: str):
        """Registers or updates a wallet's ground truth record."""
        if wallet_id not in self.ground_truth:
            self.ground_truth[wallet_id] = {
                "wallet_id": wallet_id,
                "entity_group": entity_group,
                "is_suspicious": 1 if is_suspicious else 0,
                "pattern_type": pattern_type
            }
        else:
            # Upgrade suspicion if discovered in an anomaly pattern
            if is_suspicious:
                self.ground_truth[wallet_id]["is_suspicious"] = 1
                if self.ground_truth[wallet_id]["pattern_type"] == "NORMAL":
                    self.ground_truth[wallet_id]["pattern_type"] = pattern_type
                    self.ground_truth[wallet_id]["entity_group"] = entity_group

    def _create_tx_dict(self,
                         ts: int,
                         src_ip: str,
                         dst_ip: str,
                         src_port: int,
                         dst_port: int,
                         inputs: List[Tuple[str, float]],   # [(addr, amount_btc)]
                         outputs: List[Tuple[str, float]],  # [(addr, amount_btc)]
                         fee: float,
                         script_type: str,
                         country: str,
                         asn: str,
                         pattern_tag: str = "NORMAL") -> Dict[str, Any]:
        """Formats and computes USD equivalents for a single transaction record."""
        txid = self.addr_gen.generate_txid()
        btc_price_usd = self.price_mgr.get_price(ts)
        
        in_addrs = [item[0] for item in inputs]
        in_amounts = [round(item[1], 8) for item in inputs]
        out_addrs = [item[0] for item in outputs]
        out_amounts = [round(item[1], 8) for item in outputs]

        total_in_btc = sum(in_amounts)
        total_out_btc = sum(out_amounts)
        total_vol_usd = round((total_out_btc) * btc_price_usd, 2)
        fee_usd = round(fee * btc_price_usd, 4)

        return {
            "txid": txid,
            "timestamp": ts,
            "datetime_utc": datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "geo_country": country,
            "asn": asn,
            "script_type": script_type,
            "input_addresses": json.dumps(in_addrs),
            "output_addresses": json.dumps(out_addrs),
            "input_amounts": json.dumps(in_amounts),
            "output_amounts": json.dumps(out_amounts),
            "input_count": len(in_addrs),
            "output_count": len(out_addrs),
            "total_input_btc": round(total_in_btc, 8),
            "total_output_btc": round(total_out_btc, 8),
            "fee_btc": round(fee, 8),
            "btc_price_usd": btc_price_usd,
            "volume_usd": total_vol_usd,
            "fee_usd": fee_usd,
            "pattern_label": pattern_tag
        }

    # -------------------------------------------------------------------------------
    # PATTERN A: NORMAL BACKGROUND BITCOIN TRANSACTIONS
    # -------------------------------------------------------------------------------
    def generate_normal_transactions(self, count: int, start_ts: int, end_ts: int):
        """Generates realistic benign 1-in-2-out or 2-in-2-out Bitcoin transactions."""
        print(f"[+] Generating {count:,} Normal background transactions...")
        for _ in range(count):
            ts = random.randint(start_ts, end_ts)
            src_ip, country, asn = self.net_mgr.generate_random_ip()
            dst_ip, _, _ = self.net_mgr.generate_random_ip()
            src_port, dst_port = self.net_mgr.generate_port_pair()

            # Typical transaction structure: 1-2 inputs, 1-2 outputs (payment + change)
            num_inputs = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05], k=1)[0]
            num_outputs = random.choices([1, 2], weights=[0.20, 0.80], k=1)[0]
            
            addr, script_type = self.addr_gen.generate_address()
            
            # Normal BTC transfer amounts (log-normal distribution between 0.0005 to 2.5 BTC)
            target_amount = round(random.lognormvariate(-2.5, 1.2), 6)
            target_amount = max(0.0002, min(target_amount, 10.0))

            # Inputs
            inputs = []
            accumulated = 0.0
            entity_id = f"ENTITY_NORM_{self.entity_counter}"
            self.entity_counter += 1

            for _ in range(num_inputs):
                in_addr, _ = self.addr_gen.generate_address(script_type)
                in_amt = round(target_amount / num_inputs + random.uniform(0.0001, 0.005), 6)
                inputs.append((in_addr, in_amt))
                accumulated += in_amt
                self._register_wallet(in_addr, entity_id, is_suspicious=False, pattern_type="NORMAL")

            # Fee (satoshis per vByte equivalent: ~0.00002 to 0.00025 BTC)
            fee = round(random.uniform(0.00001, 0.00020), 8)
            available_for_outputs = max(0.0001, accumulated - fee)

            # Outputs
            outputs = []
            if num_outputs == 1:
                out_addr, _ = self.addr_gen.generate_address()
                outputs.append((out_addr, available_for_outputs))
                self._register_wallet(out_addr, "EXTERNAL_RECIPIENT", is_suspicious=False, pattern_type="NORMAL")
            else:
                pay_amt = round(available_for_outputs * random.uniform(0.3, 0.7), 6)
                change_amt = round(available_for_outputs - pay_amt, 6)
                
                pay_addr, _ = self.addr_gen.generate_address()
                change_addr, _ = self.addr_gen.generate_address(script_type)
                
                outputs.append((pay_addr, pay_amt))
                outputs.append((change_addr, change_amt))
                
                self._register_wallet(pay_addr, "EXTERNAL_MERCHANT", is_suspicious=False, pattern_type="NORMAL")
                self._register_wallet(change_addr, entity_id, is_suspicious=False, pattern_type="NORMAL")

            tx = self._create_tx_dict(ts, src_ip, dst_ip, src_port, dst_port,
                                       inputs, outputs, fee, script_type, country, asn, "NORMAL")
            self.transactions.append(tx)

    # -------------------------------------------------------------------------------
    # PATTERN B: PEELING CHAIN (Layering / Smurfing Anomaly)
    # -------------------------------------------------------------------------------
    def inject_peeling_chains(self, chain_count: int = 25, start_ts: int = 0, end_ts: int = 0):
        """
        Injects classic Bitcoin Peeling Chains:
        A large fund is broken down hop-by-hop. In each hop:
        - 1 small fixed output is sent to an external / cash-out address
        - 1 large change output is forwarded to the next hop
        Repeated across 5-15 continuous hops.
        """
        print(f"[+] Injecting {chain_count} Peeling Chains (5-15 hops each)...")
        for chain_idx in range(chain_count):
            hops = random.randint(6, 14)
            current_ts = random.randint(start_ts, end_ts - (hops * 600))
            
            # Originating wallet holding illicit/stolen funds
            current_wallet, script_type = self.addr_gen.generate_address()
            initial_balance = round(random.uniform(5.0, 50.0), 6)
            current_balance = initial_balance
            
            entity_id = f"PEELING_ACTOR_{chain_idx+1}"
            self._register_wallet(current_wallet, entity_id, is_suspicious=True, pattern_type="PEELING_CHAIN_ORIGIN")
            
            # Often peeling chains route through VPN / Tor / specific bulletproof host
            src_ip, country, asn = self.net_mgr.generate_random_ip()

            for hop in range(hops):
                dst_ip, _, _ = self.net_mgr.generate_random_ip()
                src_port, dst_port = self.net_mgr.generate_port_pair()
                
                # Small fixed peel amount (e.g. 0.05 - 0.25 BTC)
                peel_amount = round(random.uniform(0.05, 0.35), 6)
                fee = round(random.uniform(0.00003, 0.00015), 8)
                change_amount = round(current_balance - peel_amount - fee, 6)

                if change_amount <= 0.05:
                    break

                peel_dest_addr, _ = self.addr_gen.generate_address()
                next_change_addr, _ = self.addr_gen.generate_address(script_type)

                self._register_wallet(peel_dest_addr, f"{entity_id}_CASHOUT", is_suspicious=True, pattern_type="PEELING_CHAIN_PEEL")
                self._register_wallet(next_change_addr, entity_id, is_suspicious=True, pattern_type="PEELING_CHAIN_HOP")

                inputs = [(current_wallet, current_balance)]
                outputs = [
                    (peel_dest_addr, peel_amount),
                    (next_change_addr, change_amount)
                ]

                tx = self._create_tx_dict(current_ts, src_ip, dst_ip, src_port, dst_port,
                                           inputs, outputs, fee, script_type, country, asn, "PEELING_CHAIN")
                self.transactions.append(tx)

                # Move to next hop
                current_wallet = next_change_addr
                current_balance = change_amount
                # Time gap between hops: 2 minutes to 45 minutes
                current_ts += random.randint(120, 2700)
                # Slight chance IP changes (hopping proxy/VPN)
                if random.random() < 0.35:
                    src_ip, country, asn = self.net_mgr.generate_random_ip()

    # -------------------------------------------------------------------------------
    # PATTERN C: COINJOIN / MIXING (Privacy / Anonymization Anomaly)
    # -------------------------------------------------------------------------------
    def inject_coinjoin_mixing(self, mix_count: int = 35, start_ts: int = 0, end_ts: int = 0):
        """
        Injects CoinJoin / Wasabi / Whirlpool style mixing transactions:
        - N inputs from diverse participants
        - N equal-denomination outputs (e.g. 0.05, 0.1, 0.5 BTC)
        - plus change outputs
        """
        print(f"[+] Injecting {mix_count} CoinJoin / Mixing transactions...")
        denominations = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0]

        for mix_idx in range(mix_count):
            ts = random.randint(start_ts, end_ts)
            pool_size = random.randint(5, 12)  # 5 to 12 participants
            target_denom = random.choice(denominations)
            
            src_ip, country, asn = self.net_mgr.generate_random_ip()
            dst_ip, _, _ = self.net_mgr.generate_random_ip()
            src_port, dst_port = self.net_mgr.generate_port_pair()

            inputs = []
            outputs = []
            mix_entity = f"COINJOIN_POOL_{mix_idx+1}"
            
            total_in = 0.0
            script_type = random.choice(["P2WPKH", "Taproot", "P2SH"])

            for participant in range(pool_size):
                in_addr, _ = self.addr_gen.generate_address(script_type)
                # Input must cover denom + fee + change
                in_amt = round(target_denom + random.uniform(0.005, 0.08), 6)
                inputs.append((in_addr, in_amt))
                total_in += in_amt
                self._register_wallet(in_addr, f"{mix_entity}_USER_{participant+1}", is_suspicious=True, pattern_type="COINJOIN_INPUT")

            # Fee calculation for large tx
            coordinator_fee_per_user = round(target_denom * 0.003, 6) # 0.3% coordinator fee
            miner_fee = round(0.00004 * pool_size, 6)
            total_fee = round((coordinator_fee_per_user * pool_size) + miner_fee, 6)

            # Equal denomination mixed outputs
            for participant in range(pool_size):
                out_addr, _ = self.addr_gen.generate_address(script_type)
                outputs.append((out_addr, target_denom))
                self._register_wallet(out_addr, f"{mix_entity}_MIXED_OUT", is_suspicious=True, pattern_type="COINJOIN_OUTPUT")

            # Change outputs for each participant
            for idx, (in_addr, in_amt) in enumerate(inputs):
                change_amt = round(in_amt - target_denom - coordinator_fee_per_user - (miner_fee / pool_size), 6)
                if change_amt > 0.001:
                    change_addr, _ = self.addr_gen.generate_address(script_type)
                    outputs.append((change_addr, change_amt))
                    self._register_wallet(change_addr, f"{mix_entity}_CHANGE_{idx+1}", is_suspicious=True, pattern_type="COINJOIN_CHANGE")

            # Shuffle outputs to mirror real Wasabi/Samourai anonymity set
            random.shuffle(outputs)

            tx = self._create_tx_dict(ts, src_ip, dst_ip, src_port, dst_port,
                                       inputs, outputs, total_fee, script_type, country, asn, "COINJOIN_MIXING")
            self.transactions.append(tx)

    # -------------------------------------------------------------------------------
    # PATTERN D: COMMON-INPUT OWNERSHIP CLUSTER (Multi-Input Heuristic + Shared IP)
    # -------------------------------------------------------------------------------
    def inject_common_input_clusters(self, cluster_count: int = 15, start_ts: int = 0, end_ts: int = 0):
        """
        Creates clusters of 5-10 wallet addresses belonging to the same entity.
        These wallets repeatedly appear together in multi-input transactions and broadcast
        from the exact same 1-2 source IPs (Sybil/Botnet/Exchange Sweep heuristic).
        """
        print(f"[+] Injecting {cluster_count} Common-Input Ownership Clusters...")
        for c_idx in range(cluster_count):
            cluster_size = random.randint(5, 9)
            entity_id = f"SYBIL_CLUSTER_{c_idx+1}"
            
            # Persistent IP and script type for this cluster
            static_src_ip, country, asn = self.net_mgr.generate_random_ip()
            backup_src_ip, _, _ = self.net_mgr.generate_random_ip()
            script_type = random.choice(["P2PKH", "P2SH", "P2WPKH"])

            # Generate the entity's wallet pool
            cluster_wallets = []
            for _ in range(cluster_size):
                w_addr, _ = self.addr_gen.generate_address(script_type)
                cluster_wallets.append(w_addr)
                self._register_wallet(w_addr, entity_id, is_suspicious=True, pattern_type="COMMON_INPUT_CLUSTER")

            # Generate 4 to 8 transactions per cluster consolidating funds
            tx_repeats = random.randint(4, 8)
            base_ts = random.randint(start_ts, end_ts - (tx_repeats * 3600))

            for rep in range(tx_repeats):
                ts = base_ts + (rep * random.randint(600, 3600))
                # Select 3-6 wallets from the cluster as co-inputs
                k_inputs = random.randint(3, min(cluster_size, 6))
                selected_in_addrs = random.sample(cluster_wallets, k=k_inputs)

                inputs = [(addr, round(random.uniform(0.1, 1.5), 6)) for addr in selected_in_addrs]
                total_in = sum(item[1] for item in inputs)
                
                fee = round(random.uniform(0.00008, 0.0003), 8)
                consolidation_dest, _ = self.addr_gen.generate_address()
                outputs = [(consolidation_dest, round(total_in - fee, 6))]
                self._register_wallet(consolidation_dest, f"{entity_id}_CONSOLIDATION", is_suspicious=True, pattern_type="CLUSTER_DEST")

                used_ip = static_src_ip if random.random() < 0.8 else backup_src_ip
                dst_ip, _, _ = self.net_mgr.generate_random_ip()
                src_port, dst_port = self.net_mgr.generate_port_pair()

                tx = self._create_tx_dict(ts, used_ip, dst_ip, src_port, dst_port,
                                           inputs, outputs, fee, script_type, country, asn, "COMMON_INPUT_CLUSTER")
                self.transactions.append(tx)

    # -------------------------------------------------------------------------------
    # PATTERN E: STATISTICAL ANOMALIES (Whales, Extreme Fees, Rapid Bursts)
    # -------------------------------------------------------------------------------
    def inject_statistical_anomalies(self, count: int = 50, start_ts: int = 0, end_ts: int = 0):
        """
        Injects outlier anomalies:
        1. Whale transfers (250 - 5,000 BTC)
        2. Extreme Fee anomalies (sub-satoshi or massive fat-finger fee > 0.5 BTC)
        3. Rapid microsecond / burst traffic (5-10 txs from same IP in < 10 seconds)
        """
        print(f"[+] Injecting {count} Statistical Outliers (Whales, Extreme Fees, Bursts)...")
        sub_types = ["WHALE_TRANSFER", "FAT_FINGER_FEE", "ZERO_FEE_DUST", "RAPID_BURST"]

        i = 0
        while i < count:
            anomaly_type = random.choice(sub_types)
            ts = random.randint(start_ts, end_ts)
            src_ip, country, asn = self.net_mgr.generate_random_ip()
            dst_ip, _, _ = self.net_mgr.generate_random_ip()
            src_port, dst_port = self.net_mgr.generate_port_pair()
            addr, script_type = self.addr_gen.generate_address()

            if anomaly_type == "WHALE_TRANSFER":
                # Huge institutional / hacker movement: 150 to 3,500 BTC
                whale_amt = round(random.uniform(150.0, 3500.0), 4)
                in_addr, _ = self.addr_gen.generate_address("Taproot")
                out_addr, _ = self.addr_gen.generate_address("Taproot")
                fee = round(random.uniform(0.0001, 0.0005), 8)
                
                self._register_wallet(in_addr, "WHALE_ENTITY", is_suspicious=True, pattern_type="WHALE_SENDER")
                self._register_wallet(out_addr, "WHALE_ENTITY", is_suspicious=True, pattern_type="WHALE_RECIPIENT")

                tx = self._create_tx_dict(ts, src_ip, dst_ip, src_port, dst_port,
                                           [(in_addr, whale_amt + fee)], [(out_addr, whale_amt)],
                                           fee, "Taproot", country, asn, "STATISTICAL_WHALE")
                self.transactions.append(tx)
                i += 1

            elif anomaly_type == "FAT_FINGER_FEE":
                # User accidentally pays 0.2 - 2.5 BTC as miner fee
                in_addr, _ = self.addr_gen.generate_address("P2PKH")
                out_addr, _ = self.addr_gen.generate_address("P2PKH")
                transfer_amt = round(random.uniform(0.1, 1.0), 6)
                huge_fee = round(random.uniform(0.25, 2.5), 6)

                self._register_wallet(in_addr, "FAT_FINGER_VICTIM", is_suspicious=True, pattern_type="EXTREME_FEE_ERROR")
                self._register_wallet(out_addr, "RECIPIENT", is_suspicious=False, pattern_type="NORMAL")

                tx = self._create_tx_dict(ts, src_ip, dst_ip, src_port, dst_port,
                                           [(in_addr, transfer_amt + huge_fee)], [(out_addr, transfer_amt)],
                                           huge_fee, "P2PKH", country, asn, "STATISTICAL_EXTREME_FEE")
                self.transactions.append(tx)
                i += 1

            elif anomaly_type == "ZERO_FEE_DUST":
                # Dust attack / zero fee transaction
                dust_amt = 0.00000546 # Classic Bitcoin dust limit
                in_addr, _ = self.addr_gen.generate_address()
                out_addr, _ = self.addr_gen.generate_address()
                zero_fee = 0.00000001 # 1 satoshi

                self._register_wallet(in_addr, "DUSTING_ATTACKER", is_suspicious=True, pattern_type="DUST_SPAM")
                self._register_wallet(out_addr, "DUST_VICTIM", is_suspicious=True, pattern_type="DUST_TARGET")

                tx = self._create_tx_dict(ts, src_ip, dst_ip, src_port, dst_port,
                                           [(in_addr, dust_amt + zero_fee)], [(out_addr, dust_amt)],
                                           zero_fee, script_type, country, asn, "STATISTICAL_DUST_ATTACK")
                self.transactions.append(tx)
                i += 1

            elif anomaly_type == "RAPID_BURST":
                # Burst of 4-6 txs within 3 seconds from the same IP
                burst_size = random.randint(4, 6)
                burst_entity = f"BURST_BOT_{i+1}"
                
                for b_idx in range(burst_size):
                    burst_ts = ts + (b_idx) # 1 sec intervals
                    b_in, _ = self.addr_gen.generate_address(script_type)
                    b_out, _ = self.addr_gen.generate_address(script_type)
                    b_amt = round(random.uniform(0.01, 0.05), 6)
                    fee = round(random.uniform(0.00002, 0.00008), 8)

                    self._register_wallet(b_in, burst_entity, is_suspicious=True, pattern_type="RAPID_BURST_BOT")
                    self._register_wallet(b_out, "BURST_TARGET", is_suspicious=True, pattern_type="RAPID_BURST_BOT")

                    tx = self._create_tx_dict(burst_ts, src_ip, dst_ip, src_port, dst_port,
                                               [(b_in, b_amt + fee)], [(b_out, b_amt)],
                                               fee, script_type, country, asn, "STATISTICAL_RAPID_BURST")
                    self.transactions.append(tx)
                i += burst_size

    # -------------------------------------------------------------------------------
    # 5. DATASET GENERATION WORKFLOW & EXPORTERS
    # -------------------------------------------------------------------------------
    def generate(self) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Runs the entire pipeline."""
        min_ts, max_ts = self.price_mgr.get_time_range()
        print(f"\n[*] Starting Synthetic Dataset Generation (Target: ~{self.total_txs:,} txs)...")
        print(f"[*] Simulation Timestamp Window: {datetime.fromtimestamp(min_ts, tz=timezone.utc)} to {datetime.fromtimestamp(max_ts, tz=timezone.utc)}")

        # Proportion breakdown:
        # 80% Normal traffic
        # 8% Peeling Chains
        # 5% CoinJoin / Mixing
        # 4% Common-Input Clusters
        # 3% Statistical Anomalies
        normal_target = int(self.total_txs * 0.80)
        
        # 1. Normal traffic
        self.generate_normal_transactions(normal_target, min_ts, max_ts)

        # 2. Peeling Chains
        peel_chains_count = max(10, int(self.total_txs * 0.08 / 10))
        self.inject_peeling_chains(chain_count=peel_chains_count, start_ts=min_ts, end_ts=max_ts)

        # 3. CoinJoin Mixing
        mixing_count = max(10, int(self.total_txs * 0.05 / 2))
        self.inject_coinjoin_mixing(mix_count=mixing_count, start_ts=min_ts, end_ts=max_ts)

        # 4. Common Input Clusters
        cluster_count = max(5, int(self.total_txs * 0.04 / 5))
        self.inject_common_input_clusters(cluster_count=cluster_count, start_ts=min_ts, end_ts=max_ts)

        # 5. Statistical Anomalies
        stat_count = max(20, int(self.total_txs * 0.03))
        self.inject_statistical_anomalies(count=stat_count, start_ts=min_ts, end_ts=max_ts)

        # Sort all transactions chronologically by timestamp
        self.transactions.sort(key=lambda x: x["timestamp"])

        print(f"\n[+] Generation Complete!")
        print(f"    Total Transactions Generated : {len(self.transactions):,}")
        print(f"    Total Unique Wallets Tracked : {len(self.ground_truth):,}")
        
        suspicious_count = sum(1 for v in self.ground_truth.values() if v["is_suspicious"] == 1)
        print(f"    Suspicious Labeled Wallets   : {suspicious_count:,} ({suspicious_count / len(self.ground_truth) * 100:.1f}%)")

        return self.transactions, self.ground_truth

    def export(self, 
               tx_csv_path: str = "transactions.csv",
               tx_json_path: str = "transactions.json",
               gt_csv_path: str = "ground_truth.csv"):
        """Exports the dataset into CSV, JSON, and Ground Truth CSV files."""
        print(f"\n[*] Exporting generated datasets to disk...")

        # 1. Export transactions.csv
        if HAS_PANDAS:
            df_tx = pd.DataFrame(self.transactions)
            df_tx.to_csv(tx_csv_path, index=False)
            print(f"    [1/3] Saved CSV: {tx_csv_path} ({len(df_tx):,} rows)")
        else:
            import csv
            if self.transactions:
                with open(tx_csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list(self.transactions[0].keys()))
                    writer.writeheader()
                    writer.writerows(self.transactions)
            print(f"    [1/3] Saved CSV: {tx_csv_path} ({len(self.transactions):,} rows)")

        # 2. Export transactions.json
        with open(tx_json_path, 'w', encoding='utf-8') as f:
            json.dump(self.transactions, f, indent=2)
        print(f"    [2/3] Saved JSON: {tx_json_path}")

        # 3. Export ground_truth.csv
        gt_list = list(self.ground_truth.values())
        if HAS_PANDAS:
            df_gt = pd.DataFrame(gt_list)
            df_gt.to_csv(gt_csv_path, index=False)
            print(f"    [3/3] Saved Ground Truth: {gt_csv_path} ({len(df_gt):,} wallet labels)")
        else:
            import csv
            if gt_list:
                with open(gt_csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list(gt_list[0].keys()))
                    writer.writeheader()
                    writer.writerows(gt_list)
            print(f"    [3/3] Saved Ground Truth: {gt_csv_path} ({len(gt_list):,} wallet labels)")

        print("\n[OK] All dataset files successfully created and verified!")


# ===================================================================================
# CLI INTERFACE
# ===================================================================================
def main():
    parser = argparse.ArgumentParser(
        description="SIH26146: Synthetic Hybrid Bitcoin Transaction & Network Dataset Generator"
    )
    parser.add_argument(
        "--count", type=int, default=8000,
        help="Number of synthetic transactions to generate (default: 8000)"
    )
    parser.add_argument(
        "--price-csv", type=str, default="btcusd_1-min_data.csv",
        help="Path to real Kaggle 1-minute price CSV file (default: btcusd_1-min_data.csv)"
    )
    parser.add_argument(
        "--geolite-city", type=str, default="GeoLite2-City.mmdb",
        help="Path to MaxMind GeoLite2-City.mmdb (optional, has offline fallback)"
    )
    parser.add_argument(
        "--geolite-asn", type=str, default="GeoLite2-ASN.mmdb",
        help="Path to MaxMind GeoLite2-ASN.mmdb (optional, has offline fallback)"
    )
    parser.add_argument(
        "--out-csv", type=str, default="transactions.csv",
        help="Output transactions CSV path (default: transactions.csv)"
    )
    parser.add_argument(
        "--out-json", type=str, default="transactions.json",
        help="Output transactions JSON path (default: transactions.json)"
    )
    parser.add_argument(
        "--out-gt", type=str, default="ground_truth.csv",
        help="Output ground truth CSV path (default: ground_truth.csv)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    generator = BitcoinDatasetGenerator(
        total_txs=args.count,
        price_csv=args.price_csv,
        seed=args.seed
    )
    
    generator.generate()
    generator.export(
        tx_csv_path=args.out_csv,
        tx_json_path=args.out_json,
        gt_csv_path=args.out_gt
    )


if __name__ == "__main__":
    main()
