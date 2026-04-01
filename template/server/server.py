import argparse
import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMTextFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMUserAggregatorParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.whisper.stt import Model as WhisperModel
from pipecat.services.whisper.stt import WhisperSTTService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from emotion_support import transcript_to_reply

load_dotenv(override=True)

pcs_map: Dict[str, SmallWebRTCConnection] = {}

SHIM_MODEL = "emotionmate-slm"
SYSTEM_INSTRUCTION = (
    "You are EmotionMate, a supportive voice companion. "
    "The model server returns short spoken responses based on the user's words."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    coros = [pc.disconnect() for pc in pcs_map.values()]
    await asyncio.gather(*coros)
    pcs_map.clear()


app = FastAPI(lifespan=lifespan)


def _last_user_text(messages: list) -> str:
    for msg in reversed(messages or []):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
            return "".join(parts).strip()
    return ""


def _chunk_line(
    *,
    completion_id: str,
    created: int,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None,
    include_usage: bool = False,
) -> str:
    choice: Dict[str, Any] = {"index": 0, "delta": delta, "finish_reason": finish_reason}
    payload: Dict[str, Any] = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [choice],
    }
    if include_usage and finish_reason == "stop":
        payload["usage"] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    return f"data: {json.dumps(payload)}\n\n"


def _stream_sse(*, model: str, reply: str, include_usage: bool) -> StreamingResponse:
    created = int(time.time())
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    async def gen():
        yield _chunk_line(
            completion_id=completion_id,
            created=created,
            model=model,
            delta={"role": "assistant", "content": ""},
            finish_reason=None,
        )
        words = reply.split()
        if not words:
            yield _chunk_line(
                completion_id=completion_id,
                created=created,
                model=model,
                delta={"content": ""},
                finish_reason=None,
            )
        else:
            for idx, word in enumerate(words):
                piece = word if idx == 0 else f" {word}"
                yield _chunk_line(
                    completion_id=completion_id,
                    created=created,
                    model=model,
                    delta={"content": piece},
                    finish_reason=None,
                )
        yield _chunk_line(
            completion_id=completion_id,
            created=created,
            model=model,
            delta={},
            finish_reason="stop",
            include_usage=include_usage,
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "EmotionMate Pipecat server",
        "routes": {
            "webrtc_offer": "POST /api/offer",
            "openai_compat": "POST /v1/chat/completions",
        },
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    body = await request.json()
    model = body.get("model") or SHIM_MODEL
    messages = body.get("messages") or []
    stream = bool(body.get("stream", False))
    stream_options = body.get("stream_options") or {}
    include_usage = bool(stream_options.get("include_usage")) if isinstance(stream_options, dict) else False

    user_text = _last_user_text(messages)
    reply = transcript_to_reply(user_text) if user_text else "I did not catch that. Could you say it again?"

    if stream:
        return _stream_sse(model=model, reply=reply, include_usage=include_usage)

    return JSONResponse(
        {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }
            ],
        }
    )


async def run_bot(webrtc_connection):
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        ),
    )

    stt = WhisperSTTService(
        model=WhisperModel.TINY,
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    )

    tts = KokoroTTSService(
        voice_id="af_heart",
        params=KokoroTTSService.InputParams(language=Language.EN),
    )

    port = int(os.getenv("PIPECAT_PORT", "7860"))
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY", "dummyKey"),
        model=SHIM_MODEL,
        base_url=f"http://127.0.0.1:{port}/v1",
        max_tokens=512,
    )

    context = OpenAILLMContext(
        [{"role": "system", "content": SYSTEM_INSTRUCTION}],
    )
    context_aggregator = llm.create_context_aggregator(
        context,
        user_params=LLMUserAggregatorParams(aggregation_timeout=0.05),
    )

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            rtvi,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=[RTVIObserver(rtvi)],
    )

    first_message = "Hi, I'm EmotionMate. How are you feeling today?"

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        await task.queue_frames([TTSSpeakFrame(first_message, append_to_context=True)])
        await task.queue_frames([LLMTextFrame(first_message)])

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"Participant joined: {participant}")
        await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant}")
        await task.cancel()

    @transport.event_handler("on_app_message")
    async def on_app_message(transport, message, sender):
        logger.info(f"Message from {sender}: {message}")

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


@app.post("/api/offer")
async def offer(request: dict, background_tasks: BackgroundTasks):
    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for pc_id: {pc_id}")
        await pipecat_connection.renegotiate(
            sdp=request["sdp"],
            type=request["type"],
            restart_pc=request.get("restart_pc", False),
        )
    else:
        pipecat_connection = SmallWebRTCConnection()
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)

        background_tasks.add_task(run_bot, pipecat_connection)

    answer = pipecat_connection.get_answer()
    pcs_map[answer["pc_id"]] = pipecat_connection
    return answer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EmotionMate Pipecat server")
    parser.add_argument("--host", default=os.getenv("PIPECAT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PIPECAT_PORT", "7860")))
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
