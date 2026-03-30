#!/bin/bash
# ============================================================
# START CHATBOT — Run the Aria agentic chatbot server
# ============================================================

# Load .env file if it exists
if [ -f ".env" ]; then
  export $(cat .env | grep -v '#' | xargs)
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "❌ ANTHROPIC_API_KEY is not set."
  echo "   Run: export ANTHROPIC_API_KEY='sk-ant-...'"
  echo "   Or create a .env file with: ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

echo ""
echo "🤖 Starting CloudTrack Support Bot (Aria)..."
echo "   Model : claude-haiku-4-5-20251001"
echo "   Port  : 8000"
echo "   URL   : http://localhost:8000"
echo ""
echo "Endpoints:"
echo "   POST http://localhost:8000/chat   ← TestMu A2A uses this"
echo "   GET  http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop."
echo ""

python3 chatbot_server.py
