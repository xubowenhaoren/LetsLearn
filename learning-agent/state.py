"""State models for LangGraph quiz generation."""
from typing import Annotated, TypedDict
import operator


class LearningQuizState(TypedDict):
    file_md5: str
    user_id: str                           # Multi-tenant: real user ID from X-User-Id
    all_chunks: list[dict]
    all_chunks_text: str
    key_points: list[str]
    key_point: str                          # Set by Send for per-card generation
    cards: Annotated[list[dict], operator.add]  # Accumulated via fan-in
    error: str
