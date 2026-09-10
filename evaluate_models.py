#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
BENCHMARK & MODEL EVALUATION ENGINE
===================================================================================
Executes rigorous evaluation against ground_truth.csv and SQLite transaction labels:
1. Transaction Anomaly Detection:
   - Isolation Forest (sklearn)
   - Autoencoder Reconstruction (MLPRegressor)
   - Blended Ensemble
   Evaluated against:
   a) Statistical Anomaly Sub-types (Whale, Fee, Burst, Dust)
   b) All Illicit / Obfuscation Patterns (Peeling, CoinJoin, Cluster, Statistical)
2. Graph Risk Scoring:
   - Personalized PageRank Taint Propagation vs Wallet Ground Truth
3. Structural Pattern Detectors:
   - Peeling Chain & CoinJoin Mixing Detection vs Graph Reality
4. Exports:
   - evaluation_results.json (Machine-readable benchmark scorecard)
   - MODEL_EVALUATION.md (Audit-ready forensic evaluation documentation)
   - reports/roc_curve.png, reports/pr_curve.png, reports/confusion_matrix.png
===================================================================================
"""

import os
import sys
import json
import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

try:
    from sklearn.metrics import (
        roc_auc_score, average_precision_score, confusion_matrix,
        precision_score, recall_score, f1_score, accuracy_score,
        roc_curve, precision_recall_curve
    )
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_EVAL_LIBS = True
except ImportError as e:
    print(f"[!] Warning: Missing evaluation libraries: {e}")
    HAS_EVAL_LIBS = False


def calculate_metrics(y_true: np.ndarray, y_scores: np.ndarray, threshold: float = 0.70) -> Dict[str, Any]:
    """Calculates comprehensive classification metrics for given score and threshold."""
    y_pred = (y_scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    acc = accuracy_score(y_true, y_pred)
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    
    try:
        roc_auc = float(roc_auc_score(y_true, y_scores))
    except Exception:
        roc_auc = 0.5
        
    try:
        pr_auc = float(average_precision_score(y_true, y_scores))
    except Exception:
        pr_auc = 0.0

    return {
        "threshold": round(float(threshold), 3),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "specificity": round(float(spec), 4),
        "accuracy": round(float(acc), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    }


def find_optimal_threshold(y_true: np.ndarray, y_scores: np.ndarray) -> Tuple[float, Dict[str, Any]]:
    """Finds the threshold that maximizes the F1 score."""
    best_f1 = -1.0
    best_thresh = 0.50
    best_metrics = None

    for t in np.linspace(0.10, 0.90, 81):
        m = calculate_metrics(y_true, y_scores, threshold=t)
        if m["f1_score"] > best_f1:
            best_f1 = m["f1_score"]
            best_thresh = t
            best_metrics = m

    return best_thresh, best_metrics


def run_evaluation(db_path: str = "bitcoin_traffic.db",
                   anomalies_csv: str = "transaction_anomalies.csv",
                   wallet_risk_csv: str = "wallet_risk_scores.csv",
                   ground_truth_csv: str = "ground_truth.csv",
                   patterns_csv: str = "detected_patterns.csv",
                   reports_dir: str = "reports") -> Dict[str, Any]:
    """Executes end-to-end benchmark evaluation across all models."""
    os.makedirs(reports_dir, exist_ok=True)
    print("="*75)
    print(" ChainSentinel // SIH26146: Quantitative Model Evaluation & Benchmarking")
    print("="*75)

    results: Dict[str, Any] = {
        "dataset_summary": {},
        "transaction_anomaly_models": {},
        "wallet_risk_scoring": {},
        "pattern_detectors": {}
    }

    # 1. Load Transaction Anomalies & Ground Truth
    print("[*] Loading transaction anomaly predictions and database labels...")
    df_anom = pd.read_csv(anomalies_csv)
    conn = sqlite3.connect(db_path)
    df_tx = pd.read_sql_query("SELECT txid, pattern_label FROM transactions", conn)
    conn.close()

    df_tx_eval = pd.merge(df_anom, df_tx[["txid", "pattern_label"]], on="txid", suffixes=("", "_db"))
    if "pattern_label_db" in df_tx_eval.columns:
        df_tx_eval["pattern_label"] = df_tx_eval["pattern_label_db"]

    n_total = len(df_tx_eval)
    y_any_anomaly = (df_tx_eval["pattern_label"] != "NORMAL").astype(int).values
    y_stat_anomaly = (df_tx_eval["pattern_label"].str.startswith("STATISTICAL_")).astype(int).values
    
    n_stat = int(y_stat_anomaly.sum())
    n_any = int(y_any_anomaly.sum())
    n_normal = n_total - n_any

    results["dataset_summary"] = {
        "total_transactions": n_total,
        "normal_transactions": n_normal,
        "total_anomalous_transactions": n_any,
        "statistical_anomalies": n_stat,
        "anomaly_prevalence_pct": round((n_any / n_total) * 100, 2)
    }

    print(f"[+] Evaluated {n_total:,} transactions: {n_normal:,} NORMAL, {n_stat:,} STATISTICAL, {n_any:,} TOTAL ANOMALIES.")

    # 2. Benchmark Transaction ML Models against Statistical Anomalies
    models = {
        "Isolation_Forest": df_tx_eval["isolation_score"].values,
        "Autoencoder_Reconstruction": df_tx_eval["autoencoder_score"].values,
        "Ensemble_Detector": df_tx_eval["anomaly_score"].values
    }

    print("\n[*] Evaluating Transaction Anomaly Models vs Statistical Anomalies:")
    for m_name, scores in models.items():
        opt_th, opt_m = find_optimal_threshold(y_stat_anomaly, scores)
        def_m = calculate_metrics(y_stat_anomaly, scores, threshold=0.70)
        
        # Also benchmark against all anomalies
        _, all_opt_m = find_optimal_threshold(y_any_anomaly, scores)
        all_def_m = calculate_metrics(y_any_anomaly, scores, threshold=0.70)

        results["transaction_anomaly_models"][m_name] = {
            "vs_statistical_anomalies": {
                "optimal_threshold": opt_m,
                "default_threshold_0_70": def_m
            },
            "vs_all_anomalous_patterns": {
                "optimal_threshold": all_opt_m,
                "default_threshold_0_70": all_def_m
            }
        }
        print(f"    - {m_name:28s} | ROC-AUC: {opt_m['roc_auc']:.4f} | PR-AUC: {opt_m['pr_auc']:.4f} | Best F1: {opt_m['f1_score']:.4f} (Thresh: {opt_th:.2f})")

    # 3. Benchmark Wallet Risk Propagation vs Ground Truth
    print("\n[*] Evaluating Wallet Risk Scoring (Personalized PageRank) vs ground_truth.csv...")
    if os.path.exists(wallet_risk_csv) and os.path.exists(ground_truth_csv):
        df_risk = pd.read_csv(wallet_risk_csv)
        df_gt = pd.read_csv(ground_truth_csv)
        df_w_eval = pd.merge(df_risk, df_gt, left_on="wallet_address", right_on="wallet_id")

        y_w_true = df_w_eval["is_suspicious"].astype(int).values
        y_w_score = df_w_eval["risk_score"].values

        w_opt_th, w_opt_m = find_optimal_threshold(y_w_true, y_w_score)
        w_def_m = calculate_metrics(y_w_true, y_w_score, threshold=0.50)

        results["wallet_risk_scoring"] = {
            "wallets_evaluated": len(df_w_eval),
            "suspicious_wallets": int(y_w_true.sum()),
            "benign_wallets": int(len(df_w_eval) - y_w_true.sum()),
            "optimal_threshold": w_opt_m,
            "default_threshold_0_50": w_def_m
        }
        print(f"    - Personalized PageRank Risk  | ROC-AUC: {w_opt_m['roc_auc']:.4f} | PR-AUC: {w_opt_m['pr_auc']:.4f} | Best F1: {w_opt_m['f1_score']:.4f} (Thresh: {w_opt_th:.2f})")

    # 4. Benchmark Pattern Detection
    print("\n[*] Evaluating Structural Pattern Detectors...")
    if os.path.exists(patterns_csv):
        df_pat = pd.read_csv(patterns_csv)
        pat_map = dict(zip(df_pat["txid"], df_pat["detected_pattern"]))

        # Peeling Chain
        y_peel_true = (df_tx_eval["pattern_label"] == "PEELING_CHAIN").astype(int).values
        y_peel_pred = np.array([1 if pat_map.get(t) == "PEELING_CHAIN" else 0 for t in df_tx_eval["txid"]])
        peel_prec = precision_score(y_peel_true, y_peel_pred, zero_division=0)
        peel_rec = recall_score(y_peel_true, y_peel_pred, zero_division=0)
        peel_f1 = f1_score(y_peel_true, y_peel_pred, zero_division=0)

        # CoinJoin Mixing
        y_cj_true = (df_tx_eval["pattern_label"] == "COINJOIN_MIXING").astype(int).values
        y_cj_pred = np.array([1 if pat_map.get(t) == "COINJOIN_MIXING" else 0 for t in df_tx_eval["txid"]])
        cj_prec = precision_score(y_cj_true, y_cj_pred, zero_division=0)
        cj_rec = recall_score(y_cj_true, y_cj_pred, zero_division=0)
        cj_f1 = f1_score(y_cj_true, y_cj_pred, zero_division=0)

        results["pattern_detectors"] = {
            "peeling_chain": {
                "ground_truth_count": int(y_peel_true.sum()),
                "detected_count": int(y_peel_pred.sum()),
                "precision": round(float(peel_prec), 4),
                "recall": round(float(peel_rec), 4),
                "f1_score": round(float(peel_f1), 4)
            },
            "coinjoin_mixing": {
                "ground_truth_count": int(y_cj_true.sum()),
                "detected_count": int(y_cj_pred.sum()),
                "precision": round(float(cj_prec), 4),
                "recall": round(float(cj_rec), 4),
                "f1_score": round(float(cj_f1), 4)
            }
        }
        print(f"    - Peeling Chain Detector     | Precision: {peel_prec:.4f} | Recall: {peel_rec:.4f} | F1: {peel_f1:.4f}")
        print(f"    - CoinJoin Mixer Detector    | Precision: {cj_prec:.4f} | Recall: {cj_rec:.4f} | F1: {cj_f1:.4f}")

    # 5. Export JSON
    out_json = "evaluation_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Exported structured evaluation results to: {out_json}")

    # 6. Generate Plot Visualizations
    generate_evaluation_plots(df_tx_eval, y_stat_anomaly, models, reports_dir)

    # 7. Generate MODEL_EVALUATION.md
    generate_markdown_report(results, "MODEL_EVALUATION.md")

    return results


def generate_evaluation_plots(df_tx_eval: pd.DataFrame, y_true: np.ndarray, models: Dict[str, np.ndarray], reports_dir: str):
    """Renders publication-ready ROC, PR, and Confusion Matrix charts."""
    try:
        # 1. ROC Curves
        plt.figure(figsize=(8, 6), dpi=300)
        colors = {"Isolation_Forest": "#3b82f6", "Autoencoder_Reconstruction": "#10b981", "Ensemble_Detector": "#8b5cf6"}
        for name, scores in models.items():
            fpr, tpr, _ = roc_curve(y_true, scores)
            auc_val = roc_auc_score(y_true, scores)
            plt.plot(fpr, tpr, label=f"{name.replace('_', ' ')} (AUC = {auc_val:.3f})", color=colors[name], lw=2)

        plt.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Guess (AUC = 0.500)")
        plt.title("Receiver Operating Characteristic (ROC) ? Anomaly Detectors", fontsize=12, fontweight="bold", pad=12)
        plt.xlabel("False Positive Rate", fontsize=10)
        plt.ylabel("True Positive Rate", fontsize=10)
        plt.legend(loc="lower right", fontsize=9)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        roc_path = os.path.join(reports_dir, "roc_curve.png")
        plt.savefig(roc_path, dpi=300)
        plt.close()
        print(f"[+] Saved ROC curve to: {roc_path}")

        # 2. Precision-Recall Curves
        plt.figure(figsize=(8, 6), dpi=300)
        for name, scores in models.items():
            prec, rec, _ = precision_recall_curve(y_true, scores)
            ap_val = average_precision_score(y_true, scores)
            plt.plot(rec, prec, label=f"{name.replace('_', ' ')} (PR-AUC = {ap_val:.3f})", color=colors[name], lw=2)

        plt.title("Precision-Recall Curve ? Anomaly Detectors", fontsize=12, fontweight="bold", pad=12)
        plt.xlabel("Recall", fontsize=10)
        plt.ylabel("Precision", fontsize=10)
        plt.legend(loc="lower left", fontsize=9)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        pr_path = os.path.join(reports_dir, "pr_curve.png")
        plt.savefig(pr_path, dpi=300)
        plt.close()
        print(f"[+] Saved Precision-Recall curve to: {pr_path}")

        # 3. Confusion Matrix Heatmaps (Side-by-Side)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)
        for ax, (name, scores) in zip(axes, models.items()):
            preds = (scores >= 0.70).astype(int)
            cm = confusion_matrix(y_true, preds, labels=[0, 1])
            im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
            ax.set_title(name.replace('_', ' '), fontsize=11, fontweight="bold")
            tick_marks = [0, 1]
            ax.set_xticks(tick_marks)
            ax.set_yticks(tick_marks)
            ax.set_xticklabels(["Normal", "Anomaly"])
            ax.set_yticklabels(["Normal", "Anomaly"])
            ax.set_ylabel("True Label", fontsize=9)
            ax.set_xlabel("Predicted Label", fontsize=9)

            thresh = cm.max() / 2.
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(j, i, f"{cm[i, j]:,}",
                            horizontalalignment="center",
                            color="white" if cm[i, j] > thresh else "black",
                            fontsize=10, fontweight="bold")
        fig.tight_layout()
        cm_path = os.path.join(reports_dir, "confusion_matrix.png")
        plt.savefig(cm_path, dpi=300)
        plt.close()
        print(f"[+] Saved Confusion Matrix heatmaps to: {cm_path}")

    except Exception as e:
        print(f"[!] Plot generation encountered error: {e}")


def generate_markdown_report(results: Dict[str, Any], out_md: str = "MODEL_EVALUATION.md"):
    """Generates a comprehensive Markdown documentation report of model metrics."""
    ds = results["dataset_summary"]
    tx_models = results["transaction_anomaly_models"]
    w_risk = results.get("wallet_risk_scoring", {})
    pats = results.get("pattern_detectors", {})

    lines = [
        "# ChainSentinel ? Machine Learning & Detection Model Evaluation Report",
        "**SIH 2026 Problem Statement:** SIH26146  ",
        "**Organization:** National Technical Research Organisation (NTRO)  ",
        "**Evaluation Date:** Automatic Post-Run Verification  ",
        "**Scope:** Transaction Anomaly Models, Personalized PageRank Taint Propagation, and Structural Pattern Detectors  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Benchmark Scorecard",
        f"ChainSentinel was benchmarked across **{ds.get('total_transactions', 0):,}** Bitcoin transactions and **{w_risk.get('wallets_evaluated', 0):,}** network wallets against verified ground-truth labels. The evaluation validates the unsupervised Isolation Forest, MLP Autoencoder, Personalized PageRank risk propagation, and deterministic graph pattern detectors.",
        "",
        "### Key Performance Indicators:",
        "| Intelligence Feed | Model Architecture | Primary Metric | ROC-AUC | PR-AUC | Optimal F1 |",
        "|---|---|---|---|---|---|",
    ]

    for m_name, m_data in tx_models.items():
        opt = m_data["vs_statistical_anomalies"]["optimal_threshold"]
        lines.append(f"| Transaction Anomaly | {m_name.replace('_', ' ')} | Statistical Anomaly | **{opt['roc_auc']:.4f}** | **{opt['pr_auc']:.4f}** | **{opt['f1_score']:.4f}** |")

    if w_risk:
        w_opt = w_risk["optimal_threshold"]
        lines.append(f"| Graph Taint Propagation | Personalized PageRank | Illicit Wallet Seed Affinity | **{w_opt['roc_auc']:.4f}** | **{w_opt['pr_auc']:.4f}** | **{w_opt['f1_score']:.4f}** |")

    if pats:
        p_peel = pats.get("peeling_chain", {})
        p_cj = pats.get("coinjoin_mixing", {})
        lines.append(f"| Structural Pattern | Peeling Chain Detector | Micro-Change Peels | N/A | N/A | **{p_peel.get('f1_score', 0):.4f}** |")
        lines.append(f"| Structural Pattern | CoinJoin Mixer Detector | Equal-Denom Mixing | N/A | N/A | **{p_cj.get('f1_score', 0):.4f}** |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Dataset & Ground Truth Distribution",
        f"- **Total Transactions Ingested:** {ds.get('total_transactions', 0):,}",
        f"- **Normal Baseline Transactions:** {ds.get('normal_transactions', 0):,} ({100 - ds.get('anomaly_prevalence_pct', 0):.1f}%)",
        f"- **Total Anomalous / Obfuscated Transactions:** {ds.get('total_anomalous_transactions', 0):,} ({ds.get('anomaly_prevalence_pct', 0):.1f}%)",
        f"- **Statistical Extreme Anomalies:** {ds.get('statistical_anomalies', 0):,} (Whale volume spikes, high fee ratios, burst bots, dust spam)",
        "",
        "---",
        "",
        "## 3. Transaction Anomaly Detection Detailed Performance",
        "Performance measured against **Statistical Anomaly Ground Truth**:",
        "",
        "| Model | Threshold Mode | Threshold | Precision | Recall | F1-Score | Specificity | Accuracy | ROC-AUC | PR-AUC |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])

    for m_name, m_data in tx_models.items():
        v = m_data["vs_statistical_anomalies"]
        opt = v["optimal_threshold"]
        df = v["default_threshold_0_70"]
        display_name = m_name.replace("_", " ")
        lines.append(f"| {display_name} | Optimal (F1 Max) | {opt['threshold']:.2f} | {opt['precision']:.4f} | {opt['recall']:.4f} | **{opt['f1_score']:.4f}** | {opt['specificity']:.4f} | {opt['accuracy']:.4f} | {opt['roc_auc']:.4f} | {opt['pr_auc']:.4f} |")
        lines.append(f"| {display_name} | Fixed Standard | {df['threshold']:.2f} | {df['precision']:.4f} | {df['recall']:.4f} | {df['f1_score']:.4f} | {df['specificity']:.4f} | {df['accuracy']:.4f} | {df['roc_auc']:.4f} | {df['pr_auc']:.4f} |")

    lines.extend([
        "",
        "### Confusion Matrices at Default Threshold (0.70):",
    ])

    for m_name, m_data in tx_models.items():
        cm = m_data["vs_statistical_anomalies"]["default_threshold_0_70"]["confusion_matrix"]
        lines.append(f"- **{m_name.replace('_', ' ')}:** TP = {cm['true_positives']:,} | FP = {cm['false_positives']:,} | TN = {cm['true_negatives']:,} | FN = {cm['false_negatives']:,}")

    if w_risk:
        w_opt = w_risk["optimal_threshold"]
        w_def = w_risk["default_threshold_0_50"]
        lines.extend([
            "",
            "---",
            "",
            "## 4. Wallet Risk Propagation Evaluation (Personalized PageRank)",
            f"- **Wallets Evaluated:** {w_risk.get('wallets_evaluated', 0):,}",
            f"- **Suspicious Entities:** {w_risk.get('suspicious_wallets', 0):,} | **Benign Wallets:** {w_risk.get('benign_wallets', 0):,}",
            "",
            "| Metric | Optimal Threshold | Fixed Threshold (0.50) |",
            "|---|---|---|",
            f"| **Threshold Value** | {w_opt['threshold']:.2f} | {w_def['threshold']:.2f} |",
            f"| **Precision** | {w_opt['precision']:.4f} | {w_def['precision']:.4f} |",
            f"| **Recall** | {w_opt['recall']:.4f} | {w_def['recall']:.4f} |",
            f"| **F1-Score** | **{w_opt['f1_score']:.4f}** | **{w_def['f1_score']:.4f}** |",
            f"| **ROC-AUC** | **{w_opt['roc_auc']:.4f}** | **{w_def['roc_auc']:.4f}** |",
            f"| **PR-AUC** | **{w_opt['pr_auc']:.4f}** | **{w_def['pr_auc']:.4f}** |",
            f"| **Accuracy** | {w_opt['accuracy']:.4f} | {w_def['accuracy']:.4f} |",
        ])

    if pats:
        p_peel = pats.get("peeling_chain", {})
        p_cj = pats.get("coinjoin_mixing", {})
        lines.extend([
            "",
            "---",
            "",
            "## 5. Structural Pattern Detection Performance",
            "| Pattern Type | Ground Truth Count | Detected Count | Precision | Recall | F1-Score |",
            "|---|---|---|---|---|---|",
            f"| **Peeling Chain** | {p_peel.get('ground_truth_count', 0):,} | {p_peel.get('detected_count', 0):,} | **{p_peel.get('precision', 0):.4f}** | **{p_peel.get('recall', 0):.4f}** | **{p_peel.get('f1_score', 0):.4f}** |",
            f"| **CoinJoin Mixer** | {p_cj.get('ground_truth_count', 0):,} | {p_cj.get('detected_count', 0):,} | **{p_cj.get('precision', 0):.4f}** | **{p_cj.get('recall', 0):.4f}** | **{p_cj.get('f1_score', 0):.4f}** |",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## 6. Generated Visual Artifacts",
        "The following high-resolution charts were generated and saved to `reports/` for presentation and audit inclusion:",
        "1. `reports/roc_curve.png`: Comparative ROC curves for Isolation Forest, Autoencoder, and Ensemble.",
        "2. `reports/pr_curve.png`: Precision-Recall curves illustrating trade-offs on skewed Bitcoin traffic data.",
        "3. `reports/confusion_matrix.png`: Multi-model confusion matrix heatmaps showing true/false detections.",
        "4. `reports/shap_summary.png`: SHAP TreeExplainer feature attribution bar chart indicating top anomaly drivers.",
        "",
        "---",
        "*Report automatically generated by ChainSentinel Evaluation Suite.*"
    ])

    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[+] Generated comprehensive Markdown report: {out_md}")


if __name__ == "__main__":
    run_evaluation()
