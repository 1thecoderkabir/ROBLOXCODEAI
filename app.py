
import os
import hmac
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

APP_TOKEN = os.environ.get("APP_TOKEN")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "app": "RobloxDevAI",
        "message": "Backend is running!"
    })

@app.post("/api/chat")
def chat():
    # Check app authentication
    supplied_token = request.headers.get("X-App-Token", "")

    if not APP_TOKEN or not hmac.compare_digest(
        supplied_token, APP_TOKEN
    ):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    message = data.get("message", "").strip()
    mode = data.get("mode", "code")

    if not message:
        return jsonify({"error": "Please enter a message"}), 400

    if len(message) > 12000:
        return jsonify({"error": "Message is too long"}), 400

    if mode not in ["code", "debug", "search"]:
        return jsonify({"error": "Invalid mode"}), 400

    instructions = """
You are RobloxDevAI, an expert Roblox Luau developer.

Rules:
- Write correct Roblox Luau code.
- Use Roblox services and APIs correctly.
- Explain where scripts should be placed:
  ServerScriptService, StarterPlayerScripts,
  StarterGui, ReplicatedStorage, etc.
- Explain important parts of the code.
- Never claim code was tested unless it actually was.
- Point out security risks and server-side validation needs.
"""

    if mode == "debug":
        instructions += """
DEBUG MODE:
Find errors in the supplied Roblox Luau code.
Explain the problems and provide corrected code.
"""

    elif mode == "search":
        instructions += """
SEARCH MODE:
Search the web for relevant Roblox development information.
Prefer official Roblox Creator documentation and Roblox DevForum.
Summarize findings and include source links.
"""

    else:
        instructions += """
CODE MODE:
Generate Roblox Luau code for the user's requested feature.
Include setup instructions and explain where each script belongs.
"""

    try:
        tools = [{"type": "web_search"}] if mode == "search" else []

        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=message,
            tools=tools
        )

        answer = response.output_text or "No answer returned."
        sources = []

        # Collect web search source links and citations
        for item in response.output:
            if getattr(item, "type", "") == "web_search_call":
                action = getattr(item, "action", None)
                for source in getattr(action, "sources", []) or []:
                    url = getattr(source, "url", None)
                    title = getattr(source, "title", None)
                    if url:
                        sources.append({
                            "title": title or url,
                            "url": url
                        })

            for content in getattr(item, "content", []) or []:
                for annotation in getattr(content, "annotations", []) or []:
                    url = getattr(annotation, "url", None)
                    title = getattr(annotation, "title", None)
                    if url:
                        sources.append({
                            "title": title or url,
                            "url": url
                        })

        # Remove duplicate links
        unique_sources = []
        seen = set()

        for source in sources:
            if source["url"] not in seen:
                seen.add(source["url"])
                unique_sources.append(source)

        return jsonify({
            "success": True,
            "answer": answer,
            "sources": unique_sources,
            "mode": mode
        })

    except Exception:
        app.logger.exception("RobloxDevAI request failed")
        return jsonify({
            "error": "The AI request failed. Check your API configuration."
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
