import os
import tempfile
from pathlib import Path
from typing import Optional
import aiofiles
import asyncio
import logging

logger = logging.getLogger(__name__)


async def download_file(bot, file_id: str, destination: Optional[Path] = None) -> Path:
    """
    Download file from Telegram
    """
    file = await bot.get_file(file_id)

    if destination is None:
        destination = Path(tempfile.mktemp())

    await bot.download_file(file.file_path, destination)
    return destination


async def extract_audio_from_video(video_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Extract audio from video using ffmpeg
    """
    if output_path is None:
        output_path = video_path.with_suffix('.mp3')

    try:
        # Run ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'libmp3lame',  # MP3 codec
            '-ab', '128k',  # Bitrate
            '-ar', '44100',  # Sample rate
            '-y',  # Overwrite output
            str(output_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None

        return output_path

    except Exception as e:
        logger.error(f"Failed to extract audio: {e}")
        return None


async def save_file_from_bytes(data: bytes, filename: str, directory: Path) -> Path:
    """
    Save bytes data to file
    """
    filepath = directory / filename

    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(data)

    return filepath


def get_file_extension(mime_type: str) -> str:
    """
    Get file extension from MIME type
    """
    mime_to_ext = {
        'audio/mpeg': 'mp3',
        'audio/mp4': 'm4a',
        'audio/ogg': 'ogg',
        'audio/wav': 'wav',
        'video/mp4': 'mp4',
        'video/mpeg': 'mpeg',
        'video/quicktime': 'mov',
        'video/x-msvideo': 'avi',
    }

    return mime_to_ext.get(mime_type, 'bin')


def clean_filename(filename: str) -> str:
    """
    Clean filename from invalid characters
    """
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return name + ext