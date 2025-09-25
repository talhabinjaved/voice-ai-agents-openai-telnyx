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

from .agent_config import (
    TELNYX_API_KEY,
    OPENAI_API_KEY,
    PUBLIC_DOMAIN,
    AGENT_VOICE,
    AGENT_INSTRUCTIONS,
    AGENT_GREETING,
)



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
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        "transcription": {
                            "model": "whisper-1"
                        },
                        "turn_detection": {
                            "type": "semantic_vad",
                            "eagerness": "auto",
                            "create_response": True,
                            "interrupt_response": True
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcmu"},
                        "voice": AGENT_VOICE
                    },
                },
                "instructions": AGENT_INSTRUCTIONS,
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
                "output_modalities": ["audio"],
                "input": [],
                "instructions": f"Say exactly this greeting: {AGENT_GREETING}",
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
                        
                        # --- USER transcript ---
                        if etype == "conversation.item.input_audio_transcription.completed":
                            transcript = event.get("transcript", "")
                            if transcript:
                                logger.info(f"[User transcript] {transcript}")            
                        elif etype == "response.output_audio.delta":
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
                        # Useful lifecycle events
                        elif etype == "input_audio_buffer.speech_started":
                            logger.info("Caller started speaking")
                            await ws.send_json({"event": "clear", "stream_id": stream_id})
                        elif etype == "input_audio_buffer.speech_stopped":
                            logger.info("Caller stopped speaking")
                        elif etype == "response.created":
                            logger.info("AI response started")
                        elif etype == "response.done":
                            # Extract useful information from response.done event
                            response_data = event.get("response", {})
                            conversation_id = response_data.get("conversation_id", "unknown")                            
                            # Extract transcript from output
                            transcript = ""
                            output_items = response_data.get("output", [])
                            for item in output_items:
                                if item.get("type") == "message" and item.get("role") == "assistant":
                                    content = item.get("content", [])
                                    for content_item in content:
                                        if content_item.get("type") == "output_audio":
                                            transcript = content_item.get("transcript", "")
                                            break
                            
                            # Log essential information
                            logger.info(f"AI Response - Conv: {conversation_id}, Transcript: '{transcript}'")
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
