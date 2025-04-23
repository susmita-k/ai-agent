# WebSocket server for handling voice-related actions.
import json
import asyncio
from datetime import datetime
from objects import voice_fragments, VoiceFragment
from websocket_manager import WebSocketConnectionManager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

voiceapp = FastAPI()
voicemanager = WebSocketConnectionManager()


# Handles WebSocket connections for voice actions."""
@voiceapp.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("voice:enter")
    try:
        await voicemanager.connect(websocket)
    except Exception as e:
        print(f"Error in voicemanager.connect: {e}")
        return
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")

                if action == "transcribe_translate":
                    # Add payload to voice_fragments
                    print("voice_fragments:", len(voice_fragments))
                    voice_fragments.append(VoiceFragment(datetime.now(), payload))
                    await voicemanager.send_personal_message(
                        json.dumps({"status": "payload_added"}), websocket
                    )
                else:
                    await voicemanager.send_personal_message(
                        json.dumps({"error": "Invalid action"}), websocket
                    )
            except json.JSONDecodeError:
                await voicemanager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}), websocket
                )
            except Exception as e:
                print(f"WebSocket error: {e}")
                await voicemanager.send_personal_message(
                    json.dumps({"error": f"Server error: {e}"}), websocket
                )
    except WebSocketDisconnect:
        voicemanager.disconnect(websocket)
        print(f"voice:Client disconnected")
    except Exception as e:
        print(f"Unexpected error in websocket_endpoint: {e}")


# heartbeat
async def send_heartbeat():
    #print("voice: heartbeat")
    try:
        while True:
            #print("voice: Heartbeat")
            await voicemanager.broadcast("heartbeat")
            await asyncio.sleep(8)
    except Exception as e:
        print(f"voice: heartbeat: Error: {e}")
        await asyncio.sleep(1)


async def startup_event():
    print("voice: startup")
    loop = asyncio.get_event_loop()
    loop.create_task(send_heartbeat())


voiceapp.add_event_handler("startup", startup_event)
