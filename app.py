"""
SEED Voice Bridge — a real Python (Flask) app.

Serves the frontend and proxies every Sunbird AI / NAROIR call itself, so the
Sunbird API key lives only as a server-side environment variable — it is
never sent to, or visible from, the browser. Frontend and backend are the
same origin, so there's no CORS to work around either.

Run locally:
    pip install -r requirements.txt
    export SUNBIRD_API_KEY=your-real-key   # optional — app runs in honest
                                            # fallback mode without it
    python app.py

Deploy: see README.md "Deploying" section (Hugging Face Spaces or Render).
"""
import os
import xml.etree.ElementTree as ET
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

SUNBIRD_API_KEY = os.environ.get("SUNBIRD_API_KEY", "")
SUNBIRD_BASE = "https://api.sunbird.ai"
NAROIR_SEARCH = "https://irbackend.naro.go.ug/server/opensearch/search"

REQUEST_TIMEOUT = 60
AUDIO_TIMEOUT = 120  # speech synthesis is slower than translate/chat — give it more room


def sunbird_headers():
    return {"Authorization": f"Bearer {SUNBIRD_API_KEY}", "Content-Type": "application/json"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Lets the frontend show an honest status indicator without exposing the key itself."""
    return jsonify({"key_configured": bool(SUNBIRD_API_KEY)})


@app.route("/api/naroir/search")
def naroir_search():
    """Live search against NARO's real institutional repository.

    Fetches a larger candidate pool from NAROIR, then filters server-side so
    every word in the search term actually has to appear in the title or
    abstract — NAROIR's own relevance ranking alone was pulling in loosely
    related items (e.g. a "bean" search surfacing unrelated governance
    documents). Returns clean JSON instead of raw Atom XML.
    """
    query = (request.args.get("query") or "").strip()
    if not query:
        query = "*"

    try:
        r = requests.get(
            NAROIR_SEARCH,
            params={"format": "atom", "query": query, "count": 25},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": f"NAROIR request failed: {e}"}), 502

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return jsonify({"error": "Could not parse NAROIR response"}), 502

    ns = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(f"{ns}entry")

    # Every word (3+ chars) in the query must appear in the title or abstract.
    # This is what actually enforces precision — NAROIR's own ranking alone
    # isn't strict enough and was surfacing tangential results.
    terms = [t.lower() for t in query.split() if len(t) >= 3] if query != "*" else []

    results = []
    for entry in entries:
        title_el = entry.find(f"{ns}title")
        link_el = entry.find(f"{ns}link")
        published_el = entry.find(f"{ns}published")
        summary_el = entry.find(f"{ns}summary")

        title = (title_el.text or "Untitled").strip() if title_el is not None else "Untitled"
        link = link_el.get("href", "") if link_el is not None else ""
        year = (published_el.text or "")[:4] if published_el is not None else ""

        summary_text = (summary_el.text or "") if summary_el is not None else ""
        marker = "dc.description.abstract:"
        idx = summary_text.find(marker)
        abstract = summary_text[idx + len(marker):] if idx != -1 else summary_text
        abstract = " ".join(abstract.split())[:480]

        haystack = f"{title} {abstract}".lower()
        if terms and not all(term in haystack for term in terms):
            continue

        results.append({"title": title, "link": link, "year": year, "abstract": abstract})
        if len(results) >= 5:
            break

    return jsonify({"results": results, "candidates_scanned": len(entries)})


@app.route("/api/simplify", methods=["POST"])
def simplify():
    if not SUNBIRD_API_KEY:
        return jsonify({"error": "Server is missing SUNBIRD_API_KEY — set it as an environment variable / secret."}), 500

    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    payload = {
        "model": "sunflower-14b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Rewrite the given Ugandan agricultural research text in 2-3 short, "
                    "plain-language sentences a smallholder farmer would understand if read "
                    "aloud on the radio. No jargon, no preamble — output only the rewritten text."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    try:
        r = requests.post(f"{SUNBIRD_BASE}/tasks/chat/completions", headers=sunbird_headers(), json=payload, timeout=REQUEST_TIMEOUT)
        data = r.json()
    except requests.RequestException as e:
        return jsonify({"error": f"Sunflower request failed: {e}"}), 502
    except ValueError:
        return jsonify({"error": "Sunflower returned a non-JSON response"}), 502

    if not r.ok:
        return jsonify({"error": data.get("message") or data.get("detail") or r.reason}), r.status_code

    choices = data.get("choices") or []
    content = choices[0].get("message", {}).get("content") if choices else None
    if not content:
        return jsonify({"error": "No content in Sunflower response"}), 502
    return jsonify({"simplified": content.strip()})


@app.route("/api/translate", methods=["POST"])
def translate():
    if not SUNBIRD_API_KEY:
        return jsonify({"error": "Server is missing SUNBIRD_API_KEY — set it as an environment variable / secret."}), 500

    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    target_language = body.get("target_language", "")
    if not text or not target_language:
        return jsonify({"error": "Missing 'text' or 'target_language'"}), 400

    try:
        r = requests.post(
            f"{SUNBIRD_BASE}/tasks/translate",
            headers=sunbird_headers(),
            json={"source_language": "eng", "target_language": target_language, "text": text},
            timeout=REQUEST_TIMEOUT,
        )
        data = r.json()
    except requests.RequestException as e:
        return jsonify({"error": f"Translate request failed: {e}"}), 502
    except ValueError:
        return jsonify({"error": "Translate endpoint returned a non-JSON response"}), 502

    if not r.ok:
        return jsonify({"error": data.get("message") or data.get("detail") or r.reason}), r.status_code

    translated = (data.get("output") or {}).get("translated_text")
    if not translated:
        return jsonify({"error": "No translated_text in response"}), 502
    return jsonify({"translated_text": translated})


@app.route("/api/voice/speakers")
def voice_speakers():
    if not SUNBIRD_API_KEY:
        return jsonify({"error": "Server is missing SUNBIRD_API_KEY — set it as an environment variable / secret."}), 500
    try:
        r = requests.get(f"{SUNBIRD_BASE}/tasks/voice/speakers", headers={"Authorization": f"Bearer {SUNBIRD_API_KEY}"}, timeout=REQUEST_TIMEOUT)
        data = r.json()
    except requests.RequestException as e:
        return jsonify({"error": f"Voice catalog request failed: {e}"}), 502
    except ValueError:
        return jsonify({"error": "Voice catalog returned a non-JSON response"}), 502
    return jsonify(data), r.status_code


@app.route("/api/voice/speech", methods=["POST"])
def voice_speech():
    if not SUNBIRD_API_KEY:
        return jsonify({"error": "Server is missing SUNBIRD_API_KEY — set it as an environment variable / secret."}), 500

    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    voice = body.get("voice", "")
    if not text or not voice:
        return jsonify({"error": "Missing 'text' or 'voice'"}), 400

    try:
        r = requests.post(
            f"{SUNBIRD_BASE}/tasks/audio/speech",
            headers=sunbird_headers(),
            json={"text": text, "voice": voice, "response_mode": "url"},
            timeout=AUDIO_TIMEOUT,
        )
        data = r.json()
    except requests.RequestException as e:
        return jsonify({"error": f"Speech request failed: {e}"}), 502
    except ValueError:
        return jsonify({"error": "Speech endpoint returned a non-JSON response"}), 502

    if not r.ok:
        return jsonify({"error": data.get("message") or data.get("detail") or r.reason}), r.status_code

    audio_url = data.get("audio_url") or (data.get("output") or {}).get("audio_url")
    if not audio_url:
        return jsonify({"error": "No audio_url in response"}), 502
    return jsonify({"audio_url": audio_url})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
