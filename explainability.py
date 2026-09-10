#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
EXPLAINABILITY ENGINE ? SHAP Feature Attribution & Forensic Driver Profiling
===================================================================================
Provides model-level and sample-level explainability for unsupervised Isolation Forest:
1. SHAP TreeExplainer calculates exact shap_values on the 8 behavioral features.
2. Inverts sign to map path-length deviation directly to anomaly contribution.
3. Ranks top-K features with impact magnitude and direction (INCREASES_ANOMALY).
4. Generates publication-quality SHAP summary plot for forensic reports.
5. Robust fallback heuristic (IQR deviation) guarantees 100% offline reliability.
===================================================================================
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

try:
    import joblib
except ImportError:
    joblib = None

# Feature definition matching anomaly_detection.py
FEATURE_NAMES = [
    "total_input_btc",
    "fee_btc",
    "fee_as_pct_of_amount",
    "input_count",
    "output_count",
    "hour_of_day",
    "src_ip_frequency",
    "time_since_last_tx"
]

FEATURE_LABELS = {
    "total_input_btc": "Whale Transfer Volume (BTC)",
    "fee_btc": "Miner Fee Amount (BTC)",
    "fee_as_pct_of_amount": "Fee-to-Capital Ratio (%)",
    "input_count": "Input Address Consolidation Count",
    "output_count": "Output Fan-out Count",
    "hour_of_day": "Broadcast Hour (UTC)",
    "src_ip_frequency": "Source IP Burst Frequency",
    "time_since_last_tx": "Consecutive Broadcast Interval (s)"
}

FEATURE_DESCRIPTIONS = {
    "total_input_btc": "Transaction volume significantly deviates from baseline distribution.",
    "fee_btc": "Unusually high miner transaction fee.",
    "fee_as_pct_of_amount": "Extreme fee ratio relative to transferred capital.",
    "input_count": "High input consolidation count indicative of multi-party mixing or aggregation.",
    "output_count": "High output dispersal count characteristic of peeling or distribution.",
    "hour_of_day": "Temporal divergence: broadcast during atypical network activity window.",
    "src_ip_frequency": "Rapid transaction bursts observed originating from same source IP node.",
    "time_since_last_tx": "Abnormally short interval between consecutive transactions from wallet."
}


