# 🌿 Evergreen: an Alexa+ companion for elder care and life stories

**Track:** Alexa+ | **Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon
**Demo video:** `PASTE_YOUR_PUBLIC_VIDEO_URL_HERE`

Families often can't see how an elderly parent is really doing, and the stories of a whole generation are never written down.
Evergreen is a self-hosted **MCP server** for Alexa+. The elder talks to Alexa+ about their day. Evergreen logs mood and
medicines, notices worrying trends, and gently collects life stories as memory cards. The family gets a weekly summary,
alerts, and a dashboard with a "life-story book".

> **Not medical advice.** Evergreen is a hackathon prototype. It does not diagnose anything and must not replace a doctor or emergency services.
> All data in this repo is invented demo data ("Paati"), not a real person.

## Features

| Feature | How it works |
|---|---|
| Daily check-in | `log_checkin` records mood (1-5), medicines taken, and symptoms; returns which doses were missed |
| Story prompts | `suggest_story_prompt` picks a reminiscence theme not yet shared; tone adapts when recent mood is low |
| Life-story book | `save_memory` stores the elder's story as a memory card (theme, year, people) |
| Weekly summary | `weekly_summary` computes mood trend, missed doses, repeated symptoms, and alert flags (simple rules, no ML) |
| Family alerts | `notify_family` always writes to `outbox.json`; also publishes to Amazon SNS if `ALERT_SNS_TOPIC_ARN` is set |
| Persistent state | Everything is saved in `data.json`, so it survives restarts and new sessions |
| Family dashboard | `/dashboard?name=paati`: alert card, stats, memory cards |
| Agent Skill | `skills/evergreen-care/SKILL.md` tells an agent how to orchestrate the tools for elder vs family |
| **Alexa+-style simulator** | `/simulator`: a *prototype* chat page that calls the real MCP tools (see below) |

## Architecture

```
 Elder / Family  ──►  Alexa+ (or the simulator / chat.py / MCP Inspector)
                              │  MCP, Streamable HTTP (spec 2025-11-25)
                              ▼
                 server.py  (official `mcp` Python SDK, FastMCP, POST /mcp)
                   6 tools ──► data.json (state)   notify_family ──► outbox.json (+ optional Amazon SNS)
                              │
                 /dashboard  /api/summary/{name}  /api/memories/{name}  /simulator
```

## Setup and run on Windows (PowerShell)

Requirements: Python 3.10+ and Node.js (only for the optional MCP Inspector).

```powershell
git clone https://github.com/YOUR_USERNAME/evergreen.git
cd evergreen
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python server.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` first, then activate again.

The server listens on `http://127.0.0.1:8000` (set `$env:PORT` or `$env:HOST` to change; it binds to localhost by default).

Open in your browser:
- Simulator: http://127.0.0.1:8000/simulator
- Family dashboard: http://127.0.0.1:8000/dashboard?name=paati
- MCP endpoint: http://127.0.0.1:8000/mcp

macOS/Linux: use `python3 -m venv .venv && source .venv/bin/activate`; the rest is identical.

Run `python seed.py` again at any time to reset the demo data.

### Test the MCP server with MCP Inspector

In a second terminal:

```powershell
npx @modelcontextprotocol/inspector
```

Choose transport **Streamable HTTP**, URL `http://127.0.0.1:8000/mcp`, click **Connect**, then **Tools → List Tools**, and run e.g. `weekly_summary` with `{"name": "Paati"}`.

### Alexa+-style simulator (prototype)

`/simulator` is **not** connected to a real Alexa+ device or account. It is a small rule-based chat page (no LLM) that sends
JSON-RPC `tools/call` requests to the real `/mcp` endpoint, and shows every tool call and result live next to the chat.
Use the *Elder* tab for a check-in and a story, and the *Family* tab for the weekly summary and an alert.

### Browser voice (Alexa+-style prototype)

The simulator has a 🎤 button next to the message box. Click it, speak (e.g. *"Alexa, I feel dizzy today"*), and the text goes through
the same flow as typing, calling the real MCP tools. Replies are read aloud with `speechSynthesis`. A leading "Alexa" is removed
(checkbox, on by default). This is **click-to-talk in the browser (Web Speech API), not real Alexa+ integration and not wake-word detection**.
Use Chrome or Edge; Chrome/Edge send audio to their speech service, so it needs internet. Typing always works.

### Optional: Claude on Amazon Bedrock chat client

`chat.py` is a terminal client that runs Claude through the Amazon Bedrock Converse API with tool use against the MCP server,
loading the Agent Skill as the system prompt. It needs your own AWS credentials and Bedrock model access:

```powershell
$env:AWS_REGION = "us-east-1"
$env:BEDROCK_MODEL_ID = "<a Claude model or inference profile enabled in your account>"
python chat.py elder
python chat.py family
```

Optional SNS delivery for family alerts: `$env:ALERT_SNS_TOPIC_ARN = "<your topic ARN>"` before `python server.py`.

## What has been tested

- ✅ MCP `initialize` (protocol `2025-11-25`), `tools/list` (6 tools), and a call to every tool through the official Python MCP client
- ✅ Dashboard, memory cards, and the simulator page exercised end to end against a running server
- ⚠️ `chat.py` (Bedrock) and Amazon SNS delivery: **written but not verified against a real AWS account**

## Limitations

- Prototype only: the weekly analysis is simple rules (thresholds on mood, missed doses, symptoms), not a clinical model.
- Single-user JSON file storage, no authentication, no encryption. Do not store real personal or health data. Do not expose it to the internet as is.
- Not tested on a real Alexa+ device or account; the simulator is a stand-in.
- Amazon SNS and Bedrock paths are untested (see above). Without SNS configured, alerts only go to `outbox.json`.
- Medicines are matched by exact name strings.

## License

MIT, see [LICENSE](LICENSE).
