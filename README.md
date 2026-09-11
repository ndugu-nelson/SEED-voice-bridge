---
title: SEED Voice Bridge
emoji: 📻
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# 📻 SEED Voice Bridge

**Research findings, in the language people already listen in.**

A real Python (Flask) app for *Breaking the Wall of Farm Radio Translation* — it queries NARO's real research repository, simplifies a finding, translates it into a Ugandan local language, generates spoken audio, and lays out a regional radio broadcast plan.

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen?style=for-the-badge)](#-live-demo)
[![Python](https://img.shields.io/badge/backend-Python%20%2F%20Flask-3776AB?style=for-the-badge&logo=python&logoColor=white)]()
[![Powered by Sunbird AI](https://img.shields.io/badge/NLP-Sunbird%20AI-D9A441?style=for-the-badge)](https://sunbird.ai)
[![License](https://img.shields.io/badge/license-MIT-lightgrey?style=for-the-badge)]()

<br>

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────┐      ┌────────────────────────┐
│  app.py  (Flask — Python)                          │ ───▶ │  Upstream APIs          │
│  serves templates/index.html AND the /api/* routes │      │  NAROIR · Sunbird AI     │
│  holds SUNBIRD_API_KEY as a server env var          │      │  (real key sent here,    │
│  — same origin, no CORS, key never reaches the      │      │   server-to-server only) │
│  browser                                            │      │                          │
└───────────────────────────────────────────────────┘      └────────────────────────┘
```

One process serves both the page and the API. The browser only ever talks to this app's own `/api/...` routes — it never calls Sunbird or NAROIR directly, and the Sunbird key is never sent to, or visible from, the browser.

<br>

## 🔗 Live demo

> **`https://huggingface.co/spaces/<your-username>/seed-voice-bridge`**
> *(update this once deployed — see below)*

<br>

## 📸 Preview

![SEED Voice Bridge running the full Search → Simplify → Localize → Voice → Distribute pipeline](docs/screenshot.png)

<br>

## ✨ What it does

| Step | What happens |
|---|---|
| **0. Search NAROIR** | Queries NARO's real institutional repository (**NAROIR**, at `irbackend.naro.go.ug`) for actual published findings matching your search term. |
| **1. Simplify** | Rewrites the selected finding into plain language via **Sunflower**, Sunbird AI's own LLM (OpenAI-compatible chat API). |
| **2. Localize** | Routes the plain-language text into one of five Ugandan languages — Luganda, Runyankole, Ateso, Acholi, Lugbara — via [Sunbird AI](https://sunbird.ai)'s translation API. |
| **3. Voice** | Generates spoken audio in that language via Sunbird AI's text-to-speech models, one native voice per language. |
| **4. Distribute** | Produces a regional broadcast plan mapping each language to its FM audience and existing farm-clinic radio slots. |

**Honest either way:** if `SUNBIRD_API_KEY` isn't set, or a downstream call to Sunbird/NAROIR fails, that specific step says so explicitly on screen and falls back to clearly labeled cached/offline content — a real cached snapshot of NARO findings for search, the unsimplified original text for Simplify, a browser voice for Voice. Nothing pretends to be live when it isn't. A status indicator at the bottom of the left panel shows whether the backend currently has its key configured.

<br>

## 🧱 Tech stack

- **Backend:** Python 3 / [Flask](https://flask.palletsprojects.com/), served with [gunicorn](https://gunicorn.org/) — `app.py`
- **Frontend:** a single Jinja-rendered template, vanilla HTML/CSS/JS, no build step — `templates/index.html`
- [NAROIR](https://researchspace.naro.go.ug) — NARO's public DSpace research repository, queried live via its OpenSearch feed
- [Sunbird AI](https://sunbird.ai) — Sunflower LLM (simplify), translation, and text-to-speech API for 5 Ugandan languages (SALT dataset)
- Browser `SpeechSynthesis` API — offline fallback voice

<br>

## 💻 Running locally

```bash
pip install -r requirements.txt
export SUNBIRD_API_KEY=your-real-key   # optional — app runs in honest fallback mode without it
python app.py
```

Then open `http://localhost:7860`.

<br>

## 🚀 Deploying — Hugging Face Spaces (recommended, free)

Spaces stays up on the free tier (no cold sleep the way some free web-service tiers have), and the Docker SDK runs this exact Flask app unmodified.

1. Create a free account at [huggingface.co](https://huggingface.co) if you don't have one.
2. **New → Space.** Pick a name (e.g. `seed-voice-bridge`), select **Docker** as the SDK, and set visibility to Public.
3. Push this repo's contents to the Space (Spaces are just git repos): either use the web uploader, or
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/seed-voice-bridge
   git push space main
   ```
4. In the Space's **Settings → Variables and secrets**, add a secret named `SUNBIRD_API_KEY` with your real key. It's encrypted and never shown in the UI or logs again.
5. The Space builds automatically from the `Dockerfile` and comes up at `https://huggingface.co/spaces/<your-username>/seed-voice-bridge`.
6. Update the **Live demo** link at the top of this README with that URL.

<br>

## 🚀 Alternative: Render (also free tier)

1. Push this repo to GitHub.
2. On [render.com](https://render.com), **New → Web Service**, connect the repo.
3. Render will detect the `Dockerfile` automatically — no other config needed.
4. Under **Environment**, add `SUNBIRD_API_KEY` with your real key.
5. Deploy — Render gives you a `https://<app-name>.onrender.com` URL.

> Note: Render's free tier spins the service down after inactivity, so the first request after a while can take ~30-60 seconds to wake up. Fine for casual use; worth a warm-up request a few minutes before a live pitch.

<br>

## 🐙 Also hosting the source on GitHub

GitHub itself only serves static files, so it can't *run* this app — but it's still the natural place to keep the source and point people to. Push the repo there as usual; the badges above link out to wherever you actually deploy it (Hugging Face Spaces or Render).

<br>

## 🔒 A note on the API key

There is no API key field anywhere in the UI. `SUNBIRD_API_KEY` is read once, server-side, from an environment variable / platform secret, and is never sent to, stored in, or visible from the browser. Visitors and judges can use the live demo without ever needing a key of their own.

> **Never commit `SUNBIRD_API_KEY` into this repo, in any form.** Set it only via your hosting platform's secrets manager (Hugging Face Spaces secrets, Render environment variables, or a local `export` for development).

<br>

## ⚠️ Disclaimer

Built for pitch/demo purposes. Translation drafts and cached-snapshot findings are clearly labeled and drawn from NARO's own published materials. Sunbird AI and NAROIR facts are drawn from their public materials as of 2025/2026.
