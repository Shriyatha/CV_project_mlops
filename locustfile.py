"""Locust performance testing for a model-serving API."""

import logging
import secrets
from typing import ClassVar

from locust import HttpUser, between, task


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
            response_code = 200
            if response.status_code == response_code:
                response.success()
                logging.info("Search successful: %s", payload)
            else:
                response.failure(
                    "Search failed: %s, Payload: %s",
                    response.status_code,
                    payload,
                )
