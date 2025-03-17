"""BentoML service for searching files based on query and file type."""

from __future__ import annotations

import bentoml
from loguru import logger
from pydantic import BaseModel

from main import (
    search_with_filters,  # Ensure this function is properly implemented in main.py
)


# Define request and response models
class SearchRequest(BaseModel):
    """Request model for search queries."""

    query: str
    file_type: str


class SearchResult(BaseModel):
    """Response model for a single search result."""

    file_path: str
    description: str


class SearchResponse(BaseModel):
    """Response model containing search results."""

    status: str = "success"
    results: list[SearchResult] = []
    error: str | None = None


# Define BentoML Service
@bentoml.service(
    resources={"cpu": "1"},
    traffic={"timeout": 60},
    port=3000,  # Specify the port number here
)
class SearchService:
    """BentoML service for handling search queries."""

    def __init__(self) -> None:
        """Initialize the SearchService."""
        logger.info("Initializing SearchService...")

    # Search API (POST method)
    @bentoml.api
    async def search(self, input_data: SearchRequest) -> SearchResponse:
        """Handle search queries and return matching results."""
        try:
            logger.info(
                "Searching for '%s' files with query: '%s'",
                input_data.file_type,
                input_data.query,
            )

            # Call the search_with_filters function
            raw_results = search_with_filters(input_data.query, input_data.file_type)

            # Format results
            formatted_results = [
                SearchResult(file_path=path, description=desc)
                for path, desc in raw_results
            ]
            return SearchResponse(results=formatted_results)

        except ValueError as e:  # More specific error handling
            logger.error(f"Search failed due to invalid input: {e!s}")
            return SearchResponse(status="failed", error="Invalid search query.")


        except (OSError, RuntimeError) as e:  # ✅ Replace blind `except Exception`
            logger.exception(f"Unexpected error: {e}")
            return SearchResponse(status="failed", error="An unexpected error.")

