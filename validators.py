"""The module contains the Pydantic models used for validation of input data."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ImageData(BaseModel):
    """Model representing a ImageData."""

    file_path: str
    description: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VideoData(BaseModel):
    """Data model for validating video-related inputs.

    Attributes:
        file_path (FilePath): Path to the video file.
        description (str): Brief description of the video.
        date (datetime): Timestamp of when the video was added.

    """

    file_path: str
    description: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Search request model
class SearchRequest(BaseModel):
    """Model representing a search request."""

    query: str
    file_type: str


# Search response model

class SearchResult(BaseModel):
    """Model representing a search result."""

    file_path: str
    description: str

class SearchResponse(BaseModel):
    """Model representing a search response."""

    results: list[SearchResult]

class SearchQuery(BaseModel):
    """Model representing a search query.

    Attributes:
        query (str): Search keyword or phrase.
        file_type (str): Type of file to search for.

    """

    query: str
    file_type: str

