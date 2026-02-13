from pathlib import Path
from google.cloud import texttospeech

def synthesize_mp3(text: str, out_path: Path, voice_name: str = "en-US-Neural2-F") -> None:
    """
    Requires GOOGLE_APPLICATION_CREDENTIALS pointing to a service account JSON.
    Produces an MP3 file.
    """
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"")
