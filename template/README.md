# EmotionMate — Voice Agent (Hackathon build)

This folder follows the **Oumi “Hack with Oumi”** voice-agent layout ([hack-with-oumi](https://github.com/oumi-ai/hack-with-oumi)): **microphone → STT → agent → TTS → speaker**, using [Pipecat](https://github.com/pipecat-ai/pipecat) and the same Next.js + SmallWebRTC client pattern as the official template.

## What this prototype does

- **STT**: local Faster Whisper (via `pipecat-ai[whisper]`, CPU-friendly `tiny` by default).
- **“SLM lane”**: OpenAI-compatible `POST /v1/chat/completions` on the same server.  
  Pipecat’s `OpenAILLMService` calls it; the handler runs **sentiment + fusion + scripted supportive replies** (DistilBERT SST-2). Swap this for your **Oumi fine-tuned SLM** by pointing `OpenAILLMService` at `vLLM`/`Ollama` and removing the shim logic later.
- **TTS**: local Kokoro ONNX (via `pipecat-ai[kokoro]`).

## Requirements

- Python **3.10–3.12** recommended (3.11 is a safe default).
- Node.js **18+** for the client.
- A microphone + speakers in the browser.

## Install — server

```powershell
cd template\server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Optional env:

- `PIPECAT_HOST` (default `0.0.0.0`)
- `PIPECAT_PORT` (default `7860`)
- `WHISPER_DEVICE` (default `cpu`; use `cuda` if you have a GPU)
- `WHISPER_COMPUTE_TYPE` (default `int8`)

## Install — client

```powershell
cd template\client
npm install
```

The client proxies `/api/*` to the Pipecat server (see `next.config.ts`).

## Run

**Terminal 1 — Pipecat / FastAPI**

```powershell
cd template\server
.\.venv\Scripts\activate
python server.py --host 0.0.0.0 --port 7860
```

**Terminal 2 — Next.js UI**

```powershell
cd template\client
npm run dev
```

Open the URL printed by Next (usually `http://localhost:3000`). Allow microphone access, connect, and talk to **EmotionMate**.

## Verify backend only

- `GET http://127.0.0.1:7860/`
- `POST http://127.0.0.1:7860/v1/chat/completions` with `{"model":"emotionmate-slm","messages":[{"role":"user","content":"I feel overwhelmed"}],"stream":true}`

## Upgrade path for judging (Oumi SLM)

1. Fine-tune / serve a small model with **Oumi** (project requirement).
2. Run an OpenAI-compatible server (e.g. `vLLM-MLX` on Mac, or another compatible stack on your machine).
3. In `server.py`, set `OpenAILLMService.base_url` to that server and `model` to your served model name.
4. Optionally keep `/v1/chat/completions` as a **fallback** route for demos.

## Fallback lightweight UI

If WebRTC or Kokoro setup blocks you during the event, use the simple browser UI in the repo root `frontend/` + `backend/` (REST) as a backup demo while you fix GPU/audio deps.
