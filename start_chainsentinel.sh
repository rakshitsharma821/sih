#!/usr/bin/env bash
# ==============================================================================
# ChainSentinel // SIH26146: AI-Powered Bitcoin Transaction Intelligence
# Linux Offline Launcher (POSIX Compliant)
# National Technical Research Organisation (NTRO) - Smart India Hackathon 2026
# ==============================================================================

set -e

# Terminal Colors
CYAN='[0;36m'
GREEN='[0;32m'
YELLOW='[1;33m'
RED='[0;31m'
NC='[0m' # No Color

echo -e "${CYAN}"
echo "========================================================================"
echo "    ChainSentinel ? Bitcoin Transaction Traffic Forensics SOC"
echo "    SIH26146 // National Technical Research Organisation (NTRO)"
echo "            100% AIR-GAPPED / LOCAL OFFLINE MODE"
echo "========================================================================"
echo -e "${NC}"

# 1. Detect Python 3 Environment
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo -e "${RED}[!] Error: Neither python3 nor python was found in PATH.${NC}"
    echo "    Please install Python 3.10+ (e.g., sudo apt install python3 python3-venv)"
    exit 1
fi

PY_VER=$($PYTHON_BIN -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
echo -e "${GREEN}[+] Detected Python interpreter: $PYTHON_BIN (v$PY_VER)${NC}"

# 2. Check Virtual Environment (if exists)
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo -e "${GREEN}[+] Activating virtual environment: ./venv${NC}"
    source venv/bin/activate
    PYTHON_BIN="python"
elif [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo -e "${GREEN}[+] Activating virtual environment: ./.venv${NC}"
    source .venv/bin/activate
    PYTHON_BIN="python"
fi

# 3. Verify Required Core Dependencies
echo -e "${CYAN}[*] Verifying critical forensics libraries...${NC}"
$PYTHON_BIN -c "
mods = ['fastapi', 'uvicorn', 'networkx', 'sklearn', 'pandas', 'numpy', 'shap']
missing = []
for m in mods:
    try:
        __import__(m)
    except ImportError:
        missing.append(m)
if missing:
    print('MISSING:' + ','.join(missing))
else:
    print('ALL_OK')
" > /tmp/chainsentinel_depcheck.txt 2>/dev/null || true

if [ -f /tmp/chainsentinel_depcheck.txt ] && grep -q "MISSING" /tmp/chainsentinel_depcheck.txt; then
    MISSING_PKGS=$(cat /tmp/chainsentinel_depcheck.txt | cut -d':' -f2)
    echo -e "${YELLOW}[!] Warning: Missing recommended packages: $MISSING_PKGS${NC}"
    echo -e "    Run: pip install -r requirements.txt"
else
    echo -e "${GREEN}[+] All core ML & graph forensic dependencies confirmed.${NC}"
fi
rm -f /tmp/chainsentinel_depcheck.txt 2>/dev/null || true

# 4. Verify Local Database and Graph Artifacts
echo -e "${CYAN}[*] Checking forensic database and graph caches...${NC}"
if [ ! -f "bitcoin_traffic.db" ]; then
    echo -e "${YELLOW}[!] Notice: bitcoin_traffic.db not found. Running pipeline initialization...${NC}"
    $PYTHON_BIN run_pipeline.py
fi

# 5. Trap Signals for Graceful Teardown
cleanup() {
    echo -e "
${YELLOW}[*] Shutting down ChainSentinel Forensics Node gracefully...${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# 6. Launch FastAPI + React Forensic SOC
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo -e "${GREEN}"
echo "========================================================================"
echo " [OK] ChainSentinel Forensic Engine is LIVE!"
echo "      - Web Dashboard:     http://localhost:$PORT"
echo "      - REST API Swagger:  http://localhost:$PORT/docs"
echo "      - Ingestion Console: http://localhost:$PORT/ingest-console"
echo "========================================================================"
echo -e "${NC}"

exec $PYTHON_BIN api.py --host "$HOST" --port "$PORT"
