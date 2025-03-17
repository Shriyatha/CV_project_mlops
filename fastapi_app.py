"""FastAPI application for handling search queries."""

import json
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from loguru import logger

from main import search_with_filters
from validators import SearchResponse, SearchResult

# Load configuration
CONFIG_PATH = Path("config/config.json")  # Change to .toml if needed
if not CONFIG_PATH.exists():
    msg = f"Configuration file not found: {CONFIG_PATH}"
    raise FileNotFoundError(msg)

try:
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        CONFIG = json.load(config_file)
except json.JSONDecodeError as error:
    error_message = "Failed to parse configuration file"
    raise RuntimeError(error_message) from error

# Initialize FastAPI
app = FastAPI(debug=CONFIG.get("fastapi", {}).get("debug", False))
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Perform a health check."""
    return {"status": "ok"}
@app.get("/search")
async def search(
    query: Annotated[str, Query(...)],
    file_type: Annotated[str, Query(...)],
) -> SearchResponse:
    """Handle search requests with query parameters."""
    logger.info(f"Received search request: query='{query}', file_type='{file_type}'")
    try:
        # Fetch results from the search function
        results = search_with_filters(query, file_type)

        formatted_results = [
            SearchResult(file_path=path, description=desc) for path, desc in results
        ]

        return SearchResponse(results=formatted_results)

    except ValueError as error:
        logger.error("Search failed due to invalid input: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    except Exception as error:
        logger.error("Error during search: %s", error)
        raise HTTPException(status_code=500, detail="Internal server error") from error

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
