import os
import io
import openai
import tempfile
import datetime
import numpy as np
import sounddevice as sd
import base64
import wave
from dotenv import load_dotenv
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
from objects import voice_fragments, text_fragments, VoiceFragment, TextFragment


load_dotenv()
#openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = ""

# global store for all saved WAVs
wav_store: dict[str, str] = {}


def record_audio(duration=5, samplerate=44100):
    print("Listening...")
    audio = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    return audio, samplerate


def buffer_wav(audio: bytes, samplerate: int) -> str:
    """
    Saves the given audio buffer to a uniquely named .wav file and
    stores the filename in wav_store keyed by timestamp.

    Returns the timestamp key under which the file was saved.
    """
    # generate a timestamp key
    timestamp = datetime.datetime.now().isoformat()

    # write to a temp .wav file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        write(f.name, samplerate, audio)

    # save in the global dictionary
    wav_store[timestamp] = f.name

    return timestamp


def save_wav(audio_bytes: bytes, samplerate: int) -> str:
    try:
        # Convert raw audio bytes to a NumPy array
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            write(f.name, samplerate, audio)
            print(f"Saved WAV file: {f.name}")
            return f.name
    except Exception as e:
        print(f"Error saving WAV file: {e}")
        return None


def transcribe_cloud(file_path):
    print("transcribe_cloud")
    txt = ""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1"
            )
            txt = transcript.text
    except Exception as e:
        print(f"Error during transcription: {e}")

    return txt


def transcribe_local(file_path, model_size="base"):
    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(file_path)
    return " ".join([segment.text for segment in segments])



def transcribe_cloud_from_memory(audio: bytes, samplerate: int) -> str:
    """
    Transcribes audio data from memory using the OpenAI Whisper API.

    Args:
        audio (bytes): Raw audio data as bytes.
        samplerate (int): Sample rate of the audio.

    Returns:
        str: Transcribed text from the audio.
    """
    print("transcribe_cloud_from_memory")
    txt = ""
    try:
        # Validate and convert audio if necessary
        if isinstance(audio, bytes):
            print("transcribe_cloud_from_memory: Converting bytes to NumPy array")
            audio = np.frombuffer(audio, dtype=np.int16)

        # Create an in-memory WAV file using the wave module
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 2 bytes per sample (int16)
            wav_file.setframerate(samplerate)
            wav_file.writeframes(audio.tobytes())
        print("transcribe_cloud_from_memory: WAV file written to memory")
        wav_buffer.seek(0)  # Reset the buffer position to the beginning

        # Send the in-memory file to the OpenAI API
        print("transcribe_cloud_from_memory: Sending audio to OpenAI API")
        transcript = openai.audio.transcriptions.create(
            file=wav_buffer,
            model="whisper-1"
        )
        txt = transcript.get("text", "")
        print("transcribe_cloud_from_memory: Transcription successful")
    except Exception as e:
        print(f"Error during transcription: {e}")

    return txt


# Processes the next voice fragment from voice_fragments by saving it as a .wav file.
def process_next_voice_fragment(fragment: VoiceFragment):
    print(f"Processing voice fragment with timestamp: {fragment.timestamp}")
    audio = fragment.payload.get("audio")
    samplerate = fragment.payload.get("samplerate")
    if audio is None or samplerate is None:
        print("Invalid fragment payload: Missing audio or samplerate.")
        return None

    # Save the audio as a .wav file
    wav_file_path = save_wav(audio, samplerate)
    print(f"Saved .wav file: {wav_file_path}")

    return wav_file_path

