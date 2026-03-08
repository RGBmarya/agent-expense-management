"""Typed HTTP client for the AgentLedger backend API."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

import httpx


# SSRF protection: block requests to private/internal networks
_BLOCKED_METADATA_HOSTS = {"metadata.google.internal", "169.254.169.254"}


def _validate_url(url: str) -> None:
    """Validate that *url* does not target a private or reserved IP range."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid URL (no hostname): {url}")

    # Block known cloud metadata endpoints
    if hostname in _BLOCKED_METADATA_HOSTS:
        raise ValueError(f"Requests to metadata endpoint '{hostname}' are blocked")

    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Unable to resolve hostname: {hostname}")

    for _family, _type, _proto, _canonname, sockaddr in resolved_ips:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            raise ValueError(
                f"Requests to private/reserved IP {ip} (hostname '{hostname}') are blocked"
            )


class AgentLedgerAPIClient:
    """Async HTTP client for AgentLedger backend API calls."""

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
    ):
        self.api_key = api_key or os.getenv("AGENTLEDGER_API_KEY", "")
        self.endpoint = (
            endpoint
            or os.getenv("AGENTLEDGER_ENDPOINT", "https://api.agentledger.dev")
        ).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self.endpoint}/v1",
            headers={"X-API-Key": self.api_key},
            timeout=30.0,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()

    # -- Cards --

    async def create_card(self, **kwargs: Any) -> Dict[str, Any]:
        return await self._request("POST", "/cards", json=kwargs)

    async def list_cards(self, **params: Any) -> List[Dict[str, Any]]:
        return await self._request("GET", "/cards", params=params)

    async def get_card(self, card_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/cards/{card_id}")

    async def get_card_sensitive(self, card_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/cards/{card_id}/sensitive")

    async def get_card_balance(self, card_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/cards/{card_id}/balance")

    async def freeze_card(self, card_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/cards/{card_id}/freeze")

    async def unfreeze_card(self, card_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/cards/{card_id}/unfreeze")

    async def close_card(self, card_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/cards/{card_id}/close")

    async def get_card_transactions(
        self, card_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return await self._request(
            "GET", f"/cards/{card_id}/transactions", params={"limit": str(limit)}
        )

    async def create_sub_card(self, parent_id: str, **kwargs: Any) -> Dict[str, Any]:
        return await self._request("POST", f"/cards/{parent_id}/sub-cards", json=kwargs)

    # -- Overview --

    async def get_overview(self) -> Dict[str, Any]:
        return await self._request("GET", "/dashboard/overview")

    # -- x402 --

    async def x402_fetch(self, url: str, method: str = "GET", **kwargs: Any) -> Dict[str, Any]:
        """Make an HTTP request and detect 402 Payment Required responses."""
        _validate_url(url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, **kwargs)

        if resp.status_code == 402:
            # Parse payment requirements from headers
            return {
                "status": 402,
                "payment_required": True,
                "amount": resp.headers.get("X-Payment-Amount"),
                "recipient": resp.headers.get("X-Payment-Recipient"),
                "payment_methods": resp.headers.get("X-Payment-Methods"),
                "body": resp.text,
            }

        return {
            "status": resp.status_code,
            "payment_required": False,
            "body": resp.text,
        }

    async def close(self) -> None:
        await self._client.aclose()
