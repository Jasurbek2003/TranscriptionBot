"""Gemini-based transcription service."""

import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Union
import google.generativeai as genai

from .base import BaseTranscriptionService
from core.logging import logger


class GeminiTranscriptionService(BaseTranscriptionService):
    """Gemini API transcription service."""

    def __init__(self, api_key: str):
        """Initialize Gemini transcription service.

        Args:
            api_key: Gemini API key
        """
        super().__init__(api_key)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    async def transcribe_from_bytes(self, file_bytes: bytes, media_type: str, duration: int = 0) -> str:
        """Transcribe media from bytes.

        Args:
            file_bytes: Media file content as bytes
            media_type: Type of media ("audio" or "video")
            duration: Duration in seconds

        Returns:
            Transcribed text
        """
        try:
            logger.info(f"Transcribing {media_type} from bytes (duration: {duration}s)")

            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f'.{self._get_file_extension(media_type)}', delete=False) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = Path(tmp_file.name)

            try:
                # Upload file to Gemini with proper configuration
                logger.info("Uploading file to Gemini API...")

                # Try upload with compatibility for different library versions
                try:
                    # Try newer API (0.8.0+)
                    uploaded_file = await asyncio.to_thread(
                        genai.upload_file,
                        str(tmp_path)
                    )
                except (TypeError, AttributeError) as e:
                    # Fallback for older API (0.7.x) - use Blob API
                    logger.info(f"Using Blob API for older library version: {e}")

                    from google.generativeai.types import Blob

                    with open(tmp_path, 'rb') as f:
                        file_data = f.read()

                    # Create a Blob object
                    blob = Blob(
                        mime_type=self._get_mime_type(media_type),
                        data=file_data
                    )

                    prompt = """
                    Please transcribe the audio/video content in this file.
                    Provide only the transcribed text without any additional commentary or formatting.
                    If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
                    """

                    # Generate content with blob
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        [prompt, blob]
                    )

                    transcription_text = response.text.strip()
                    logger.info(f"Transcription completed successfully ({len(transcription_text)} characters)")
                    return transcription_text

                # Wait for processing
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    uploaded_file = await asyncio.to_thread(genai.get_file, uploaded_file.name)

                if uploaded_file.state.name == "FAILED":
                    raise Exception("File processing failed")

                # Generate transcription
                prompt = """
                Please transcribe the audio/video content in this file.
                Provide only the transcribed text without any additional commentary or formatting.
                If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
                """

                response = await asyncio.to_thread(
                    self.model.generate_content,
                    [prompt, uploaded_file]
                )

                transcription_text = response.text.strip()
                logger.info(f"Transcription completed successfully ({len(transcription_text)} characters)")

                # Clean up uploaded file
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup uploaded file: {cleanup_error}")

                return transcription_text

            finally:
                # Clean up temporary file
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def _get_file_extension(self, media_type: str) -> str:
        """Get appropriate file extension for media type."""
        return "mp4" if media_type == "video" else "mp3"

    def _get_mime_type(self, media_type: str) -> str:
        """Get appropriate MIME type for media type."""
        if media_type == "video":
            return "video/mp4"
        return "audio/mpeg"

    async def transcribe_audio(self, file_path: Path, language: str = "auto") -> Dict[str, Any]:
        """Transcribe audio file using Gemini API.

        Args:
            file_path: Path to the audio file
            language: Language code for transcription

        Returns:
            Dictionary with transcription results
        """
        try:
            logger.info(f"Transcribing audio file: {file_path}")

            # For now, return a placeholder response
            # In a full implementation, you would upload the file to Gemini
            # and process the transcription
            return {
                "text": "Audio transcription placeholder - Gemini service not fully implemented",
                "confidence": 0.0,
                "language": language,
                "duration": 0
            }

        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            raise

    async def transcribe_video(self, file_path: Path, language: str = "auto") -> Dict[str, Any]:
        """Transcribe video file using Gemini API.

        Args:
            file_path: Path to the video file
            language: Language code for transcription

        Returns:
            Dictionary with transcription results
        """
        try:
            logger.info(f"Transcribing video file: {file_path}")

            # For now, return a placeholder response
            return {
                "text": "Video transcription placeholder - Gemini service not fully implemented",
                "confidence": 0.0,
                "language": language,
                "duration": 0
            }

        except Exception as e:
            logger.error(f"Video transcription failed: {e}")
            raise

    async def get_supported_formats(self) -> Dict[str, list]:
        """Get supported audio and video formats.

        Returns:
            Dictionary with supported formats
        """
        return {
            "audio": ["mp3", "wav", "m4a", "ogg", "flac"],
            "video": ["mp4", "avi", "mov", "mkv", "webm"]
        }