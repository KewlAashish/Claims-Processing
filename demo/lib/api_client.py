from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_SECONDS = 10.0


class DemoApiError(RuntimeError):
    """Raised when the demo cannot complete an expected API step."""


class ClaimsDemoClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("DEMO_API_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=DEFAULT_TIMEOUT_SECONDS)

    def close(self) -> None:
        self._client.close()

    def check_health(self) -> dict[str, Any]:
        return self._request("GET", "/health", expected_status=200)

    def create_member(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/members", json=payload, expected_status=201)

    def create_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/policies", json=payload, expected_status=201)

    def add_coverage_rule(self, policy_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/policies/{policy_id}/coverage-rules",
            json=payload,
            expected_status=201,
        )

    def enroll_member(self, member_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/members/{member_id}/policies",
            json=payload,
            expected_status=201,
        )

    def submit_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/claims", json=payload, expected_status=201)

    def get_claim(self, claim_id: str) -> dict[str, Any]:
        return self._request("GET", f"/claims/{claim_id}", expected_status=200)

    def pay_claim(self, claim_id: str) -> dict[str, Any]:
        return self._request("POST", f"/claims/{claim_id}/pay", expected_status=200)

    def create_dispute(self, claim_id: str, reason: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/claims/{claim_id}/disputes",
            json={"reason": reason},
            expected_status=201,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected_status: int,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise DemoApiError(
                f"Could not reach API at {self.base_url}. Start it with "
                "`uvicorn app.main:app --reload` or set DEMO_API_URL."
            ) from exc

        if response.status_code != expected_status:
            raise DemoApiError(
                f"{method} {path} expected HTTP {expected_status}, got "
                f"{response.status_code}: {response.text}"
            )

        if not response.content:
            return {}
        return response.json()
