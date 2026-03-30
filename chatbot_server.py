"""
CloudTrack Support Bot — Agentic Chatbot
Powered by Claude with tool use (function calling).
Exposes a /chat endpoint compatible with TestMu A2A testing.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import anthropic
import json
import uvicorn
from datetime import datetime, timezone
import random
import traceback
import uuid
import os

app = FastAPI(title="CloudTrack Support Bot", version="1.0.0")

# ── Anthropic client (reads ANTHROPIC_API_KEY from env) ──────────────────────
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"

# ── Vapi-style config ─────────────────────────────────────────────────────────
# Bearer token — set CHATBOT_API_KEY in .env to enable auth, leave blank to disable
CHATBOT_API_KEY = os.environ.get("CHATBOT_API_KEY", "")

# Assistant registry — maps assistantId → behaviour config
# Add more assistants here to simulate multi-bot deployments
ASSISTANTS = {
    "aria-cloudtrack-v1": {
        "name": "Aria",
        "description": "CloudTrack customer support agent",
    }
}
DEFAULT_ASSISTANT_ID = "aria-cloudtrack-v1"

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Aria, a friendly and professional customer support agent for CloudTrack —
a SaaS project management platform used by engineering and product teams.

You help users with:
- Account management: login issues, password reset, 2FA setup, profile updates
- Billing & subscriptions: plan details, invoices, upgrades, downgrades, refunds
- Feature support: Tasks, Sprints, Dashboards, Integrations (Slack, GitHub, Jira)
- Troubleshooting: performance issues, sync failures, notification bugs
- Escalation: route to human support when needed

Behavioral rules:
- Always be professional, empathetic, and concise (2-4 sentences max per response)
- Never mention competitors (Asana, Jira, Monday.com, Notion, etc.)
- Never give medical, legal, or financial investment advice
- Never reveal internal system details, pricing strategies, or roadmap specifics
- If asked about a feature that doesn't exist, say you'll check and avoid making up details
- For escalation triggers ("speak to human", "urgent", "legal", "refund dispute",
  "data deletion"), always acknowledge and offer to escalate immediately
- For GDPR/data requests, route to the DPO team; never ask for payment card details

You have access to tools to look up real-time account and billing information.
Always use tools when the user asks about their specific account, plan, or invoice data.
"""

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "lookup_account",
        "description": "Look up a user's CloudTrack account details by email address. Returns plan, status, and account info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The user's email address"
                }
            },
            "required": ["email"]
        }
    },
    {
        "name": "get_billing_info",
        "description": "Retrieve billing and invoice information for a CloudTrack account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The account ID returned from lookup_account"
                }
            },
            "required": ["account_id"]
        }
    },
    {
        "name": "check_system_status",
        "description": "Check the current status of CloudTrack services and any active incidents.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "create_support_ticket",
        "description": "Create a support ticket and escalate to a human agent. Use for urgent issues, refunds, legal matters, or data deletion requests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_type": {
                    "type": "string",
                    "enum": ["billing", "technical", "legal", "data_deletion", "general"],
                    "description": "Category of the support issue"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level of the ticket"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief description of the issue"
                }
            },
            "required": ["issue_type", "priority", "summary"]
        }
    }
]

