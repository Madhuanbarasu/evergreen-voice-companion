"""Evergreen: an Alexa+ MCP server for elder care + reminiscence.
Transport: Streamable HTTP at /mcp. Family dashboard at /dashboard."""
import json, os, datetime as dt
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from starlette.responses import HTMLResponse, JSONResponse

DB = Path(os.environ.get("EVERGREEN_DB", "data.json"))
mcp = FastMCP("Evergreen", host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8000)),
              stateless_http=True, json_response=True)

PROMPTS = {
    "childhood": "What is your happiest memory from when you were little?",
    "family": "Tell me about your parents. What were they like?",
    "love": "How did you meet your husband or wife?",
    "work": "What was your first job, and what did you love about it?",
    "food": "What dish did you cook that everyone asked for?",
    "festival": "How did your family celebrate festivals when you were young?",
    "home": "Describe the house you grew up in.",
    "advice": "What is one piece of advice you want your grandchildren to remember?",
}

def load():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else {"people": {}}

def save(d):
    DB.write_text(json.dumps(d, indent=2), encoding="utf-8")

def person(d, name):
    return d["people"].setdefault(name.lower(), {"name": name, "meds": [], "checkins": [], "memories": []})

@mcp.tool()
def set_profile(name: str, medications: list[str]) -> dict:
    """Register an elder and their daily medications (e.g. ["BP tablet", "Vitamin D"])."""
    d = load(); p = person(d, name); p["meds"] = medications; save(d)
    return {"ok": True, "name": name, "medications": medications}

@mcp.tool()
def log_checkin(name: str, mood: int, meds_taken: list[str] = [], symptoms: str = "") -> dict:
    """Log a daily check-in. mood is 1 (very low) to 5 (great). meds_taken lists medications taken today."""
    d = load(); p = person(d, name)
    p["checkins"].append({"date": dt.date.today().isoformat(), "mood": max(1, min(5, mood)),
                          "meds_taken": meds_taken, "symptoms": symptoms})
    save(d)
    missed = [m for m in p["meds"] if m not in meds_taken]
    return {"ok": True, "missed_today": missed, "symptoms_noted": bool(symptoms)}

@mcp.tool()
def suggest_story_prompt(name: str) -> dict:
    """Pick a gentle reminiscence question on a theme the elder has not yet shared. Adapts to recent mood."""
    d = load(); p = person(d, name)
    done = {m["theme"] for m in p["memories"]}
    left = [t for t in PROMPTS if t not in done] or list(PROMPTS)
    recent = [c["mood"] for c in p["checkins"][-3:]]
    low = bool(recent) and sum(recent) / len(recent) < 2.5
    theme = "food" if low and "food" in left else left[0]
    return {"theme": theme, "question": PROMPTS[theme],
            "tone": "extra warm and brief; mood has been low" if low else "relaxed and curious"}

@mcp.tool()
def save_memory(name: str, theme: str, story: str, people_mentioned: list[str] = [], year: str = "") -> dict:
    """Save a story the elder told as a memory card for the family's life-story book."""
    d = load(); p = person(d, name)
    card = {"date": dt.date.today().isoformat(), "theme": theme, "story": story,
            "people": people_mentioned, "year": year}
    p["memories"].append(card); save(d)
    return {"ok": True, "total_memories": len(p["memories"]), "card": card}

@mcp.tool()
def weekly_summary(name: str) -> dict:
    """Analyse the last 7 days: mood trend, missed medication, symptoms, memories shared, and any alert flags."""
    d = load(); p = person(d, name)
    cutoff = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    week = [c for c in p["checkins"] if c["date"] >= cutoff]
    moods = [c["mood"] for c in week]
    half = len(moods) // 2
    trend = "not enough data"
    if half:
        a, b = sum(moods[:half]) / half, sum(moods[half:]) / (len(moods) - half)
        trend = "declining" if b < a - 0.5 else "improving" if b > a + 0.5 else "steady"
    missed = sum(len([m for m in p["meds"] if m not in c["meds_taken"]]) for c in week)
    symptoms = [c["symptoms"] for c in week if c["symptoms"]]
    mems = [m for m in p["memories"] if m["date"] >= cutoff]
    flags = []
    if trend == "declining": flags.append("Mood is trending down")
    if missed >= 3: flags.append(f"{missed} missed doses this week")
    if len(symptoms) >= 2: flags.append("Repeated symptoms reported")
    return {"name": p["name"], "checkins": len(week),
            "avg_mood": round(sum(moods) / len(moods), 1) if moods else None, "trend": trend,
            "missed_doses": missed, "symptoms": symptoms, "memories_this_week": len(mems),
            "latest_memory": mems[-1] if mems else None, "flags": flags,
            "alert": bool(flags)}


@mcp.tool()
def notify_family(name: str, message: str, urgency: str = "normal") -> dict:
    """Send an alert or update to the family. urgency: normal | urgent. Publishes to Amazon SNS if ALERT_SNS_TOPIC_ARN is set; always records it in outbox.json."""
    entry = {"time": dt.datetime.now().isoformat(timespec="seconds"), "about": name,
             "urgency": urgency, "message": message, "delivery": "outbox only"}
    topic = os.environ.get("ALERT_SNS_TOPIC_ARN")
    if topic:
        try:
            import boto3
            boto3.client("sns").publish(TopicArn=topic, Subject=f"Evergreen: {name} ({urgency})"[:100], Message=message)
            entry["delivery"] = "sent via Amazon SNS"
        except Exception as e:
            entry["delivery"] = f"SNS failed: {e}"
    box = Path("outbox.json")
    log = json.loads(box.read_text(encoding="utf-8")) if box.exists() else []
    log.append(entry); box.write_text(json.dumps(log, indent=2), encoding="utf-8")
    return entry

@mcp.custom_route("/api/summary/{name}", methods=["GET"])
async def api_summary(request):
    return JSONResponse(weekly_summary(request.path_params["name"]))

@mcp.custom_route("/api/memories/{name}", methods=["GET"])
async def api_memories(request):
    return JSONResponse(person(load(), request.path_params["name"])["memories"])

@mcp.custom_route("/dashboard", methods=["GET"])
async def dashboard(request):
    return HTMLResponse(Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8"))

@mcp.custom_route("/simulator", methods=["GET"])
async def simulator(request):
    return HTMLResponse(Path(__file__).with_name("simulator.html").read_text(encoding="utf-8"))

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
