# CloudTrack A2A Demo — End-to-End Guide

Agent-to-Agent Testing demo using TestMu AI + an agentic Claude-powered chatbot.

---

## File Structure

```
a2a-demo/
├── cleanup.sh              ← Uninstall everything from previous setup
├── setup.sh                ← Install all dependencies + download tunnel
├── run_chatbot.sh          ← Start the agentic chatbot server
├── run_tunnel.sh           ← Start TestMu Underpass tunnel
├── run_local_tests.py      ← Validate bot locally before TestMu demo
├── chatbot_server.py       ← The agentic chatbot (Claude + tool use)
├── cloudtrack_prd.md       ← PRD doc to upload into TestMu A2A
├── requirements.txt        ← Python dependencies
└── .env                    ← (you create this) API keys
```

---

## Step 0 — Cleanup Previous Setup

```bash
chmod +x cleanup.sh && ./cleanup.sh
```

---

## Step 1 — Create .env File

```bash
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-your-key-here
TESTMU_USER=your@email.com
TESTMU_KEY=your-testmu-access-key
EOF
```

Get your TestMu access key at: **testmuai.com → Profile → Access Key**
Get your Anthropic key at: **console.anthropic.com → API Keys**

---

## Step 2 — Install & Setup

```bash
chmod +x setup.sh run_chatbot.sh run_tunnel.sh
./setup.sh
```

---

## Step 3 — Start the Chatbot

```bash
# Terminal 1
./run_chatbot.sh
```

You should see:
```
🤖 Starting CloudTrack Support Bot (Aria)...
   Port  : 8000
   URL   : http://localhost:8000
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

## Step 4 — Validate Locally (Optional but Recommended)

```bash
# Terminal 2 — run all 16 test scenarios
python3 run_local_tests.py

# With verbose output to see bot responses
python3 run_local_tests.py --verbose
```

Expected: 14–16/16 passing before you open TestMu.

---

## Step 5 — Start the Tunnel

```bash
# Terminal 2 (or 3 if running local tests)
./run_tunnel.sh
```

Wait for:
```
You can start testing now with tunnel name: cloudtrack-demo
```

---

## Step 6 — Run A2A in TestMu

1. Go to **testmuai.com** → **Agent to Agent Testing** → **Create Agent**
   - Name: `CloudTrack Support Bot`
   - Description: `Agentic customer support bot for CloudTrack SaaS`

2. Upload **`cloudtrack_prd.md`** as the requirements document

3. Select test categories:
   - ✅ Personality & Tone
   - ✅ Hallucination Detection
   - ✅ Out-of-Scope Handling
   - ✅ Escalation Flows
   - ✅ Compliance & Safety

4. Click **Generate Test Scenarios** — wait ~30–60 seconds

5. Enter bot URL:
   ```
   http://localhost:8000/chat
   ```

6. Click **Run Evaluation**

7. Review results under **Evaluation Results** tab

---

## What the Bot Can Do (Agentic Tools)

| Tool | Triggers On |
|------|-------------|
| `lookup_account` | "my account", user provides email |
| `get_billing_info` | invoice, billing, plan questions |
| `check_system_status` | "is it down?", performance complaints |
| `create_support_ticket` | escalation triggers (refund, legal, urgent, human) |

---

## Quick Smoke Tests

```bash
# Basic chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "How do I reset my password?"}]}'

# Escalation trigger (should create a ticket)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need a refund, this is urgent"}]}'

# Hallucination bait (should NOT confirm fake feature)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "How do I use the AI Autopilot feature?"}]}'

# Health check
curl http://localhost:8000/health
```

---

## Demo Talking Points

1. **Zero scripting** — the PRD doc is the only input; TestMu generates 30-50 scenarios automatically
2. **Agentic bot** — Aria uses live tool calls (account lookup, ticket creation) not canned responses
3. **Non-deterministic validation** — TestMu evaluates response quality holistically, not string matching
4. **HyperExecute parallelism** — all scenarios run simultaneously, not sequentially
5. **Rich metrics** — Hallucination, Toxicity, Escalation Accuracy, Tone, Competitor Avoidance
