# Defines periodic tasks for transcription, translation, and agent calls.

import asyncio
import os
import base64
import numpy as np
from datetime import datetime
from agent_call import agentCall_async  
from translate_openai import translate_text
from objects import voice_fragments, text_fragments, TextFragment
from transcribe_whisper import transcribe_cloud_from_memory, record_audio, save_wav, transcribe_cloud, transcribe_local

translate_fragment_running = False  # Flag to track if translate_fragment is running


def decode_audio_base64(audio_base64: str) -> np.ndarray:
    try:
        if not audio_base64:
            raise ValueError("Audio data is empty or None.")

        # Ensure the base64 string is properly padded
        if len(audio_base64) % 4 != 0:
            print("Base64 string length is not a multiple of 4. Adding padding.")
            audio_base64 += "=" * (4 - len(audio_base64) % 4)

        # Decode the base64 string
        audio_bytes = base64.b64decode(audio_base64)

        # Convert the raw bytes into a NumPy array
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        return audio
    except Exception as e:
        raise ValueError(f"Error decoding base64 audio: {e}")


async def translate_fragment():
    print("Running translate_fragment")
    global translate_fragment_running
    if translate_fragment_running:
        print("translate_fragment already running. Skipping this run.")
        return

    translate_fragment_running = True
    try:
        while voice_fragments:
            fragment = voice_fragments.pop(0)
            payload = fragment.payload
            duration = payload.get("duration")
            transcription_mode = payload.get("mode").lower()
            translate_to = payload.get("translate_to")
            rate = payload.get("sample_rate")
            audio_base64 = payload.get("audio")  # Base64-encoded audio string
            print("duration, mode, translate_to, audio length: ", duration, transcription_mode, translate_to, len(audio_base64))

            # Decode the base64-encoded audio string using the utility function
            try:
                audio = decode_audio_base64(audio_base64)
            except ValueError as e:
                print(e)
                continue

            path = await asyncio.to_thread(save_wav, audio, rate)

            # Perform transcription
            if transcription_mode == "c":
                transcribed_text = transcribe_cloud(path)
                #transcribed_text = transcribe_cloud_from_memory(audio, rate)
            elif transcription_mode == "l":
                transcribed_text = transcribe_local(path)
            else:
                print("Invalid transcription mode. Skipping.")
                continue

            print("transcribed_text size: ", len(transcribed_text))

            # Perform translation if needed
            if translate_to:
                translated_text = await asyncio.to_thread(
                    translate_text, transcribed_text, "English", translate_to
                )
            else:
                translated_text = transcribed_text

            # Append the translated text to text_fragments
            text_fragments.append(TextFragment(datetime.now(), translated_text))
            print("after append text_fragments: ", len(text_fragments))

    except Exception as e:
        print(f"Error in translate_fragment: {e}")
    finally:
        translate_fragment_running = False


# Runs translate_fragment periodically
async def run_translate_fragment_periodically(interval: int = 5):
    print("Running translate_fragment periodically")
    while True:
        await translate_fragment()
        await asyncio.sleep(interval)


# Processes text fragments and calls the agent periodically.
async def run_agent_call_periodically(interval: int = 10):
    print("Running agent_call periodically")
    while True:
        if text_fragments:
            fragment = text_fragments.pop(0)
            await agentCall_async(fragment.translation_output)  # Call the imported function
        await asyncio.sleep(interval)

