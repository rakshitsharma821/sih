#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
STEP 4 (MODULE B) — ANOMALY DETECTION (Isolation Forest + Autoencoder Reconstruction)
===================================================================================
1. Transaction Feature Engineering:
   - total_input_btc
   - fee_btc
   - fee_as_pct_of_amount
   - input_count
   - output_count
   - hour_of_day
   - src_ip_transaction_frequency
   - time_since_last_tx_from_same_wallet
2. Unsupervised Models:
   - Model 1: Isolation Forest (Scikit-Learn) with path-length anomaly scoring.
   - Model 2: Deep / Shallow Reconstruction Autoencoder (Reconstruction MSE).
3. Ensembles normalized anomaly scores into [0, 1].
===================================================================================
"""

import os
import sys
import math
import sqlite3
import argparse
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import RobustScaler, MinMaxScaler
    from sklearn.neural_network import MLPRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class TransactionAnomalyDetector:
    """Extracts features and trains Isolation Forest + Autoencoder ensemble."""

    def __init__(self, db_path: str = "bitcoin_traffic.db", contamination: float = 0.08, seed: int = 42):
        self.db_path = db_path
        self.contamination = contamination
        self.seed = seed
        self.feature_names = [
            "total_input_btc",
            "fee_btc",
            "fee_as_pct_of_amount",
            "input_count",
            "output_count",
            "hour_of_day",
            "src_ip_frequency",
            "time_since_last_tx"
        ]
        self.iso_model = None
        self.autoencoder_model = None
        self.scaler = None
        self.df_features = None
        self.df_results = None

    def extract_features(self) -> pd.DataFrame:
        """Loads transaction data from SQLite and computes behavioral financial features."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database {self.db_path} not found.")

        print(f"[*] Extracting transaction features from: {self.db_path}...")
        conn = sqlite3.connect(self.db_path)

        # 1. Main transaction metadata
        df_tx = pd.read_sql_query("""
            SELECT txid, timestamp, datetime_utc, src_ip, total_input_btc,
                   fee_btc, input_count, output_count, btc_price_usd, volume_usd, pattern_label
            FROM transactions
            ORDER BY timestamp ASC
        """, conn)

        # 2. Input mappings to compute time_since_last_tx_from_same_wallet
        df_inputs = pd.read_sql_query("""
            SELECT txid, address FROM tx_inputs
        """, conn)
        conn.close()

        print(f"[+] Calculating temporal and colocation signals for {len(df_tx):,} transactions...")

        # Feature 1: fee_as_pct_of_amount
        df_tx["fee_as_pct_of_amount"] = (
            df_tx["fee_btc"] / (df_tx["total_input_btc"] + 1e-7)
        ) * 100.0

        # Feature 2: hour_of_day (UTC)
        df_tx["hour_of_day"] = pd.to_datetime(df_tx["datetime_utc"]).dt.hour

        # Feature 3: src_ip_frequency
        ip_counts = df_tx["src_ip"].value_counts().to_dict()
        df_tx["src_ip_frequency"] = df_tx["src_ip"].map(ip_counts).fillna(1).astype(int)

        # Feature 4: time_since_last_tx_from_same_wallet
        # Map first input address of each tx to last seen timestamp
        tx_primary_wallet = df_inputs.groupby("txid")["address"].first().to_dict()
        df_tx["primary_wallet"] = df_tx["txid"].map(tx_primary_wallet).fillna("UNKNOWN")

        wallet_last_time: Dict[str, int] = {}
        time_diffs = []

        for _, row in df_tx.iterrows():
            w = row["primary_wallet"]
            ts = row["timestamp"]
            if w in wallet_last_time:
                diff = max(0, ts - wallet_last_time[w])
            else:
                diff = 86400  # Default 24 hours if first appearance
            time_diffs.append(diff)
            wallet_last_time[w] = ts

        df_tx["time_since_last_tx"] = time_diffs

        self.df_features = df_tx
        print(f"[+] Extracted 8 analytical features across {len(df_tx):,} records.")
        return df_tx

    def train_models(self) -> pd.DataFrame:
        """Trains Isolation Forest and Autoencoder models and blends scores."""
        if self.df_features is None:
            self.extract_features()

        X_raw = self.df_features[self.feature_names].copy()

        # Handle log-transformations for heavy-tailed financial amounts
        X_trans = X_raw.copy()
        X_trans["total_input_btc"] = np.log1p(np.maximum(0, X_trans["total_input_btc"]))
        X_trans["fee_btc"] = np.log1p(np.maximum(0, X_trans["fee_btc"]))
        X_trans["fee_as_pct_of_amount"] = np.log1p(np.maximum(0, X_trans["fee_as_pct_of_amount"]))
        X_trans["time_since_last_tx"] = np.log1p(np.maximum(0, X_trans["time_since_last_tx"]))

        if HAS_SKLEARN:
            # 1. Scale features
            self.scaler = RobustScaler()
            X_scaled = self.scaler.fit_transform(X_trans)

            # 2. Train Isolation Forest
            print(f"[*] Training Isolation Forest (contamination={self.contamination})...")
            self.iso_model = IsolationForest(
                n_estimators=150,
                contamination=self.contamination,
                random_state=self.seed,
                n_jobs=-1
            )
            self.iso_model.fit(X_scaled)
            # score_samples returns opposite of anomaly score (lower is more anomalous)
            raw_iso_scores = -self.iso_model.score_samples(X_scaled)
            iso_min_max = MinMaxScaler()
            iso_scores = iso_min_max.fit_transform(raw_iso_scores.reshape(-1, 1)).flatten()

            # 3. Train Autoencoder (Reconstruction Error via BottleNeck MLP)
            print("[*] Training 3-layer Autoencoder for reconstruction anomaly profiling...")
            # 8 -> 4 (bottleneck) -> 8
            self.autoencoder_model = MLPRegressor(
                hidden_layer_sizes=(16, 4, 16),
                activation="relu",
                max_iter=40,
                random_state=self.seed,
                early_stopping=True
            )
            self.autoencoder_model.fit(X_scaled, X_scaled)
            X_recon = self.autoencoder_model.predict(X_scaled)
            mse = np.mean(np.square(X_scaled - X_recon), axis=1)
            ae_min_max = MinMaxScaler()
            ae_scores = ae_min_max.fit_transform(mse.reshape(-1, 1)).flatten()

            # 4. Ensemble Score (60% Isolation Forest + 40% Autoencoder)
            ensemble_scores = 0.60 * iso_scores + 0.40 * ae_scores
        else:
            # Fallback heuristic statistical anomaly score if sklearn missing
            print("[!] Scikit-learn not available; utilizing statistical z-score fallback.")
            z_scores = np.abs((X_trans - X_trans.mean()) / (X_trans.std() + 1e-6))
            ensemble_scores = np.clip(z_scores.mean(axis=1) / 3.0, 0.0, 1.0)
            iso_scores = ensemble_scores
            ae_scores = ensemble_scores

        df_out = self.df_features.copy()
        df_out["isolation_score"] = np.round(iso_scores, 4)
        df_out["autoencoder_score"] = np.round(ae_scores, 4)
        df_out["anomaly_score"] = np.round(ensemble_scores, 4)
        df_out["is_anomaly"] = (df_out["anomaly_score"] >= 0.70).astype(int)

        self.df_results = df_out
        n_flagged = df_out['is_anomaly'].sum()
        print(f"[+] Anomaly Detection Complete: Flagged {n_flagged:,} transactions ({n_flagged / len(df_out) * 100:.1f}%).")
        return df_out

    def save_results(self, out_csv: str = "transaction_anomalies.csv"):
        """Exports anomaly detections to CSV."""
        if self.df_results is not None:
            self.df_results.to_csv(out_csv, index=False)
            print(f"[+] Saved anomaly detection results to: {out_csv}")


def run_anomaly_detection(db_path: str = "bitcoin_traffic.db",
                          out_csv: str = "transaction_anomalies.csv") -> pd.DataFrame:
    """Convenience functional API for Step 5 integration."""
    detector = TransactionAnomalyDetector(db_path=db_path)
    df = detector.train_models()
    detector.save_results(out_csv)
    return df


def main():
    parser = argparse.ArgumentParser(description="ChainSentinel // Step 4 (Module B): Anomaly Detection")
    parser.add_argument("--db", type=str, default="bitcoin_traffic.db", help="Path to SQLite database")
    parser.add_argument("--out", type=str, default="transaction_anomalies.csv", help="Output CSV path")
    args = parser.parse_args()

    run_anomaly_detection(db_path=args.db, out_csv=args.out)


if __name__ == "__main__":
    main()
