#!/usr/bin/env python3
"""
===================================================================================
ChainSentinel // AI-Powered Bitcoin Transaction Intelligence
MASTER PIPELINE RUNNER (Steps 1 through 6)
===================================================================================
Executes the full ChainSentinel intelligence pipeline from end to end:
1. Synthetic Generation (generate_dataset.py)
2. Ingestion & SQLite persistence (ingest.py)
3. Graph Construction & Common-Input Heuristic (graph_builder.py)
4. AI/ML Detection: Modules A, B, C, D
5. Alert Generation & Forensic Explainability (alert_generator.py)
6. Ready for Dashboard launch (streamlit run dashboard.py)
===================================================================================
"""

import os
import sys
import time
import subprocess


def run_cmd(cmd, desc):
    print(f"\n{'='*70}")
    print(f"[*] {desc}")
    print(f"    Command: {cmd}")
    print(f"{'='*70}")
    start = time.time()
    ret = subprocess.run(cmd, shell=True)
    if ret.returncode != 0:
        print(f"[!] Step failed with return code {ret.returncode}")
        sys.exit(ret.returncode)
    print(f"[✔] Completed in {time.time() - start:.2f}s")


def main():
    print("""
   ______  __            _           _____            __  _            __
  / ____/ / /_   ____ _ (_)____     / ___/___   ____ / /_(_)____  ___ / /
 / /     / __ \ / __ `// // __ \    \__ \ / _ \ / __ \/ __// // __ \ / _ \/ / 
/ /___  / / / // /_/ // // / / /   ___/ //  __// / / / /_ / // / / //  __/ /  
\____/ /_/ /_/ \__,_//_//_/ /_/   /____/ \___//_/ /_/\__//_//_/ /_/ \___/_/   
             AI-Powered Bitcoin Transaction Intelligence (SIH26146)
    """)

    py = sys.executable
    # Step 1: Synthetic Dataset Generation
    if not os.path.exists("transactions.csv"):
        run_cmd(f'"{py}" generate_dataset.py --count 8000', "STEP 1: Generating Synthetic Bitcoin Hybrid Dataset")
    else:
        print("[i] STEP 1: Found existing transactions.csv. Skipping generation.")

    # Step 2: Ingestion & Relational SQLite Persistence
    run_cmd(f'"{py}" ingest.py --input transactions.csv --db bitcoin_traffic.db', "STEP 2: Ingesting & Normalizing into SQLite Database")

    # Step 3: Graph Construction & Heuristics
    run_cmd(f'"{py}" graph_builder.py --db bitcoin_traffic.db --out graph.gpickle', "STEP 3: Building MultiDiGraph & Union-Find Clustering")

    # Step 4 & 5: AI/ML Detection & Alert Generation
    run_cmd(f'"{py}" alert_generator.py --db bitcoin_traffic.db --graph graph.gpickle --out alerts.json --top-n 150', "STEP 4 & 5: Executing 4 ML Modules & Alert Explainability")

    print("\n" + "="*70)
    print("ALL INTELLIGENCE PIPELINE STEPS (1-5) COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("To launch the ChainSentinel investigator dashboard, run:")
    print("   streamlit run dashboard.py\n")


if __name__ == "__main__":
    main()
