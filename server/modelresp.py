# WebSocket for model responses
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket_manager import WebSocketConnectionManager
from objects import modelresps
import asyncio
import json

modelrespapp = FastAPI()
modelrespmanager = WebSocketConnectionManager()


# Handles WebSocket connections for model responses.
@modelrespapp.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await modelrespmanager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # Keep the connection alive
    except WebSocketDisconnect:
        modelrespmanager.disconnect(websocket)
        print("modelresp: client disconnected")
    except Exception as e:
        print(f"modelresp: Error in websocket_endpoint: {e}")


# Periodically sends new model responses to connected clients
async def send_new_modelresp():
    print("enter modelresp")
    try:
        while True:
            for fragment in modelresps:
                if not fragment.sent:  # Only send unsent fragments
                    print("modelresp: preparing to send new fragment")
                    message = {
                        "timestamp": fragment.timestamp.isoformat(),
                        "model_resp": fragment.response,
                    }
                    print("modelresp: send_new:")

                    # Check if there are active WebSocket connections
                    if modelrespmanager.active_connections:
                        try:
                            # Broadcast the message to all active connections
                            await modelrespmanager.broadcast(json.dumps(message))
                            fragment.sent = True  # Mark as sent only if broadcast succeeds
                            print("modelresp: broadcast succeeded, fragment marked as sent")
                        except Exception as e:
                            print(f"modelresp: Error broadcasting message: {e}")
                    else:
                        print("modelresp: No active WebSocket connections, skipping broadcast")
            await asyncio.sleep(1)
    except Exception as e:
        print(f"modelresp: Error in send_new_modelresp: {e}")
        await asyncio.sleep(1)


# Monitors the given tasks to check if they exit or terminate
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
                if task.get_coro().__name__ == "send_new_modelresp":
                    print("Restarting send_new_modelresp task...")
                    tasks = list(tasks)  # Convert tuple to list to modify
                    tasks.remove(task)
                    new_task = asyncio.create_task(send_new_modelresp())
                    tasks.append(new_task)
        await asyncio.sleep(5)


# Startup event to initialize tasks
async def startup_event():
    print("modelresp: startup")
    try:
        # Create the tasks
        send_new_modelresp_task = asyncio.create_task(send_new_modelresp())
        print(f"send_new_modelresp task created: {send_new_modelresp_task}")

        # Monitor the tasks
        asyncio.create_task(monitor_tasks(send_new_modelresp_task))

        print("modelresp: after send_new_modelresp")
    except Exception as e:
        print(f"modelresp: startup_event: Error: {e}")
        await asyncio.sleep(1)


modelrespapp.add_event_handler("startup", startup_event)
