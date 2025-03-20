"""Locust load testing script for FastAPI and BentoML services.

This script automatically detects whether the target service is FastAPI or BentoML
and adjusts the request type (`GET` for FastAPI, `POST` for BentoML).
"""

import secrets  # Secure random selection
from typing import ClassVar

from locust import HttpUser, between, task

# Constants
HTTP_OK = 200


class SearchUser(HttpUser):
    """Simulates a user making search requests to a FastAPI or BentoML service."""

    wait_time = between(1, 5)  # Simulate real user delays between requests

    search_queries: ClassVar[list[dict[str, str]]] = [
        {"query": "cat", "file_type": "image"},
        {"query": "dog", "file_type": "video"},
        {"query": "flower", "file_type": "image"},
        {"query": "man", "file_type": "image"},
    ]

    use_post: bool = False  # True for BentoML (POST), False for FastAPI (GET)
    health_endpoint: str = "/health"  # Default FastAPI health check

    def on_start(self) -> None:
        """Detect service type by checking health endpoints."""
        # Try FastAPI health check first
        response = self.client.get("/health")
        if response.status_code == HTTP_OK:
            self.use_post = False  # FastAPI uses GET for search
            self.health_endpoint = "/health"
            return

        # If FastAPI check fails, assume BentoML and check /healthz
        response = self.client.get("/healthz")
        if response.status_code == HTTP_OK:
            self.use_post = True  # BentoML uses POST for search
            self.health_endpoint = "/healthz"
            return

        # If both fail, assume BentoML but log an issue
        self.use_post = True
        self.health_endpoint = "/healthz"


    @task(3)  # Prioritize search requests (3x more frequent)
    def search_test(self) -> None:
        """Simulate a user making a search request."""
        payload = secrets.choice(self.search_queries)  # Secure random choice

        # BentoML requires input to be wrapped inside "input_data"
        formatted_payload = {"input_data": payload}

        if self.use_post:
            response = self.client.post("/search", json=formatted_payload)
        else:
            response = self.client.get("/search", params=payload)

        if response.status_code == HTTP_OK:
            response.success()
        else:
            response.failure(
                f"Search request fail:{response.status_code}, Response:{response.text}",
            )

    @task(1)  # Less frequent health checks
    def health_check(self) -> None:
        """Perform periodic health checks."""
        # Check health using the detected endpoint
        response = self.client.get(self.health_endpoint)

        if response.status_code != HTTP_OK:
            response.failure(
                f"Health failed at {self.health_endpoint}: {response.status_code}",
            )
