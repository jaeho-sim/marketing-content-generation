"""
Whisper transcription.

The GCS key has no file extension, so the MIME type from the Pub/Sub
notification is used to give ffmpeg the right hint when decoding.
"""
import os
import tempfile
import structlog
from app.config import get_settings
from app.services.gcs import download_to_file

log = structlog.get_logger()
settings = get_settings()

_MIME_TO_EXT: dict[str, str] = {
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/flac": ".flac",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/mpeg": ".mpeg",
}

_model = None  # lazy-loaded so startup stays fast


def _load_model():
    global _model
    if _model is None:
        import whisper
        log.info("loading_whisper_model", size=settings.whisper_model_size)
        _model = whisper.load_model(settings.whisper_model_size)
    return _model


def transcribe_gcs_object(gcs_key: str, content_type: str | None = None) -> str:
    """Download from GCS and transcribe with Whisper. Returns transcript text."""
    ext = _MIME_TO_EXT.get(content_type or "", ".tmp")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        log.info("downloading_media", gcs_key=gcs_key)
        download_to_file(gcs_key, tmp_path)

        model = _load_model()
        log.info("transcribing", gcs_key=gcs_key)
        result = model.transcribe(tmp_path)
        text: str = result["text"].strip()
        log.info("transcription_complete", chars=len(text))
        return text
    finally:
        os.unlink(tmp_path)