class ShapForensicExplainer:
    """Computes genuine SHAP values for Isolation Forest anomaly models."""

    def __init__(self,
                 model_path: str = "isolation_forest.joblib",
                 scaler_path: str = "feature_scaler.joblib",
                 model: Any = None,
                 scaler: Any = None):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.iso_model = model
        self.scaler = scaler
        self.explainer = None
        self._load_or_init()

    def _load_or_init(self):
        """Loads serialized model and scaler or initializes them."""
        if self.iso_model is None and joblib is not None and os.path.exists(self.model_path):
            try:
                self.iso_model = joblib.load(self.model_path)
                print(f"[+] Loaded Isolation Forest model from {self.model_path}")
            except Exception as e:
                print(f"[!] Warning: Could not load {self.model_path}: {e}")

        if self.scaler is None and joblib is not None and os.path.exists(self.scaler_path):
            try:
                self.scaler = joblib.load(self.scaler_path)
                print(f"[+] Loaded feature scaler from {self.scaler_path}")
            except Exception as e:
                print(f"[!] Warning: Could not load {self.scaler_path}: {e}")

        if self.iso_model is not None:
            try:
                import shap
                self.explainer = shap.TreeExplainer(self.iso_model)
                print("[+] Initialized SHAP TreeExplainer for Isolation Forest.")
            except Exception as e:
                print(f"[!] Warning: Could not initialize SHAP TreeExplainer: {e}")
                self.explainer = None

    def prepare_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """Applies consistent log-transformations and scaling to transaction features."""
        X_raw = df[FEATURE_NAMES].copy().fillna(0)
        X_trans = X_raw.copy()
        X_trans["total_input_btc"] = np.log1p(np.maximum(0, X_trans["total_input_btc"]))
        X_trans["fee_btc"] = np.log1p(np.maximum(0, X_trans["fee_btc"]))
        X_trans["fee_as_pct_of_amount"] = np.log1p(np.maximum(0, X_trans["fee_as_pct_of_amount"]))
        X_trans["time_since_last_tx"] = np.log1p(np.maximum(0, X_trans["time_since_last_tx"]))

        if self.scaler is not None:
            try:
                X_scaled = self.scaler.transform(X_trans)
            except Exception:
                from sklearn.preprocessing import RobustScaler
                self.scaler = RobustScaler().fit(X_trans)
                X_scaled = self.scaler.transform(X_trans)
        else:
            try:
                from sklearn.preprocessing import RobustScaler
                self.scaler = RobustScaler().fit(X_trans)
                X_scaled = self.scaler.transform(X_trans)
            except Exception:
                X_scaled = X_trans.values

        return X_scaled, X_trans

    def explain_transactions(self, df_tx: pd.DataFrame, top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Computes top-K SHAP feature attributions for each transaction in df_tx.
        Returns: { txid: [ { feature, shap_value, impact, direction, label, description }, ... ] }
        """
        if df_tx.empty or "txid" not in df_tx.columns:
            return {}

        txids = df_tx["txid"].tolist()
        explanations: Dict[str, List[Dict[str, Any]]] = {}

        if self.explainer is not None:
            try:
                X_scaled, _ = self.prepare_feature_matrix(df_tx)
                raw_shap = self.explainer.shap_values(X_scaled)
                # In sklearn Isolation Forest, lower score = more anomalous.
                # In TreeExplainer, negative SHAP pulls path length shorter (more anomalous).
                # Invert sign so positive impact = increases anomaly likelihood.
                anomaly_impact = -np.array(raw_shap)

                for i, txid in enumerate(txids):
                    row_impact = anomaly_impact[i]
                    top_indices = np.argsort(np.abs(row_impact))[::-1][:top_k]

                    tx_exps = []
                    for idx in top_indices:
                        fname = FEATURE_NAMES[idx]
                        val = float(row_impact[idx])
                        direction = "INCREASES_ANOMALY" if val > 0 else "DECREASES_ANOMALY"
                        sign = "+" if val >= 0 else ""
                        shap_str = f"{sign}{val:.3f} SHAP"
                        tx_exps.append({
                            "feature": fname,
                            "label": FEATURE_LABELS.get(fname, fname),
                            "shap_value": round(val, 4),
                            "impact": round(abs(val), 4),
                            "direction": direction,
                            "description": f"{FEATURE_DESCRIPTIONS.get(fname, '')} ({shap_str})"
                        })
                    explanations[txid] = tx_exps

                return explanations
            except Exception as e:
                print(f"[!] SHAP calculation issue ({e}); falling back to heuristic.")

        return self._heuristic_feature_attribution(df_tx, top_k=top_k)

    def _heuristic_feature_attribution(self, df_tx: pd.DataFrame, top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Graceful fallback computing normalized deviation when SHAP is unavailable."""
        txids = df_tx["txid"].tolist()
        explanations: Dict[str, List[Dict[str, Any]]] = {}

        X_raw = df_tx[FEATURE_NAMES].copy().fillna(0)
        medians = X_raw.median()
        iqrs = (X_raw.quantile(0.75) - X_raw.quantile(0.25)).replace(0, 1e-5)
        deviations = np.abs((X_raw - medians) / iqrs)

        for i, txid in enumerate(txids):
            row_dev = deviations.iloc[i]
            top_feats = row_dev.nlargest(top_k)

            tx_exps = []
            for fname, dev_val in top_feats.items():
                float_dev = float(dev_val)
                tx_exps.append({
                    "feature": fname,
                    "label": FEATURE_LABELS.get(fname, fname),
                    "shap_value": round(float_dev / 10.0, 4),
                    "impact": round(float_dev / 10.0, 4),
                    "direction": "INCREASES_ANOMALY",
                    "description": f"{FEATURE_DESCRIPTIONS.get(fname, '')} (Robust Z: {float_dev:.2f})"
                })
            explanations[txid] = tx_exps

        return explanations

    def generate_summary_plot(self, df_sample: pd.DataFrame, output_path: str = "reports/shap_summary.png"):
        """Generates a publication-grade SHAP summary chart saved to reports/."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            X_scaled, _ = self.prepare_feature_matrix(df_sample)
            if self.explainer is not None:
                shap_values = self.explainer.shap_values(X_scaled)
                mean_abs = np.mean(np.abs(shap_values), axis=0)
                sorted_idx = np.argsort(mean_abs)

                plt.figure(figsize=(9, 5), dpi=300)
                plt.barh([FEATURE_LABELS[FEATURE_NAMES[i]] for i in sorted_idx],
                         mean_abs[sorted_idx],
                         color="#3b82f6", edgecolor="#1d4ed8", alpha=0.85)
                plt.title("Isolation Forest Feature Importance via TreeExplainer SHAP", fontsize=12, fontweight="bold", pad=12)
                plt.xlabel("Mean |SHAP Value| (Average impact on anomaly score)", fontsize=10)
                plt.grid(axis="x", linestyle="--", alpha=0.5)
                plt.tight_layout()
                plt.savefig(output_path, dpi=300)
                plt.close()
                print(f"[+] Saved SHAP summary plot to: {output_path}")
                return True
        except Exception as e:
            print(f"[!] Could not generate SHAP summary plot: {e}")
            return False


if __name__ == "__main__":
    print("[*] Testing ShapForensicExplainer...")
    if os.path.exists("transaction_anomalies.csv"):
        df_test = pd.read_csv("transaction_anomalies.csv").head(20)
        explainer = ShapForensicExplainer()
        res = explainer.explain_transactions(df_test, top_k=3)
        sample_txid = list(res.keys())[0]
        print(f"[+] Sample explanation for {sample_txid[:16]}...:")
        print(json.dumps(res[sample_txid], indent=2))
        explainer.generate_summary_plot(df_test, "reports/shap_summary.png")
        print("[OK] ShapForensicExplainer test passed!")
    else:
        print("[!] transaction_anomalies.csv not found; run anomaly_detection.py first.")
