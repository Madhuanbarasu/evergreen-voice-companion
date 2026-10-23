"""Evergreen chat client: Claude on Amazon Bedrock + the Evergreen MCP server (Streamable HTTP).
The Agent Skill (skills/evergreen-care/SKILL.md) is loaded as the system prompt.
Usage: python chat.py elder   |   python chat.py family
Env:   BEDROCK_MODEL_ID (a Claude model/inference profile enabled in your account), AWS_REGION, MCP_URL"""
import asyncio, os, sys
from pathlib import Path
import boto3
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")
MODEL = os.environ.get("BEDROCK_MODEL_ID", "REPLACE_WITH_YOUR_BEDROCK_MODEL_ID")
bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
SKILL = (Path(__file__).parent / "skills/evergreen-care/SKILL.md").read_text(encoding="utf-8")

async def main(role: str):
    who = ("You are Alexa+ speaking with the elder, Paati. Be warm and brief." if role == "elder"
           else "You are Alexa+ speaking with a family member of Paati. Use weekly_summary first.")
    system = [{"text": f"{who}\n\nFollow this skill:\n{SKILL}"}]
    async with streamablehttp_client(MCP_URL) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            cfg = {"tools": [{"toolSpec": {"name": t.name, "description": t.description or "",
                              "inputSchema": {"json": t.inputSchema}}} for t in tools]}
            msgs = []
            print(f"[{role} mode] tools: {[t.name for t in tools]}\nType 'quit' to exit.\n")
            while True:
                user = input("You: ").strip()
                if user.lower() in ("quit", "exit"): break
                msgs.append({"role": "user", "content": [{"text": user}]})
                while True:
                    resp = bedrock.converse(modelId=MODEL, system=system, messages=msgs, toolConfig=cfg)
                    msg = resp["output"]["message"]; msgs.append(msg)
                    if resp["stopReason"] != "tool_use":
                        print("Alexa+:", "".join(b.get("text", "") for b in msg["content"]), "\n"); break
                    results = []
                    for b in msg["content"]:
                        if "toolUse" in b:
                            tu = b["toolUse"]; print(f"  [tool] {tu['name']}({tu['input']})")
                            out = await session.call_tool(tu["name"], tu["input"])
                            text = "".join(c.text for c in out.content if hasattr(c, "text"))
                            results.append({"toolResult": {"toolUseId": tu["toolUseId"], "content": [{"text": text}]}})
                    msgs.append({"role": "user", "content": results})

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "elder"))
