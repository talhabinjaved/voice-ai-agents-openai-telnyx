import os
import json
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .utils.telnyx_http import telnyx_cmd

load_dotenv()

# -----------------------------
# Config & logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PUBLIC_DOMAIN = os.getenv("DOMAIN")

# Voice & prompting
AGENT_VOICE = os.getenv("AGENT_VOICE", "marin")  # alloy|marin|...
AGENT_INSTRUCTIONS = os.getenv(
    "AGENT_INSTRUCTIONS",
    "You are a helpful voice assistant. Greet warmly, then help succinctly. "
    "Keep responses concise but informative. Be friendly and professional."
)
AGENT_GREETING = os.getenv(
    "AGENT_GREETING",
    "Hi! Thanks for calling. How can I help you today?"
)

if not TELNYX_API_KEY or not PUBLIC_DOMAIN or not OPENAI_API_KEY:
    raise RuntimeError("Missing required env vars: TELNYX_API_KEY, OPENAI_API_KEY, DOMAIN")

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Health endpoint
# -----------------------------
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

# -----------------------------
# Telnyx webhook
# -----------------------------
@app.post("/webhook")
async def telnyx_webhook(request: Request):
    event = await request.json()
    logger.info(f"Received Telnyx webhook: {json.dumps(event, indent=2)}")

    data = event.get("data", {})
    payload = data.get("payload", {})
    ev_type = data.get("event_type") or data.get("type") or data.get("record_type")
    call_control_id = payload.get("call_control_id")

    if not call_control_id:
        logger.warning("No call_control_id in webhook event")
        return JSONResponse({"status": "ignored", "reason": "missing call_control_id"})

    if ev_type == "call.initiated":
        logger.info(f"Answering call {call_control_id}")
        await telnyx_cmd(call_control_id, "answer", TELNYX_API_KEY)

        # Start media streaming to our WS with bidirectional RTP (PCMU)
        stream_url = f"wss://{PUBLIC_DOMAIN}/telnyx_media"
        body = {
            "stream_url": stream_url,
            # Which leg to fork TO US – matches Telnyx docs (inbound_track/outbound_track/both_tracks)
            "stream_track": "inbound_track",
            # Enable bidirectional RTP so we can send audio back to the call
            "stream_bidirectional_mode": "rtp",
            "stream_bidirectional_codec": "PCMU",
        }
        await telnyx_cmd(call_control_id, "streaming_start", TELNYX_API_KEY, body)
        logger.info(f"Started media streaming for call {call_control_id}")

    elif ev_type == "call.hangup":
        logger.info(f"Call {call_control_id} ended")

    return JSONResponse({"status": "ok"})

