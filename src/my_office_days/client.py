from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

from .crypto import ModCryptoError, decode_payload, encode_payload


class ModApiError(RuntimeError):
    pass


class ModClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        encryption_key: str | None = None,
    ) -> None:
        headers = {"Accept": "application/json"}
        if token:
            # The Android app sends employee_session verbatim, without a
            # "Bearer" prefix.
            headers["Authorization"] = token
        self._client = httpx.Client(headers=headers, timeout=30)
        self._base_url = base_url.rstrip("/") + "/"
        self._encryption_key = encryption_key

    def __enter__(self) -> "ModClient":
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    def get(self, path: str) -> Any:
        url = urljoin(self._base_url, path.lstrip("/"))
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise ModApiError(f"My Office Days returned HTTP {status}.") from error
        except httpx.HTTPError as error:
            raise ModApiError(f"My Office Days could not be reached: {error}") from error
        try:
            return response.json()
        except ValueError as error:
            raise ModApiError("The server did not return valid JSON.") from error

    def request_login_token(self, email: str) -> Any:
        """Ask the confirmed mobile endpoint to send a one-time login token."""
        return self._post_form(
            "connection/rest/employee/reset",
            {"email": email, "forceEmail": "false", "accessTo": "app"},
        )

    def authenticate(self, email: str, token: str) -> Any:
        """Exchange a one-time login token for the app's account credentials."""
        return self._post_form(
            "connection/rest/employee/authenticate",
            {"email": email, "token": token},
        )

    def _post_form(self, path: str, data: dict[str, str]) -> Any:
        url = urljoin(self._base_url, path.lstrip("/"))
        try:
            response = self._client.post(url, data=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise ModApiError(f"My Office Days returned HTTP {status}.") from error
        except httpx.HTTPError as error:
            raise ModApiError(f"My Office Days could not be reached: {error}") from error

        try:
            body = response.json()
        except ValueError as error:
            raise ModApiError("The server did not return valid JSON.") from error
        if not isinstance(body, dict):
            raise ModApiError("The server returned an unknown login response.")
        if body.get("status") != "success":
            error_code = body.get("error")
            suffix = f" ({error_code})" if isinstance(error_code, str) else ""
            raise ModApiError(f"My Office Days rejected the login{suffix}.")
        return body

    def graphql(self, name: str, query: str, variables: dict[str, Any] | None = None) -> Any:
        """Execute one operation using the app's GraphQL batch envelope."""
        endpoint = urljoin(self._base_url, "connection/graphql")
        payload = [{"name": name, "query": query, "variables": variables or {}}]
        try:
            if self._encryption_key:
                encoded = encode_payload(json.dumps(payload, separators=(",", ":")), self._encryption_key)
                response = self._client.post(
                    endpoint,
                    content=encoded.encode("utf-8"),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "algorithm": "f0a940",
                    },
                )
            else:
                response = self._client.post(endpoint, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise ModApiError(f"My Office Days returned HTTP {status}.") from error
        except httpx.HTTPError as error:
            raise ModApiError(f"My Office Days could not be reached: {error}") from error

        try:
            if self._encryption_key:
                try:
                    encoded_body = response.json()
                except ValueError:
                    encoded_body = response.text
                if not isinstance(encoded_body, str):
                    raise ModCryptoError("The encrypted response is not a string.")
                body = json.loads(
                    decode_payload(encoded_body, self._encryption_key, response=True)
                )
            else:
                body = response.json()
        except (ValueError, ModCryptoError) as error:
            raise ModApiError("The server did not return valid JSON.") from error

        if isinstance(body, dict):
            # The app's batch API normally keys each operation result by the
            # supplied random name. Accept conventional GraphQL responses too,
            # which makes failures during live validation easier to diagnose.
            item = body.get(name, body)
            if isinstance(item, dict) and item.get("errors"):
                message = item["errors"][0].get("message", "unknown GraphQL error")
                raise ModApiError(f"My Office Days GraphQL error: {message}")
            if isinstance(item, dict):
                return item.get("data", item)
        if isinstance(body, list) and body and isinstance(body[0], dict):
            item = body[0]
            if item.get("errors"):
                message = item["errors"][0].get("message", "unknown GraphQL error")
                raise ModApiError(f"My Office Days GraphQL error: {message}")
            return item.get("data", item)
        raise ModApiError("The server returned an unknown GraphQL response.")
