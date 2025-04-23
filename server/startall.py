# Wrapper to start WebSocket servers for voice, transcribed, and model response services.

import asyncio
from uvicorn.config import Config
from uvicorn.server import Server
from tasks import run_translate_fragment_periodically, run_agent_call_periodically
from voice import voiceapp as voice_app  # Import the FastAPI app for voice
from transcribed import transcribeapp as transcribed_app  # Import the FastAPI app for transcribed
from modelresp import modelrespapp as modelresp_app  # Import the FastAPI app for model response
from fastapi.middleware.cors import CORSMiddleware

transcribed_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def start_voice_server():
    """Starts the WebSocket server for voice-related actions."""
    config = Config("voice:voiceapp", host="0.0.0.0", port=8081, reload=False)
    server = Server(config)
    # Trigger FastAPI lifecycle events
    await voice_app.router.startup()
    await server.serve()
    await voice_app.router.shutdown()


async def start_transcribed_server():
    """Starts the WebSocket server for transcribed text."""
    config = Config("transcribed:transcribeapp", host="0.0.0.0", port=6081, reload=False)
    server = Server(config)
    # Trigger FastAPI lifecycle events
    print("Starting transcribed_app...")
    await transcribed_app.router.startup()
    print("transcribed_app started. Serving...")
    await server.serve()
    print("Shutting down transcribed_app...")
    await transcribed_app.router.shutdown()
    print("transcribed_app shut down.")


async def start_modelresp_server():
    """Starts the WebSocket server for model response."""
    config = Config("modelresp:modelrespapp", host="0.0.0.0", port=7081, reload=False)
    server = Server(config)
    # Trigger FastAPI lifecycle events
    await modelresp_app.router.startup()
    await server.serve()
    await modelresp_app.router.shutdown()


async def main():
    """Main function to run all WebSocket servers and periodic tasks."""
    print("Starting all servers and periodic tasks...")
    await asyncio.gather(
        start_voice_server(),
        start_transcribed_server(),
        start_modelresp_server(),
        run_translate_fragment_periodically(),
        run_agent_call_periodically(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down servers...")