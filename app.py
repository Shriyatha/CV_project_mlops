"""Flask application for managing API interactions and serving content."""

from __future__ import annotations  # Simplify type hints

import os
import shutil
import signal
import subprocess
import time
from typing import Any

import httpx
from flask import (
    Flask,
    Response,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from loguru import logger
from pydantic import ValidationError

from validators import SearchQuery

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")

# API URLs
API_URLS = {
    "fastapi": "http://127.0.0.1:8000/search",
    "bentoml": "http://localhost:3000/search",
}

# Constants
HTTP_OK = 200


class APIManager:
    """Manages the API process for FastAPI and BentoML."""

    def __init__(self) -> None:
        """Initialize the APIManager."""
        self.api_process: subprocess.Popen | None = None

    def wait_for_api(self, api_url: str, timeout: int = 200) -> bool:
        """Wait for the API to be ready by polling its health endpoint."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(api_url, timeout=5)
                if response.status_code == HTTP_OK:
                    logger.info("API is up and running at {}", api_url)
                    return True
            except httpx.RequestError as e:
                logger.info(f"Waiting for API to start... Error: {e}")
            time.sleep(1)
        logger.error("API did not start within {} seconds", timeout)
        return False

    def start_api(self, api_source: str) -> bool:
        """Start the selected API (FastAPI or BentoML)."""
        # Kill existing API process if running
        if self.api_process:
            logger.info("Stopping previous API process...")
            os.kill(self.api_process.pid, signal.SIGTERM)
            self.api_process.wait()  # Wait for the process to terminate

        # Start the selected API
        if api_source == "fastapi":
            logger.info("Starting FastAPI server...")
            uvicorn_path = shutil.which("uvicorn")
            uvicorn_path = shutil.which("uvicorn")
            if not uvicorn_path:
                error_msg = "uvicorn not found in PATH"
                raise ValueError(error_msg)
            if not os.access(uvicorn_path, os.X_OK):
                error_msg = "uvicorn is not executable"
                raise ValueError(error_msg)
            self.api_process = subprocess.Popen(
                [
                    uvicorn_path,
                    "fastapi_app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
            )
            api_url = "http://127.0.0.1:8000/health"
        elif api_source == "bentoml":
            logger.info("Starting BentoML server...")
            bentoml_path = shutil.which("bentoml")
            if not bentoml_path:
                error_msg = "bentoml not found in PATH"
                raise ValueError(error_msg)
            if not os.access(bentoml_path, os.X_OK):
                error_msg = "bentoml is not executable"
                raise ValueError(error_msg)

            self.api_process = subprocess.Popen(
                [
                    bentoml_path,
                    "serve",
                    "bento_service:SearchService",
                    "--port",
                    "3000",
                ],
            )
            api_url = "http://127.0.0.1:3000/healthz"
        else:
            logger.error("Unknown API source: {}", api_source)
            return False

        # Wait for API to be ready before proceeding
        if not self.wait_for_api(api_url):
            logger.error("API failed to start. Please check logs.")
            return False
        return True


# Initialize APIManager
api_manager = APIManager()


@app.route("/", methods=["GET", "POST"])
def select_api() -> Response:
    """Page to select the API source and start it."""
    if request.method == "POST":
        selected_api = request.form.get("api_source", "fastapi")
        session["api_source"] = selected_api

        # Start API and wait for it to be ready
        if api_manager.start_api(selected_api):
            return redirect(url_for("index"))
        return "Error: API failed to start.", 500

    return render_template(
        "select_api.html", selected_api=session.get("api_source", "fastapi"),
    )


def fetch_results_fastapi(validated_input: SearchQuery) -> list[dict[str, Any]]:
    """Fetch search results from the FastAPI service."""
    api_url = API_URLS["fastapi"]

    try:
        with httpx.Client(timeout=10) as client:
            logger.info(
                "Sending request to FastAPI with params {}",
                validated_input.model_dump(),
            )
            response = client.get(api_url, params=validated_input.model_dump())
            response.raise_for_status()
            api_results = response.json().get("results", [])
            logger.info("Received {} results from FastAPI", len(api_results))

            # Format results and strip the 'static/' prefix
            formatted_results = []
            for result in api_results:
                file_path = result.get("file_path", "")
                if file_path.startswith("static/images"):
                    file_path = file_path.replace("static/images", "", 1)
                if file_path.startswith("static/videos"):
                    file_path = file_path.replace("static/videos", "", 1)
                formatted_results.append({
                    "media": file_path,
                    "caption": result.get("description", "No caption available"),
                    "media_type": validated_input.file_type,
                })
            return formatted_results

    except (httpx.HTTPError, ValueError) as e:
        logger.error("Error communicating with FastAPI: {}", e)
        return [
            {
                "media": None,
                "caption": "Could not fetch results from FastAPI",
                "media_type": "text",
            },
        ]


def fetch_results_bentoml(validated_input: SearchQuery) -> list[dict[str, Any]]:
    """Fetch search results from the BentoML service."""
    api_url = API_URLS["bentoml"]

    try:
        with httpx.Client(timeout=10) as client:
            logger.info(
                "Sending request to BentoML with params {}",
                validated_input.model_dump(),
            )
            payload = {"input_data": validated_input.model_dump()}
            response = client.post(api_url, json=payload)
            response.raise_for_status()
            api_results = response.json().get("results", [])
            logger.info("Received {} results from BentoML", len(api_results))

            # Format results and strip the 'static/' prefix
            formatted_results = []
            for result in api_results:
                file_path = result.get("file_path", "")
                description = result.get("description", "No caption available")
                if file_path.startswith("static/images"):
                    file_path = file_path.replace("static/images/", "", 1)
                elif file_path.startswith("static/videos"):
                    file_path = file_path.replace("static/videos/", "", 1)
                formatted_results.append({
                    "media": file_path,
                    "caption": description,
                    "media_type": validated_input.file_type,
                })
            return formatted_results

    except httpx.HTTPError as e:
        logger.error("Error communicating with BentoML: {}", e)
        return [
            {
                "media": None,
                "caption": "Could not fetch results from BentoML",
                "media_type": "text",
            },
        ]


def fetch_results(validated_input: SearchQuery) -> list[dict[str, Any]]:
    """Fetch search results from the selected API source."""
    api_source = session.get("api_source", "fastapi")  # Default to FastAPI

    if api_source == "fastapi":
        return fetch_results_fastapi(validated_input)
    if api_source == "bentoml":
        return fetch_results_bentoml(validated_input)
    logger.error("Unknown API source: {}", api_source)
    return [{"media": None, "caption": "Unknown API source", "media_type": "text"}]


@app.route("/home", methods=["GET", "POST"])
def index() -> Response:
    """Render the home page and process user queries."""
    results = []

    if request.method == "POST":
        try:
            validated_input = SearchQuery(
                query=request.form.get("query", ""),
                file_type=request.form.get("file_type"),
            )
            results = fetch_results(validated_input)
        except ValidationError as e:
            logger.error("Validation Error: {}", e)
            results = [
                {
                    "media": None,
                    "caption": "Invalid input provided",
                    "media_type": "text",
                },
            ]

    return render_template(
        "index.html",
        results=results,
        selected_api=session.get("api_source", "fastapi"),
    )


@app.route("/images/<path:filename>")
def serve_image(filename: str) -> Response:
    """Serve static image files from the 'static/images' folder."""
    return send_from_directory("static/images", filename)


@app.route("/videos/<path:filename>")
def serve_video(filename: str) -> Response:
    """Serve static video files from the 'static/videos' folder."""
    return send_from_directory("static/videos", filename)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
