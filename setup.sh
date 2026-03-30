#!/bin/bash
# ============================================================
# SETUP — Install everything needed for the A2A demo
# ============================================================
set -e

echo ""
echo "🚀 CloudTrack A2A Demo — Setup"
echo "================================"

# 1. Check Python
echo ""
echo "→ Checking Python..."
if ! command -v python3 &>/dev/null; then
  echo "  ❌ Python 3 not found. Install from https://python.org"
  exit 1
fi
echo "  ✅ Python $(python3 --version)"

# 2. Install Python dependencies
echo ""
echo "→ Installing Python dependencies..."
pip3 install -r requirements.txt --quiet
echo "  ✅ fastapi, uvicorn, anthropic, python-dotenv installed"

# 3. Check for ANTHROPIC_API_KEY
echo ""
echo "→ Checking ANTHROPIC_API_KEY..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "  ⚠️  ANTHROPIC_API_KEY not set."
  echo ""
  echo "  Set it by running:"
  echo "    export ANTHROPIC_API_KEY='sk-ant-...'"
  echo "  Or add it to a .env file in this directory:"
  echo "    echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env"
else
  echo "  ✅ ANTHROPIC_API_KEY is set"
fi

# 4. Download TestMu Underpass tunnel binary
echo ""
echo "→ Setting up TestMu Underpass tunnel..."
if [ ! -f "./LT" ]; then
  echo "  Downloading Underpass for Mac..."
  curl -sL https://downloads.lambdatest.com/tunnel/v3/mac/64bit/LT_Mac.zip -o LT_Mac.zip
  unzip -q LT_Mac.zip
  chmod +x LT
  rm LT_Mac.zip
  echo "  ✅ Underpass binary ready (./LT)"
else
  echo "  ✅ Underpass binary already present"
fi

echo ""
echo "================================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start the chatbot:"
echo "     ./run_chatbot.sh"
echo ""
echo "  2. In a new terminal, start the tunnel:"
echo "     ./run_tunnel.sh YOUR_TESTMU_EMAIL YOUR_ACCESS_KEY"
echo ""
echo "  3. In TestMu A2A, use this as your bot URL:"
echo "     http://localhost:8000/chat"
echo ""
echo "  Get your access key at: testmuai.com → Profile → Access Key"
echo "================================================"
echo ""
