import os
import json
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
import subprocess
from pathlib import Path
import questionary
import yt_dlp
import assemblyai


load_dotenv()

elevenlabs_client = ElevenLabs(
    api_key=os.getenv("ELEVEN_LABS_API_KEY"),
)
assemblyai.settings.api_key = os.getenv("ASSEMBLY_AI_API_KEY")

LANGUAGES = {
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

TMP_DIR = Path("tmp")
OUTPUT_DIR = Path("output")
SUBTITLE_PATH = TMP_DIR / "output.srt"

YDL_OPT = {"format": "best[ext=mp4]", "outtmpl": str(TMP_DIR / "%(id)s.%(ext)s")}


def ensure_dir() -> None:
    TMP_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def download_yt_video(url: str) -> str:
    with yt_dlp.YoutubeDL(YDL_OPT) as ydl:
        try:
            print("🎬 Downloading video from Youtube...")

            info = ydl.extract_info(url, download=True)
            filename = info["id"] + "." + info["ext"]
            return str(TMP_DIR / filename)
        except Exception as e:
            print(f"Error downloading {url}: {e}")


def gen_subtitles_elevenlabs(
    *,
    input_path: str,
    language_code: str,
):
    print("📝 Generating subtitles with Eleven Labs...")

    with open(input_path, "rb") as audio_file:
        audio_data = audio_file.read()

    additional_formats = [{"format": "srt"}]

    response = elevenlabs_client.speech_to_text.convert(
        model_id="scribe_v1",
        file=audio_data,
        language_code=language_code,
        diarize=True,
        additional_formats=json.dumps(additional_formats),
    )

    response_format = response.additional_formats[0]

    with open(SUBTITLE_PATH, "w", encoding="utf-8") as srt_file:
        srt_file.write(response_format.content)


def gen_subtitles_assembly(
    *,
    input_path: str,
    language_code: str,
):
    print("📝 Generating subtitles with Assembly AI...")

    transcriber = assemblyai.Transcriber()

    config = assemblyai.TranscriptionConfig(
        speech_model=assemblyai.SpeechModel.best,
        punctuate=True,
        format_text=True,
        language_code=language_code,
    )

    transcript = transcriber.transcribe(input_path, config=config)

    srt_content = transcript.export_subtitles_srt()

    with open(SUBTITLE_PATH, "w", encoding="utf-8") as f:
        f.write(srt_content)


def create_output_path(input_path: str) -> str:
    return str(OUTPUT_DIR / Path(input_path).name)


def burn_subtitles(input_path: str):
    print("🔥 Burning subtitles into video...")

    output_path = create_output_path(input_path)

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_path,
            "-vf",
            f"subtitles={SUBTITLE_PATH}",
            "-c:a",
            "copy",
            output_path,
        ],
        check=True,
    )


def handler():
    ensure_dir()

    transcribe_provider = questionary.select(
        "Which transcription provider do you want to use?",
        choices=["Eleven Labs", "Assembly AI"],
    ).ask()

    upload_type = questionary.select(
        "Where is the video located?",
        choices=["Local file", "Youtube"],
    ).ask()

    language = questionary.select(
        "What language is the video in?",
        choices=list(LANGUAGES.keys()),
    ).ask()

    is_local = upload_type == "Local file"

    if is_local:
        input_path = questionary.path(
            "What is the path to the video?",
        ).ask()
    else:
        youtube_url = questionary.text(
            "What is the Youtube URL?",
        ).ask()

        input_path = download_yt_video(youtube_url)

    langugae_code = LANGUAGES[language]

    try:
        if transcribe_provider == "Eleven Labs":
            gen_subtitles_elevenlabs(input_path=input_path, language_code=langugae_code)
        else:
            gen_subtitles_assembly(input_path=input_path, language_code=langugae_code)

        burn_subtitles(input_path)
    finally:
        if os.path.exists(SUBTITLE_PATH):
            os.remove(SUBTITLE_PATH)

        if not is_local and os.path.exists(input_path):
            os.remove(input_path)
        pass


if __name__ == "__main__":
    handler()
