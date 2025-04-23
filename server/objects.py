from pydantic import BaseModel

# Global objects
voice_fragments = [] # Stores VoiceFragment objects
text_fragments = []  # Stores TextFragment objects
modelresps = []

# Represents a voice fragment with a timestamp and payload."""
class VoiceFragment:
    def __init__(self, timestamp, payload):
        self.timestamp = timestamp
        self.payload = payload


# Represents a text fragment with a timestamp, translation output, and sent status."""
class TextFragment:
    def __init__(self, timestamp, translation_output):
        self.timestamp = timestamp
        self.translation_output = translation_output
        self.sent = False  # Tracks whether this fragment has been sent to clients

# Represents a model response."""
class ModelResp:
    def __init__(self, timestamp, response):
        self.timestamp = timestamp
        self.response = response
        self.sent = False  # Tracks whether this fragment has been sent to clients

class PatientInput(BaseModel):
    gender: str
    age: int
    symptoms: str
    medical_history: str


