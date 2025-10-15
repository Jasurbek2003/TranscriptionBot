"""Media file utilities for extracting metadata like duration"""

import subprocess
import json
import logging
from typing import Optional, Tuple
import tempfile
import os

logger = logging.getLogger(__name__)


def get_media_duration(file_bytes: bytes, file_extension: str = None) -> Optional[int]:
    """
    Extract duration from audio/video file using ffprobe

    Args:
        file_bytes: File content as bytes
        file_extension: Optional file extension (e.g., 'mp3', 'mp4')

    Returns:
        Duration in seconds, or None if extraction failed
    """
    try:
        # Create a temporary file to save the bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension or '') as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            # Use ffprobe to get duration
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                temp_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return None

            # Parse JSON output
            data = json.loads(result.stdout)

            # Try to get duration from format
            if 'format' in data and 'duration' in data['format']:
                duration = float(data['format']['duration'])
                return int(duration)

            # Try to get duration from streams
            if 'streams' in data:
                for stream in data['streams']:
                    if 'duration' in stream:
                        duration = float(stream['duration'])
                        return int(duration)

            logger.warning("Could not find duration in ffprobe output")
            return None

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

    except subprocess.TimeoutExpired:
        logger.error("ffprobe timed out")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting duration: {e}", exc_info=True)
        return None


def get_media_info(file_bytes: bytes, file_extension: str = None) -> Tuple[Optional[int], Optional[str]]:
    """
    Extract media info including duration and codec

    Args:
        file_bytes: File content as bytes
        file_extension: Optional file extension

    Returns:
        Tuple of (duration in seconds, codec type)
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension or '') as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                temp_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None, None

            data = json.loads(result.stdout)

            # Extract duration
            duration = None
            if 'format' in data and 'duration' in data['format']:
                duration = int(float(data['format']['duration']))

            # Extract codec type (audio or video)
            codec_type = None
            if 'streams' in data and len(data['streams']) > 0:
                codec_type = data['streams'][0].get('codec_type')

            return duration, codec_type

        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error extracting media info: {e}", exc_info=True)
        return None, None


def is_ffprobe_available() -> bool:
    """
    Check if ffprobe is available on the system

    Returns:
        True if ffprobe is available, False otherwise
    """
    try:
        subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            timeout=5
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
