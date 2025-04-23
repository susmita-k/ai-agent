# WebSocket for transcribed
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket_manager import WebSocketConnectionManager
from objects import text_fragments
import asyncio
import json

transcribeapp = FastAPI()
transcribemanager = WebSocketConnectionManager()


# Handles WebSocket connections for transcribed text.
@transcribeapp.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await transcribemanager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # Keep the connection alive
    except WebSocketDisconnect:
        transcribemanager.disconnect(websocket)
        print("transcribe: client disconnected")
    except Exception as e:
        print(f"transcribe: Error in websocket_endpoint: {e}")


# Periodically sends new transcriptions to connected clients
async def send_new_transcriptions():
    print("enter send_new_transcriptions")
    try:
        while True:
            # print("TRUE send_new_transcriptions")
            for fragment in text_fragments:
                print("transcribe: for loop")
                if not fragment.sent:
                    print("transcribe: preparing to send new fragment")
                    message = {
                        "timestamp": fragment.timestamp.isoformat(),
                        "translation_output": fragment.translation_output,
                    }
                    print("transcribe: send_new:", message)

                    # Check if there are active WebSocket connections
                    if transcribemanager.active_connections:
                        try:
                            await transcribemanager.broadcast(json.dumps(message))
                            fragment.sent = True  # Mark as sent only if broadcast succeeds
                            print("transcribe: broadcast succeeded, fragment marked as sent")
                        except Exception as e:
                            print(f"transcribe: Error broadcasting message: {e}")
                    else:
                        print("transcribe: No active WebSocket connections, skipping broadcast")
            await asyncio.sleep(7)
    except Exception as e:
        print(f"transcribe: Error in send_new_transcriptions: {e}")
        await asyncio.sleep(7)


# heartbeat
async def send_heartbeat():
    print("transcribe: heartbeat")
    try:
        while True:
            await transcribemanager.broadcast('heartbeat')
            await asyncio.sleep(8)
    except Exception as e:
        print(f"transcribe: heartbeat: Error: {e}")
        await asyncio.sleep(8)


async def monitor_tasks(*tasks):
    """Monitors the given tasks to check if they exit or terminate."""
    while True:
        for task in tasks:
            if task.done():
                if task.cancelled():
                    print(f"Task {task.get_name()} was cancelled.")
                else:
                    exception = task.exception()
                    if exception:
                        print(f"Task {task.get_name()} exited with exception: {exception}")
                    else:
                        print(f"Task {task.get_name()} completed successfully.")
                # Optionally restart the task if needed
                if task.get_coro().__name__ == "send_new_transcriptions":
                    print("Restarting send_new_transcriptions task...")
                    tasks = list(tasks)  # Convert tuple to list to modify
                    tasks.remove(task)
                    new_task = asyncio.create_task(send_new_transcriptions())
                    tasks.append(new_task)
                elif task.get_coro().__name__ == "send_heartbeat":
                    print("Restarting send_heartbeat task...")
                    tasks = list(tasks)  # Convert tuple to list to modify
                    tasks.remove(task)
                    new_task = asyncio.create_task(send_heartbeat())
                    tasks.append(new_task)
        await asyncio.sleep(5)


async def startup_event():
    print("transcribe: startup")
    try:
        # Create the tasks
        send_new_transcriptions_task = asyncio.create_task(send_new_transcriptions())
        print(f"send_new_transcriptions task created: {send_new_transcriptions_task}")

        send_heartbeat_task = asyncio.create_task(send_heartbeat())
        print(f"send_heartbeat task created: {send_heartbeat_task}")

        # Monitor the tasks
        asyncio.create_task(monitor_tasks(send_new_transcriptions_task, send_heartbeat_task))

        print("transcribe: after send_new_transcriptions and send_heartbeat")
    except Exception as e:
        print(f"transcribe: startup_event: Error: {e}")
        await asyncio.sleep(1)


transcribeapp.add_event_handler("startup", startup_event)