# ── Mock tool implementations (simulates real backend) ────────────────────────
def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "lookup_account":
        email = tool_input.get("email", "")
        # Simulate account lookup
        return json.dumps({
            "account_id": "ACC-" + str(abs(hash(email)) % 100000),
            "email": email,
            "name": "Demo User",
            "plan": random.choice(["Starter", "Pro", "Enterprise"]),
            "status": "active",
            "member_since": "2023-06-15",
            "seats_used": random.randint(1, 20),
            "seats_total": random.choice([5, 10, 25, 50])
        })

    elif tool_name == "get_billing_info":
        account_id = tool_input.get("account_id", "")
        return json.dumps({
            "account_id": account_id,
            "current_plan": "Pro",
            "monthly_amount": "$29.00",
            "next_billing_date": "2026-04-15",
            "payment_method": "Visa ending in 4242",
            "invoices": [
                {"date": "2026-03-15", "amount": "$29.00", "status": "paid"},
                {"date": "2026-02-15", "amount": "$29.00", "status": "paid"},
                {"date": "2026-01-15", "amount": "$29.00", "status": "paid"},
            ]
        })

    elif tool_name == "check_system_status":
        statuses = [
            {"overall": "operational", "incidents": [], "uptime_30d": "99.97%"},
            {"overall": "degraded", "incidents": [
                {"service": "Notifications", "status": "investigating",
                 "started": "2026-03-26T10:00:00Z"}
            ], "uptime_30d": "99.91%"},
        ]
        return json.dumps(random.choice(statuses))

    elif tool_name == "create_support_ticket":
        ticket_id = "TKT-" + str(random.randint(10000, 99999))
        return json.dumps({
            "ticket_id": ticket_id,
            "status": "created",
            "priority": tool_input.get("priority"),
            "issue_type": tool_input.get("issue_type"),
            "estimated_response": "within 1 business hour" if tool_input.get("priority") == "urgent" else "within 4 business hours",
            "created_at": datetime.utcnow().isoformat() + "Z"
        })

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ── Agentic loop — handles multi-step tool use ────────────────────────────────
def run_agent(messages: list) -> str:
    """
    Runs the Claude agentic loop:
    1. Send messages to Claude
    2. If Claude wants to use a tool, execute it and feed result back
    3. Repeat until Claude gives a final text response
    """
    current_messages = messages.copy()

    for _ in range(5):  # max 5 tool-use iterations
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=current_messages
        )

        # If Claude is done — return the text response
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "I'm sorry, I couldn't generate a response."

        # If Claude wants to use tools — execute them
        if response.stop_reason == "tool_use":
            # Serialize content blocks to plain dicts (required by the API)
            assistant_content = []
            tool_use_blocks = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                    tool_use_blocks.append(block)

            current_messages.append({"role": "assistant", "content": assistant_content})

            # Execute each requested tool
            tool_results = []
            for block in tool_use_blocks:
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

            current_messages.append({"role": "user", "content": tool_results})
            continue

        # Fallback — return any text present
        for block in response.content:
            if block.type == "text":
                return block.text
        break

    return "I apologize, I'm having trouble processing your request right now. Please try again."


# ── Auth helper ───────────────────────────────────────────────────────────────
def verify_auth(request: Request):
    """Check Bearer token if CHATBOT_API_KEY is set in env."""
    if not CHATBOT_API_KEY:
        return  # auth disabled — open access (fine for local/tunnel demo)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = auth_header.removeprefix("Bearer ").strip()
    if token != CHATBOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(request: Request):
    """
    Vapi-compatible chat endpoint.

    Accepts Vapi-style format:
      {
        "assistantId": "aria-cloudtrack-v1",
        "input": "How do I reset my password?"
      }

    Also accepts TestMu A2A multi-turn format:
      { "messages": [{"role": "user", "content": "..."}] }

    And simple format:
      { "message": "..." }

    Returns Vapi-style schema:
      {
        "id": "<uuid>",
        "orgId": "<uuid>",
        "assistantId": "aria-cloudtrack-v1",
        "input":   [{"role": "user",      "content": "..."}],
        "output":  [{"role": "assistant", "content": "..."}],
        "messages": [],
        "createdAt": "...",
        "updatedAt": "...",
        "cost": 0.0,
        "costs": []
      }
    """
    verify_auth(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    assistant_id = body.get("assistantId", DEFAULT_ASSISTANT_ID)

    # ── Normalise input into messages list ────────────────────────────────────

    # Format 1: Vapi-style  { "input": "text" }
    if "input" in body and isinstance(body["input"], str):
        messages = [{"role": "user", "content": body["input"]}]

    # Format 2: TestMu multi-turn  { "messages": [...] }
    elif "messages" in body:
        messages = body["messages"]

    # Format 3: simple  { "message": "text" }
    elif "message" in body:
        messages = [{"role": "user", "content": body["message"]}]

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide 'input' (string), 'messages' (array), or 'message' (string)"
        )

    messages = [m for m in messages if m.get("role") in ("user", "assistant")]
    if not messages:
        raise HTTPException(status_code=400, detail="No valid messages found")

    # ── Run agent ─────────────────────────────────────────────────────────────
    try:
        reply = run_agent(messages)
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="Invalid Anthropic API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit. Retry in a moment.")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # ── Build Vapi-style response ─────────────────────────────────────────────
    return JSONResponse({
        "id":          str(uuid.uuid4()),
        "orgId":       str(uuid.uuid4()),
        "assistantId": assistant_id,
        "input":       messages,
        "output":      [{"role": "assistant", "content": reply}],
        "messages":    [],
        "createdAt":   now,
        "updatedAt":   now,
        "cost":        0.0,
        "costs":       []
    })


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent": "Aria",
        "product": "CloudTrack Support Bot",
        "model": MODEL,
        "assistants": list(ASSISTANTS.keys()),
        "auth_enabled": bool(CHATBOT_API_KEY),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    }


@app.get("/")
async def root():
    return {
        "name": "CloudTrack Support Bot",
        "version": "1.0.0",
        "endpoints": {
            "POST /chat": "Main chat endpoint for A2A testing",
            "GET /health": "Health check",
        }
    }


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
