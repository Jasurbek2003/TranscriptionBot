from typing import Any, Dict, Union
from aiogram.filters import Filter
from aiogram.types import Message
from bot.config import settings


class MediaFilter(Filter):
    """Filter for media messages (audio or video)"""

    async def __call__(self, message: Message) -> bool:
        return bool(message.audio or message.video or message.voice or message.video_note)


class AudioFilter(Filter):
    """Filter for audio messages"""

    def __init__(self, check_duration: bool = True, max_duration: int = None):
        self.check_duration = check_duration
        self.max_duration = max_duration or settings.MAX_AUDIO_DURATION_SECONDS

    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        if not (message.audio or message.voice):
            return False

        media = message.audio or message.voice

        if self.check_duration and media.duration > self.max_duration:
            return False

        return {
            "media_type": "audio",
            "duration": media.duration,
            "file_id": media.file_id,
            "file_size": media.file_size
        }


class VideoFilter(Filter):
    """Filter for video messages"""

    def __init__(self, check_duration: bool = True, max_duration: int = None):
        self.check_duration = check_duration
        self.max_duration = max_duration or settings.MAX_VIDEO_DURATION_SECONDS

    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        if not (message.video or message.video_note):
            return False

        media = message.video or message.video_note

        if self.check_duration and media.duration > self.max_duration:
            return False

        return {
            "media_type": "video",
            "duration": media.duration,
            "file_id": media.file_id,
            "file_size": media.file_size
        }


class FileSizeFilter(Filter):
    """Filter for checking file size"""

    def __init__(self, max_size_mb: int = None):
        self.max_size_bytes = (max_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024

    async def __call__(self, message: Message) -> bool:
        media = message.audio or message.video or message.voice or message.video_note

        if not media:
            return False

        if media.file_size and media.file_size > self.max_size_bytes:
            return False

        return True
