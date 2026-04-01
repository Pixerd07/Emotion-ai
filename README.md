# EmotionMate — Hackathon voice agent

Two ways to run the same idea (**speech → understanding → supportive reply → speech**), aligned with the Oumi hackathon brief ([hack-with-oumi](https://github.com/oumi-ai/hack-with-oumi)).

## A) Primary (Pipecat + WebRTC UI) — matches Oumi template

Full voice loop with **local Whisper STT**, **local Kokoro TTS**, and a small **OpenAI-compatible “SLM shim”** (`/v1/chat/completions`) you can later replace with your **Oumi fine-tuned model** served behind `vLLM` / another OpenAI-compatible server.

See **`template/README.md`** for install and run steps:

- `template/server` — `python server.py`
- `template/client` — `npm install` && `npm run dev`

## B) Fallback (REST + static HTML) — fastest if WebRTC deps bite

- `backend/` — Flask API: `POST /analyze` (audio), `POST /analyze-text` (text)  
  Run with `python app.py` or `flask --app app run` — **not** `uvicorn` (that is for `template/server/server.py` only).
- `frontend/` — open `index.html` or `python -m http.server` from `frontend/`

## Oumi submission notes

- Requirement: use **Oumi** to fine-tune the language model in your final story; star the Oumi repo per their README.
- This repo ships a **working prototype lane** (sentiment + heuristics + scripted comforting replies) so you can demo **today**, then swap the shim URL in `template/server/server.py` for your **served SLM**.

## Repo layout

| Path | Role |
|------|------|
| `template/server` | Pipecat voice server + `/api/offer` + `/v1/chat/completions` |
| `template/client` | Next.js + `@pipecat-ai/voice-ui-kit` (from Oumi template) |
| `backend/` | Lightweight Flask REST for backup demos |
| `frontend/` | Simple recording UI + chart + browser TTS |
| `oumi-template-source/` | Upstream clone (reference only; safe to delete) |
