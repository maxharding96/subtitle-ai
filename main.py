import os
import json
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
import subprocess
from pathlib import Path
import questionary

load_dotenv()

client = ElevenLabs(
    api_key=os.getenv("ELEVEN_LABS_API_KEY"),
)

language_dict = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Russian": "ru",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
}

subtitle_file = "tmp/output.srt"


def generate_srt_file(
    *,
    input_path: str,
    language_code: str,
):
    with open(input_path, "rb") as audio_file:
        audio_data = audio_file.read()

    additional_formats = [{"format": "srt"}]

    response = client.speech_to_text.convert(
        model_id="scribe_v1",
        file=audio_data,
        language_code=language_code,
        diarize=True,
        additional_formats=json.dumps(additional_formats),
    )

    response_format = response.additional_formats[0]

    with open(subtitle_file, "w", encoding="utf-8") as srt_file:
        srt_file.write(response_format.content)


def create_output_path(input_path: str) -> str:
    input_path = Path(input_path)
    stem = input_path.stem
    suffix = input_path.suffix
    output_path = input_path.parent / f"{stem}_subtitled{suffix}"

    return str(output_path)


def burn_subtitles(input_path: str):
    output_path = create_output_path(input_path)

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_path,
            "-vf",
            f"subtitles={subtitle_file}",
            "-c:a",
            "copy",
            output_path,
        ],
        check=True,
    )


def handler():
    language_choices = list(language_dict.keys())

    langugae = questionary.select(
        "What language is the video in?",
        choices=language_choices,
    ).ask()

    langugae_code = language_dict[langugae]

    input_path = questionary.path(
        "What is the path to the video?",
    ).ask()

    try:
        generate_srt_file(input_path=input_path, language_code=langugae_code)
        burn_subtitles(input_path)
    finally:
        if os.path.exists(subtitle_file):
            os.remove(subtitle_file)


if __name__ == "__main__":
    handler()