# -----------------------------
# Telnyx Media WebSocket
# -----------------------------
@app.websocket("/telnyx_media")
async def telnyx_media(ws: WebSocket):
    await ws.accept()
    logger.info("Telnyx media WebSocket connection accepted")

    import websockets

    openai_ws = None
    forward_task = None
    stream_id = None
    call_control_id = None

    try:
        # Wait for Telnyx 'start' frame to get stream/call ids
        start_received = False
        while not start_received:
            data = await ws.receive_json()
            if data.get("event") == "start":
                stream_id = data.get("stream_id")
                start_data = data.get("start", {})
                call_control_id = start_data.get("call_control_id")
                logger.info(
                    f"Media stream started for call {call_control_id}, stream {stream_id}"
                )
                start_received = True
            elif data.get("event") in ("stop", "callEnded"):
                logger.info("Media stream ended before start")
                return

        # Connect to OpenAI Realtime API over WebSocket
        uri = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }

        openai_ws = await websockets.connect(
            uri, additional_headers=headers, ping_interval=20, ping_timeout=10
        )
        logger.info("Connected to OpenAI Realtime API")

        # --- Correct Realtime session.update (includes session.type, nested audio, modalities) ---
        session_update = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": "gpt-realtime",
                # lock output to audio; add "text" here if you also want text deltas
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        # Telnyx is sending PCMU frames; configure model to expect PCMU
                        "format": {"type": "audio/pcmu"},
                        "turn_detection": {
                            "type": "semantic_vad",
                            # Let the server auto-create a response when the user stops speaking
                            "create_response": True
                        },
                    },
                    "output": {
                        # We will forward these chunks directly back to Telnyx
                        "format": {"type": "audio/pcmu"},
                        "voice": AGENT_VOICE,
                    },
                },
                "instructions": AGENT_INSTRUCTIONS,
                # tools & tool_choice can be added here as needed
            },
        }

        await openai_ws.send(json.dumps(session_update))
        logger.info("Sent session configuration to OpenAI")

        # Wait for session confirmation
        session_event_raw = await openai_ws.recv()
        session_event = json.loads(session_event_raw)
        logger.info(f"OpenAI session status: {session_event.get('type')}")

        # --- Prompt an immediate greeting (audio) ---
        greeting_event = {
            "type": "response.create",
            "response": {
                # use session defaults but we can be explicit:
                "output_modalities": ["audio"],
                # Empty input array = ignore prior conversation context
                "input": [],
                # Say this as the first line
                "instructions": AGENT_GREETING,
            },
        }
        await openai_ws.send(json.dumps(greeting_event))
        logger.info("Queued initial greeting to caller")

        async def handle_openai_events():
            """Forward OpenAI audio to Telnyx + log useful events."""
            try:
                async for message in openai_ws:
                    try:
                        event = json.loads(message)
                        etype = event.get("type", "")

                        # Canonical audio events from Realtime (audio chunks and completion)
                        if etype == "response.output_audio.delta":
                            audio_b64 = event.get("delta", "")
                            if audio_b64:
                                await ws.send_json(
                                    {
                                        "event": "media",
                                        "stream_id": stream_id,
                                        "media": {"payload": audio_b64},
                                    }
                                )

                        elif etype == "response.output_audio.done":
                            # Optional marker to help you correlate ends on Telnyx side
                            await ws.send_json(
                                {
                                    "event": "mark",
                                    "stream_id": stream_id,
                                    "mark": {"name": "audio_end"},
                                }
                            )

                        # Text deltas can be handy for logs/analytics
                        elif etype == "response.output_text.delta":
                            txt = event.get("delta", "")
                            if txt:
                                logger.info(f"[Model text] {txt}")

                        # Transcripts of model output; optional to log
                        elif etype == "response.output_audio_transcript.delta":
                            t = event.get("delta", "")
                            if t:
                                logger.info(f"[AI transcript] {t}")

                        # Useful lifecycle events
                        elif etype == "input_audio_buffer.speech_started":
                            logger.info("Caller started speaking")
                        elif etype == "input_audio_buffer.speech_stopped":
                            logger.info("Caller stopped speaking")
                        elif etype == "response.created":
                            logger.info("AI response started")
                        elif etype == "response.done":
                            logger.info("AI response completed")
                        elif etype == "error":
                            logger.error(f"OpenAI error: {event}")

                    except json.JSONDecodeError:
                        logger.warning("Received non-JSON message from OpenAI")
                    except Exception as e:
                        logger.error(f"Error processing OpenAI event: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.info("OpenAI WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error in OpenAI event handler: {e}")

        # Start the OpenAI event handler
        forward_task = asyncio.create_task(handle_openai_events())

        # Telnyx -> OpenAI (append inbound PCMU frames)
        async for telnyx_message in ws.iter_json():
            try:
                event_type = telnyx_message.get("event")

                if event_type == "media":
                    media = telnyx_message.get("media", {})
                    payload = media.get("payload")
                    if payload:
                        # Forward base64 PCMU bytes directly
                        await openai_ws.send(
                            json.dumps(
                                {"type": "input_audio_buffer.append", "audio": payload}
                            )
                        )

                elif event_type in ("stop", "callEnded"):
                    logger.info(f"Telnyx media stream ended: {event_type}")
                    break

            except Exception as e:
                logger.error(f"Error processing Telnyx message: {e}")
                break

    except WebSocketDisconnect:
        logger.info("Telnyx WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected error in media handler: {e}")
    finally:
        # Cleanup
        if forward_task and not forward_task.done():
            forward_task.cancel()
            try:
                await forward_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error cancelling forward task: {e}")

        if openai_ws:
            try:
                await openai_ws.close()
                logger.info("Closed OpenAI WebSocket")
            except Exception as e:
                logger.error(f"Error closing OpenAI WebSocket: {e}")

        try:
            # 1 == OPEN in Starlette's WebSocketState
            if ws.client_state.value == 1:
                await ws.close()
        except Exception as e:
            logger.error(f"Error closing Telnyx WebSocket: {e}")

        logger.info(f"Media session cleanup complete for call {call_control_id}")
