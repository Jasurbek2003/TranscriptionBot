from aiogram.fsm.state import State, StatesGroup


class TranscriptionStates(StatesGroup):
    """Transcription process states"""

    # Media processing
    waiting_for_media = State()
    processing_media = State()
    confirming_transcription = State()
    transcribing = State()

    # Settings
    choosing_language = State()
    choosing_format = State()

    # Feedback
    rating_transcription = State()
    leaving_feedback = State()
