from dataclasses import dataclass
from typing import Optional


@dataclass
class MessageEnvelope:
    """
    Standard container for any NavWarn message entering the pipeline.

    This ensures all sources (TLX export, OCR, NAVTOR, phone capture)
    share the same structure before interpretation.
    """

    raw_text: str

    source: Optional[str] = None
    source_file: Optional[str] = None

    navarea: Optional[str] = None
    warning_id: Optional[str] = None
    dtg: Optional[str] = None

    message_class_guess: Optional[str] = None

    split_confidence: float = 1.0
    split_warning: Optional[str] = None
