"""Programmatic card management client for the AgentLedger API."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class Card:
    """Represents a virtual card."""

    id: str
    label: Optional[str]
    status: str
    card_type: str
    spending_limit_usd: Optional[Decimal]
    daily_limit_usd: Optional[Decimal]
    monthly_limit_usd: Optional[Decimal]
    agent_id: Optional[str]
    team: Optional[str]
    project: Optional[str]
    last4: Optional[str]
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Card:
        return cls(
            id=data["id"],
            label=data.get("label"),
            status=data["status"],
            card_type=data["card_type"],
            spending_limit_usd=Decimal(str(data["spending_limit_usd"])) if data.get("spending_limit_usd") else None,
            daily_limit_usd=Decimal(str(data["daily_limit_usd"])) if data.get("daily_limit_usd") else None,
            monthly_limit_usd=Decimal(str(data["monthly_limit_usd"])) if data.get("monthly_limit_usd") else None,
            agent_id=data.get("agent_id"),
            team=data.get("team"),
            project=data.get("project"),
            last4=data.get("last4"),
            created_at=data["created_at"],
        )


@dataclass
class CardBalance:
    """Card balance information."""

    card_id: str
    spending_limit_usd: Optional[Decimal]
    total_spent_usd: Decimal
    remaining_usd: Optional[Decimal]
    daily_spent_usd: Decimal
    monthly_spent_usd: Decimal

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CardBalance:
        return cls(
            card_id=data["card_id"],
            spending_limit_usd=Decimal(str(data["spending_limit_usd"])) if data.get("spending_limit_usd") else None,
            total_spent_usd=Decimal(str(data["total_spent_usd"])),
            remaining_usd=Decimal(str(data["remaining_usd"])) if data.get("remaining_usd") else None,
            daily_spent_usd=Decimal(str(data["daily_spent_usd"])),
            monthly_spent_usd=Decimal(str(data["monthly_spent_usd"])),
        )


@dataclass
class CardSensitive:
    """Encrypted card details (PAN + CVC)."""

    card_id: str
    number: str
    cvc: str
    exp_month: int
    exp_year: int


class CardClient:
    """Client for managing virtual cards via the AgentLedger API.

    Example::

        client = CardClient(api_key="al_...")
        card = client.create(label="research-42", spending_limit_usd=50, single_use=True)
        details = client.get_sensitive(card.id)
        balance = client.balance(card.id)
        client.close(card.id)
    """

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
        self._client = httpx.Client(
            base_url=f"{self.endpoint}/v1",
            headers={"X-API-Key": self.api_key},
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()

    def create(
        self,
        *,
        label: Optional[str] = None,
        agent_id: Optional[str] = None,
        spending_limit_usd: Optional[float] = None,
        daily_limit_usd: Optional[float] = None,
        monthly_limit_usd: Optional[float] = None,
        single_use: bool = False,
        team: Optional[str] = None,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        spend_program_id: Optional[str] = None,
    ) -> Card:
        """Create a new virtual card."""
        body: Dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if agent_id is not None:
            body["agent_id"] = agent_id
        if spending_limit_usd is not None:
            body["spending_limit_usd"] = spending_limit_usd
        if daily_limit_usd is not None:
            body["daily_limit_usd"] = daily_limit_usd
        if monthly_limit_usd is not None:
            body["monthly_limit_usd"] = monthly_limit_usd
        if single_use:
            body["card_type"] = "single_use"
        if team is not None:
            body["team"] = team
        if project is not None:
            body["project"] = project
        if environment is not None:
            body["environment"] = environment
        if spend_program_id is not None:
            body["spend_program_id"] = spend_program_id

        data = self._request("POST", "/cards", json=body)
        return Card.from_dict(data)

    def list(
        self,
        *,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        team: Optional[str] = None,
    ) -> List[Card]:
        """List virtual cards."""
        params: Dict[str, str] = {}
        if status:
            params["status"] = status
        if agent_id:
            params["agent_id"] = agent_id
        if team:
            params["team"] = team
        data = self._request("GET", "/cards", params=params)
        return [Card.from_dict(c) for c in data]

    def get(self, card_id: str) -> Card:
        """Get card details."""
        data = self._request("GET", f"/cards/{card_id}")
        return Card.from_dict(data)

    def get_sensitive(self, card_id: str) -> CardSensitive:
        """Get encrypted PAN + CVC (fetched from Stripe, never stored)."""
        data = self._request("GET", f"/cards/{card_id}/sensitive")
        return CardSensitive(
            card_id=data["card_id"],
            number=data["number"],
            cvc=data["cvc"],
            exp_month=data["exp_month"],
            exp_year=data["exp_year"],
        )

    def balance(self, card_id: str) -> CardBalance:
        """Get remaining balance on a card."""
        data = self._request("GET", f"/cards/{card_id}/balance")
        return CardBalance.from_dict(data)

    def freeze(self, card_id: str) -> Card:
        """Temporarily freeze a card."""
        data = self._request("POST", f"/cards/{card_id}/freeze")
        return Card.from_dict(data)

    def unfreeze(self, card_id: str) -> Card:
        """Unfreeze a frozen card."""
        data = self._request("POST", f"/cards/{card_id}/unfreeze")
        return Card.from_dict(data)

    def close(self, card_id: str) -> Card:
        """Permanently close a card."""
        data = self._request("POST", f"/cards/{card_id}/close")
        return Card.from_dict(data)

    def transactions(self, card_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history for a card."""
        return self._request("GET", f"/cards/{card_id}/transactions", params={"limit": str(limit)})

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
