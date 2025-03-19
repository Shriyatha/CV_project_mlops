"""LOCUST FILE CODE."""
import logging
import secrets
from typing import ClassVar

from locust import HttpUser, between, task

HTTP_OK = 200  # ✅ Define a constant for the status code

class ModelServingUser(HttpUser):
    """Simulates user behavior for load testing the model-serving API."""

    wait_time = between(1, 2.5)

    search_queries: ClassVar[list[dict[str, str]]] = [
        {"query": "cat", "file_type": "image"},
        {"query": "dog", "file_type": "video"},
        {"query": "sunset", "file_type": "image"},
        {"query": "car", "file_type": "video"},
    ]

    @task
    def search_content(self) -> None:
        """Simulate a search request with randomized query parameters."""
        payload = {"input_data": secrets.choice(self.search_queries)}

        with self.client.post("/search", json=payload, catch_response=True) as response:
            if response.status_code == HTTP_OK:  # ✅ Use constant instead of 200
                response.success()
                logging.info("Search successful: %s", payload)
            else:
                response.failure(
                    f"Search failed: {response.status_code}, "
                    f"Payload: {payload}",  # ✅ Break long line
                )
