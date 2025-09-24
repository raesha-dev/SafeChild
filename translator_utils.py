import os
import requests
from dotenv import load_dotenv
load_dotenv()


# Azure Translator Service credentials and endpoint from .env
TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
TRANSLATOR_ENDPOINT = os.getenv("AZURE_TRANSLATOR_ENDPOINT")  # e.g. https://api.cognitive.microsofttranslator.com
TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION")  # if required by new APIs

def translate_text(text: str, from_lang: str = "auto", to_lang: str = "en") -> str:
    """
    Translate input text from source language to target language using Azure Translator API.
    
    Parameters:
        text (str): Text to translate.
        from_lang (str): Source language code, 'auto' for auto-detection.
        to_lang (str): Target language code (default 'en' for English).
    
    Returns:
        str: Translated text.
    """
    path = "/translate"
    constructed_url = TRANSLATOR_ENDPOINT + path
    params = {
        "api-version": "3.0",
        "from": from_lang if from_lang != "auto" else "",
        "to": to_lang
    }
    headers = {
        "Ocp-Apim-Subscription-Key": TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": TRANSLATOR_REGION,
        "Content-type": "application/json"
    }
    body = [{"text": text}]

    response = requests.post(constructed_url, params=params, headers=headers, json=body)
    response.raise_for_status()
    translations = response.json()
    
    # Extract the translated text from response
    translated_text = translations[0]["translations"][0]["text"]
    return translated_text
