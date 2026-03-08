"""Thin wrapper around Stripe Issuing API for virtual card management."""

from __future__ import annotations

import base64
import os
from decimal import Decimal

import stripe
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

# Configure Stripe
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _get_encryption_key() -> bytes:
    """Return the 32-byte AES key from config (hex-encoded)."""
    key_hex = settings.CARD_ENCRYPTION_KEY
    if not key_hex:
        raise ValueError("CARD_ENCRYPTION_KEY not configured")
    if key_hex.strip("0") == "":
        raise ValueError(
            "CARD_ENCRYPTION_KEY is set to all zeros — generate a real key with: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return bytes.fromhex(key_hex)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string with AES-256-GCM, return base64(nonce + ciphertext)."""
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


async def create_cardholder(
    org_id: str,
    name: str = "AI Agent",
    email: str | None = None,
) -> stripe.issuing.Cardholder:
    """Create a Stripe Issuing cardholder for the organization."""
    params: dict = {
        "type": "individual",
        "name": name,
        "billing": {
            "address": {
                "line1": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94111",
                "country": "US",
            },
        },
        "metadata": {"org_id": org_id},
    }
    if email:
        params["email"] = email
    return stripe.issuing.Cardholder.create(**params)


async def create_card(
    cardholder_id: str,
    spending_limit_usd: Decimal | None = None,
    card_type: str = "virtual",
    metadata: dict | None = None,
) -> stripe.issuing.Card:
    """Create a Stripe Issuing virtual card."""
    params: dict = {
        "cardholder": cardholder_id,
        "currency": "usd",
        "type": card_type,
        "status": "active",
    }
    if spending_limit_usd is not None:
        # Stripe uses cents for spending limits
        amount_cents = int(spending_limit_usd * 100)
        params["spending_controls"] = {
            "spending_limits": [
                {
                    "amount": amount_cents,
                    "interval": "all_time",
                }
            ]
        }
    if metadata:
        params["metadata"] = metadata
    return stripe.issuing.Card.create(**params)


async def update_card(
    stripe_card_id: str,
    status: str | None = None,
    spending_controls: dict | None = None,
    metadata: dict | None = None,
) -> stripe.issuing.Card:
    """Update a Stripe Issuing card (status, limits, metadata)."""
    params: dict = {}
    if status:
        params["status"] = status
    if spending_controls:
        params["spending_controls"] = spending_controls
    if metadata:
        params["metadata"] = metadata
    return stripe.issuing.Card.modify(stripe_card_id, **params)


async def get_card_sensitive(stripe_card_id: str) -> dict:
    """Fetch PAN + CVC from Stripe and return encrypted values.

    Values are encrypted with AES-256-GCM before returning; never stored.
    """
    # Stripe test mode: retrieve card details
    card = stripe.issuing.Card.retrieve(
        stripe_card_id,
        expand=["number", "cvc"],
    )
    return {
        "number": encrypt_value(card.number),
        "cvc": encrypt_value(card.cvc),
        "exp_month": card.exp_month,
        "exp_year": card.exp_year,
    }


async def cancel_card(stripe_card_id: str) -> stripe.issuing.Card:
    """Cancel (permanently close) a Stripe card."""
    return stripe.issuing.Card.modify(stripe_card_id, status="canceled")


async def create_funding_session(
    amount_usd: Decimal,
    org_id: str,
) -> str:
    """Create a Stripe Checkout session for funding the Issuing balance.

    Returns the checkout URL.
    """
    amount_cents = int(amount_usd * 100)
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": "AgentLedger Card Funding",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={"org_id": org_id, "purpose": "card_funding"},
        success_url="https://app.agentledger.dev/cards?funded=true",
        cancel_url="https://app.agentledger.dev/cards?funded=false",
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
