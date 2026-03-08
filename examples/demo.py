"""AgentLedger end-to-end demo script.

Demonstrates:
1. SDK initialization + LLM instrumentation
2. Virtual card creation via CardClient
3. Card balance check
4. Spend summary

Usage:
    export AGENTLEDGER_API_KEY="al_..."
    export AGENTLEDGER_ENDPOINT="http://localhost:8000"  # if running locally
    export OPENAI_API_KEY="sk-..."  # optional, for live LLM calls
    python examples/demo.py
"""

from __future__ import annotations

import os
import sys

# Add SDK to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk", "python", "src"))


def main() -> None:
    import agentledger
    from agentledger.cards import CardClient

    api_key = os.getenv("AGENTLEDGER_API_KEY", "")
    endpoint = os.getenv("AGENTLEDGER_ENDPOINT", "http://localhost:8000")

    if not api_key:
        print("Set AGENTLEDGER_API_KEY environment variable first.")
        print("  export AGENTLEDGER_API_KEY='al_...'")
        sys.exit(1)

    # ── Step 1: Initialize SDK ──────────────────────────────────────────────
    print("\n=== Step 1: Initialize AgentLedger SDK ===")
    agentledger.init(
        api_key=api_key,
        project="demo",
        team="examples",
        environment="development",
        endpoint=endpoint,
        debug=True,
    )
    patched = agentledger.instrument()
    print(f"Instrumented: {patched}")

    # ── Step 2: Make LLM calls (if OpenAI key available) ────────────────────
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("\n=== Step 2: LLM Calls ===")
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say hello in 5 words."}],
                max_tokens=20,
            )
            print(f"LLM response: {resp.choices[0].message.content}")
            print(f"Tokens: {resp.usage.prompt_tokens} in / {resp.usage.completion_tokens} out")
        except Exception as e:
            print(f"LLM call failed (expected in test mode): {e}")
    else:
        print("\n=== Step 2: Skipped LLM calls (no OPENAI_API_KEY) ===")

    # ── Step 3: Create a virtual card ───────────────────────────────────────
    print("\n=== Step 3: Create Virtual Card ===")
    cards = CardClient(api_key=api_key, endpoint=endpoint)

    try:
        card = cards.create(
            label="demo-research-card",
            spending_limit_usd=50.00,
            single_use=False,
            team="examples",
            project="demo",
        )
        print(f"Card created: {card.id}")
        print(f"  Label: {card.label}")
        print(f"  Status: {card.status}")
        print(f"  Limit: ${card.spending_limit_usd}")
    except Exception as e:
        print(f"Card creation failed: {e}")
        card = None

    # ── Step 4: Check balance ───────────────────────────────────────────────
    if card:
        print("\n=== Step 4: Card Balance ===")
        try:
            balance = cards.balance(card.id)
            print(f"  Total spent: ${balance.total_spent_usd}")
            print(f"  Remaining: ${balance.remaining_usd}")
            print(f"  Daily spent: ${balance.daily_spent_usd}")
            print(f"  Monthly spent: ${balance.monthly_spent_usd}")
        except Exception as e:
            print(f"Balance check failed: {e}")

    # ── Step 5: List cards ──────────────────────────────────────────────────
    print("\n=== Step 5: List Cards ===")
    try:
        all_cards = cards.list()
        print(f"Total cards: {len(all_cards)}")
        for c in all_cards[:5]:
            print(f"  {c.id[:12]}... | {c.label or '-'} | {c.status} | ${c.spending_limit_usd or 'no limit'}")
    except Exception as e:
        print(f"Card listing failed: {e}")

    # ── Step 6: Close the demo card ─────────────────────────────────────────
    if card:
        print("\n=== Step 6: Close Card ===")
        try:
            closed = cards.close(card.id)
            print(f"Card {closed.id} closed: status={closed.status}")
        except Exception as e:
            print(f"Card close failed: {e}")

    # ── Cleanup ─────────────────────────────────────────────────────────────
    agentledger.shutdown()
    print("\n=== Demo complete! ===")
    print("Check your dashboard at http://localhost:3000 to see the data.")


if __name__ == "__main__":
    main()
