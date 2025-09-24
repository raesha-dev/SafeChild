import os
import logging
import time
from functools import wraps
from dotenv import load_dotenv
import requests

from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, AudioConfig
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Retry decorator with exponential backoff
def retry(exceptions, tries=3, delay=1, backoff=2):
    def decorator_retry(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    result = func(*args, **kwargs)
                    logger.info(f"{func.__name__} succeeded")
                    return result
                except exceptions as e:
                    logger.warning(f"{func.__name__} failed: {e}, retrying in {_delay}s...")
                    time.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
            return func(*args, **kwargs)  # last attempt, exceptions propagate
        return wrapper
    return decorator_retry

def validate_env_vars(*vars):
    """Helper to validate environment variables exist and are not None."""
    missing = [v for v in vars if not os.getenv(v)]
    if missing:
        errmsg = f"Missing environment variables: {', '.join(missing)}"
        logger.error(errmsg)
        raise EnvironmentError(errmsg)

@retry(Exception)
def translate_text(text, from_lang="auto", to_lang="en"):
    validate_env_vars("AZURE_TRANSLATOR_KEY", "AZURE_TRANSLATOR_ENDPOINT", "AZURE_TRANSLATOR_REGION")
    key = os.getenv("AZURE_TRANSLATOR_KEY")
    endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT")
    region = os.getenv("AZURE_TRANSLATOR_REGION")

    path = "/translate"
    constructed_url = endpoint + path

    params = {
        "api-version": "3.0",
        "to": to_lang,
    }
    if from_lang and from_lang.lower() != "auto":
        params["from"] = from_lang

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-type": "application/json",
    }

    body = [{"text": text or ""}]

    try:
        logger.info("Calling Azure Translator API")
        response = requests.post(constructed_url, params=params, headers=headers, json=body)
        response.raise_for_status()
        translations = response.json()
        if (
            translations and isinstance(translations, list)
            and "translations" in translations[0]
            and translations[0]["translations"]
        ):
            return translations[0]["translations"][0].get("text", "")
        else:
            raise ValueError("Unexpected translation response format")
    except Exception as e:
        logger.error(f"translate_text failed: {e}", exc_info=True)
        raise

@retry(Exception)
def speech_to_text(audio_file_path, language="en-US"):
    validate_env_vars("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")
    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")

    speech_config = SpeechConfig(subscription=key, region=region)
    audio_config = AudioConfig(filename=audio_file_path)
    speech_recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    result = speech_recognizer.recognize_once_async().get()
    if result.reason == result.Reason.RecognizedSpeech:
        return result.text
    else:
        raise ValueError(f"Speech recognition failed with reason: {result.reason}")

def authenticate_text_analytics_client():
    validate_env_vars("AZURE_TEXT_ANALYTICS_KEY", "AZURE_TEXT_ANALYTICS_ENDPOINT")
    key = os.getenv("AZURE_TEXT_ANALYTICS_KEY")
    endpoint = os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")

    credential = AzureKeyCredential(key)
    client = TextAnalyticsClient(endpoint=endpoint, credential=credential)
    return client

@retry(Exception)
def analyze_text_entities(text):
    client = authenticate_text_analytics_client()
    try:
        response = client.recognize_entities(documents=[text])[0]
        key_phrases = [entity.text for entity in response.entities]
        sentiments = client.analyze_sentiment(documents=[text])[0]
        sentiment = sentiments.sentiment if sentiments else "neutral"
        return key_phrases, sentiment
    except Exception as e:
        logger.error(f"analyze_text_entities failed: {e}", exc_info=True)
        raise
