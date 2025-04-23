import openai
from dotenv import load_dotenv
import os

load_dotenv()
#TODO - should come from .env file
openai.api_key = ""

def translate_text(text, input_lang="English", output_lang="Spanish"):
    prompt = (
        f"Translate the following text from {input_lang} to {output_lang}:\n\n"
        f"{text}\n\nOnly return the translated text."
    )

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional translator with medical context awareness."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()
