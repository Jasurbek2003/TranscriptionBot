"""Gemini-based transcription service."""

import asyncio
import base64
from pathlib import Path
from typing import Any, Dict

from core.logging import logger
from .base import BaseTranscriptionService

# Try to import the new google-genai library, fallback to old one
try:
    from google import genai
    from google.genai import types

    USE_NEW_API = True
except ImportError:
    import google.generativeai as genai

    USE_NEW_API = False


class GeminiTranscriptionService(BaseTranscriptionService):
    """Gemini API transcription service."""

    def __init__(self, api_key: str, max_output_tokens: int = 8192):
        """Initialize Gemini transcription service.

        Args:
            api_key: Gemini API key
            max_output_tokens: Maximum output tokens (default: 8192, max: 8192 for most models)
        """
        super().__init__(api_key)
        self.max_output_tokens = max_output_tokens

        if USE_NEW_API:
            # New google-genai library
            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.0-flash-exp"
        else:
            # Old google-generativeai library
            genai.configure(api_key=api_key)
            self.client = None
            self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    async def transcribe_from_bytes(
            self, file_bytes: bytes, media_type: str, duration: int = 0
    ) -> str:
        """Transcribe media from bytes.

        Args:
            file_bytes: Media file content as bytes
            media_type: Type of media ("audio" or "video")
            duration: Duration in seconds

        Returns:
            Transcribed text
        """
        # For very long audio (>20 minutes), use chunking strategy
        if duration > 1200:  # 20 minutes
            logger.info(f"Audio duration {duration}s exceeds 20 minutes - using chunking strategy")
            return await self._transcribe_long_audio_chunked(file_bytes, media_type, duration)

        try:
            logger.info(
                f"Transcribing {media_type} from bytes (duration: {duration}s) using {'new' if USE_NEW_API else 'old'} API"
            )

            # Create improved prompt emphasizing completeness
            prompt = f"""
            Please transcribe the COMPLETE audio/video content in this file from beginning to end.

            IMPORTANT:
            - Transcribe the ENTIRE audio, do not stop or truncate early
            - Duration is approximately {duration} seconds - transcribe ALL of it
            - Provide ONLY the transcribed text without any additional commentary
            - If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
            - Do not add summaries, descriptions, or notes - just the complete transcription
            - If you need more space, continue transcribing until you reach the end

            Begin transcription:
            """

            if USE_NEW_API:
                # Use new google-genai library
                file_data_base64 = base64.b64encode(file_bytes).decode("utf-8")

                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=self._get_mime_type(media_type), data=file_data_base64
                                )
                            ),
                        ],
                    ),
                ]

                logger.info("Sending request to Gemini API (new API)...")

                # Configure generation with higher token limit
                config = types.GenerateContentConfig(
                    max_output_tokens=self.max_output_tokens,
                    temperature=0.2,  # Lower temperature for more accurate transcription
                    top_p=0.8,
                    top_k=40,
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                transcription_text = response.text.strip()

                # Check if response was truncated
                if hasattr(response, "candidates") and response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason == "MAX_TOKENS":
                        logger.warning(
                            f"Transcription may be incomplete - hit max_output_tokens limit ({self.max_output_tokens}). "
                            f"Consider splitting audio into chunks or increasing max_output_tokens."
                        )
                        transcription_text += (
                            "\n\n[Note: Transcription may be incomplete due to length limits]"
                        )
            else:
                # Use old google-generativeai library with Part API
                logger.info("Sending request to Gemini API (old API)...")

                # Create a part with inline data
                part = {
                    "inline_data": {
                        "mime_type": self._get_mime_type(media_type),
                        "data": base64.b64encode(file_bytes).decode("utf-8"),
                    }
                }

                # Configure generation with higher token limit
                generation_config = {
                    "max_output_tokens": self.max_output_tokens,
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "top_k": 40,
                }

                response = await asyncio.to_thread(
                    self.model.generate_content, [prompt, part], generation_config=generation_config
                )
                transcription_text = response.text.strip()

                # Check if response was truncated
                if hasattr(response, "candidates") and response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason.name == "MAX_TOKENS":
                        logger.warning(
                            f"Transcription may be incomplete - hit max_output_tokens limit ({self.max_output_tokens}). "
                            f"Consider splitting audio into chunks or increasing max_output_tokens."
                        )
                        transcription_text += (
                            "\n\n[Note: Transcription may be incomplete due to length limits]"
                        )

            logger.info(
                f"Transcription completed successfully ({len(transcription_text)} characters)"
            )
            return transcription_text

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
                "duration": 0,
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
                "duration": 0,
            }

        except Exception as e:
            logger.error(f"Video transcription failed: {e}")
            raise

    async def _transcribe_long_audio_chunked(
            self, file_bytes: bytes, media_type: str, duration: int
    ) -> str:
        """Transcribe long audio by splitting into chunks.

        This method splits audio into ~10-minute chunks and transcribes each separately.

        Args:
            file_bytes: Media file content as bytes
            media_type: Type of media
            duration: Total duration in seconds

        Returns:
            Combined transcription text
        """
        try:
            import io

            from pydub import AudioSegment

            logger.info(f"Splitting {duration}s audio into chunks for transcription")

            # Load audio from bytes
            audio = AudioSegment.from_file(io.BytesIO(file_bytes))

            # Split into 10-minute chunks (600 seconds = 600,000 ms)
            chunk_length_ms = 10 * 60 * 1000  # 10 minutes
            chunks = []

            for i in range(0, len(audio), chunk_length_ms):
                chunk = audio[i: i + chunk_length_ms]
                chunks.append(chunk)

            logger.info(f"Split audio into {len(chunks)} chunks")

            # Transcribe each chunk
            transcriptions = []
            for idx, chunk in enumerate(chunks, 1):
                logger.info(f"Transcribing chunk {idx}/{len(chunks)} ({len(chunk) / 1000:.1f}s)")

                # Export chunk to bytes
                buffer = io.BytesIO()
                chunk.export(buffer, format="mp3")
                chunk_bytes = buffer.getvalue()

                # Transcribe chunk with modified prompt
                chunk_duration = int(len(chunk) / 1000)  # Convert ms to seconds
                chunk_text = await self._transcribe_single_chunk(
                    chunk_bytes, media_type, chunk_duration, idx, len(chunks)
                )

                if chunk_text:
                    transcriptions.append(f"[Part {idx}]\n{chunk_text}")
                else:
                    logger.error(f"Failed to transcribe chunk {idx}")
                    transcriptions.append(f"[Part {idx} - Transcription failed]")

                # Small delay to avoid rate limiting
                if idx < len(chunks):
                    await asyncio.sleep(1)

            # Combine all transcriptions
            combined_text = "\n\n".join(transcriptions)
            logger.info(f"Chunked transcription completed: {len(combined_text)} characters total")

            return combined_text

        except ImportError:
            logger.error(
                "pydub not installed - cannot split long audio. Install with: pip install pydub"
            )
            logger.info("Falling back to single transcription (may be truncated)")
            return await self._transcribe_single(file_bytes, media_type, duration)
        except Exception as e:
            logger.error(f"Chunked transcription failed: {e}", exc_info=True)
            logger.info("Falling back to single transcription")
            return await self._transcribe_single(file_bytes, media_type, duration)

    async def _transcribe_single_chunk(
            self, file_bytes: bytes, media_type: str, duration: int, chunk_num: int, total_chunks: int
    ) -> str:
        """Transcribe a single chunk of audio.

        Args:
            file_bytes: Chunk bytes
            media_type: Media type
            duration: Chunk duration
            chunk_num: Current chunk number
            total_chunks: Total number of chunks

        Returns:
            Transcribed text for this chunk
        """
        prompt = f"""
        Please transcribe this audio segment (Part {chunk_num} of {total_chunks}).

        IMPORTANT:
        - This is part of a longer audio that has been split into chunks
        - Transcribe the COMPLETE audio in this segment
        - Start immediately with the transcription - do not add introductory text
        - If this segment starts or ends mid-sentence, transcribe what you hear
        - Provide ONLY the transcribed text

        Transcription:
        """

        try:
            if USE_NEW_API:
                file_data_base64 = base64.b64encode(file_bytes).decode("utf-8")

                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=self._get_mime_type(media_type), data=file_data_base64
                                )
                            ),
                        ],
                    ),
                ]

                config = types.GenerateContentConfig(
                    max_output_tokens=self.max_output_tokens,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40,
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                return response.text.strip()
            else:
                part = {
                    "inline_data": {
                        "mime_type": self._get_mime_type(media_type),
                        "data": base64.b64encode(file_bytes).decode("utf-8"),
                    }
                }

                generation_config = {
                    "max_output_tokens": self.max_output_tokens,
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "top_k": 40,
                }

                response = await asyncio.to_thread(
                    self.model.generate_content, [prompt, part], generation_config=generation_config
                )
                return response.text.strip()

        except Exception as e:
            logger.error(f"Failed to transcribe chunk {chunk_num}: {e}")
            return None

    async def _transcribe_single(self, file_bytes: bytes, media_type: str, duration: int) -> str:
        """Single-pass transcription without chunking (fallback method).

        Args:
            file_bytes: Media file content as bytes
            media_type: Type of media
            duration: Duration in seconds

        Returns:
            Transcribed text
        """
        # Use the normal transcription logic but bypass the duration check
        # This is used as a fallback when chunking fails
        logger.info(f"Using single-pass transcription for {duration}s audio")

        prompt = f"""
        Please transcribe the COMPLETE audio/video content in this file from beginning to end.

        IMPORTANT:
        - Transcribe the ENTIRE audio, do not stop or truncate early
        - Duration is approximately {duration} seconds - transcribe ALL of it
        - Provide ONLY the transcribed text without any additional commentary
        - If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
        - Do not add summaries, descriptions, or notes - just the complete transcription
        - If you need more space, continue transcribing until you reach the end

        Begin transcription:
        """

        try:
            if USE_NEW_API:
                file_data_base64 = base64.b64encode(file_bytes).decode("utf-8")

                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=self._get_mime_type(media_type), data=file_data_base64
                                )
                            ),
                        ],
                    ),
                ]

                config = types.GenerateContentConfig(
                    max_output_tokens=self.max_output_tokens,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40,
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                transcription_text = response.text.strip()

                # Check if truncated
                if hasattr(response, "candidates") and response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason == "MAX_TOKENS":
                        logger.warning(
                            f"Transcription truncated at max_output_tokens ({self.max_output_tokens})"
                        )
                        transcription_text += (
                            "\n\n[Note: Transcription may be incomplete due to length limits]"
                        )
            else:
                part = {
                    "inline_data": {
                        "mime_type": self._get_mime_type(media_type),
                        "data": base64.b64encode(file_bytes).decode("utf-8"),
                    }
                }

                generation_config = {
                    "max_output_tokens": self.max_output_tokens,
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "top_k": 40,
                }

                response = await asyncio.to_thread(
                    self.model.generate_content, [prompt, part], generation_config=generation_config
                )
                transcription_text = response.text.strip()

                # Check if truncated
                if hasattr(response, "candidates") and response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason.name == "MAX_TOKENS":
                        logger.warning(
                            f"Transcription truncated at max_output_tokens ({self.max_output_tokens})"
                        )
                        transcription_text += (
                            "\n\n[Note: Transcription may be incomplete due to length limits]"
                        )

            logger.info(
                f"Single-pass transcription completed ({len(transcription_text)} characters)"
            )
            return transcription_text

        except Exception as e:
            logger.error(f"Single-pass transcription failed: {e}", exc_info=True)
            return None

    async def get_supported_formats(self) -> Dict[str, list]:
        """Get supported audio and video formats.

        Returns:
            Dictionary with supported formats
        """
        return {
            "audio": ["mp3", "wav", "m4a", "ogg", "flac"],
            "video": ["mp4", "avi", "mov", "mkv", "webm"],
        }
