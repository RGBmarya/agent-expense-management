"""Rich table formatting utilities for CLI output."""

from __future__ import annotations

from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

console = Console()


def print_cards_table(cards: List[Dict[str, Any]]) -> None:
    table = Table(title="Virtual Cards")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Label")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Last4")
    table.add_column("Limit")
    table.add_column("Team")
    table.add_column("Agent")

    for c in cards:
        status_style = {
            "active": "green",
            "frozen": "yellow",
            "closed": "red",
            "pending": "dim",
        }.get(c.get("status", ""), "")

        limit = c.get("spending_limit_usd")
        limit_str = f"${limit}" if limit else "No limit"

        table.add_row(
            c["id"][:12],
            c.get("label") or "-",
            f"[{status_style}]{c.get('status', '-')}[/{status_style}]",
            c.get("card_type", "-"),
            c.get("last4") or "-",
            limit_str,
            c.get("team") or "-",
            c.get("agent_id") or "-",
        )

    console.print(table)


def print_card_detail(card: Dict[str, Any]) -> None:
    table = Table(title="Card Details", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    fields = [
        ("ID", card["id"]),
        ("Label", card.get("label") or "-"),
        ("Status", card.get("status", "-")),
        ("Type", card.get("card_type", "-")),
        ("Last4", card.get("last4") or "-"),
        ("Spending Limit", f"${card['spending_limit_usd']}" if card.get("spending_limit_usd") else "No limit"),
        ("Daily Limit", f"${card['daily_limit_usd']}" if card.get("daily_limit_usd") else "No limit"),
        ("Monthly Limit", f"${card['monthly_limit_usd']}" if card.get("monthly_limit_usd") else "No limit"),
        ("Agent", card.get("agent_id") or "-"),
        ("Team", card.get("team") or "-"),
        ("Project", card.get("project") or "-"),
        ("Created", card.get("created_at", "-")),
    ]
    for field, value in fields:
        table.add_row(field, str(value))

    console.print(table)


def print_balance(balance: Dict[str, Any]) -> None:
    table = Table(title="Card Balance")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    limit = balance.get("spending_limit_usd")
    remaining = balance.get("remaining_usd")

    table.add_row("Total Spent", f"${balance['total_spent_usd']}")
    table.add_row("Spending Limit", f"${limit}" if limit else "No limit")
    table.add_row("Remaining", f"${remaining}" if remaining is not None else "Unlimited")
    table.add_row("Daily Spent", f"${balance['daily_spent_usd']}")
    table.add_row("Daily Limit", f"${balance.get('daily_limit_usd')}" if balance.get("daily_limit_usd") else "No limit")
    table.add_row("Monthly Spent", f"${balance['monthly_spent_usd']}")
    table.add_row("Monthly Limit", f"${balance.get('monthly_limit_usd')}" if balance.get("monthly_limit_usd") else "No limit")

    console.print(table)


def print_policies_table(policies: List[Dict[str, Any]]) -> None:
    table = Table(title="Spend Policies")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Name")
    table.add_column("Scope")
    table.add_column("Max Txn")
    table.add_column("Daily Limit")
    table.add_column("Monthly Limit")
    table.add_column("Default")

    for p in policies:
        table.add_row(
            p["id"][:12],
            p["name"],
            p.get("scope", "-"),
            f"${p['max_transaction_usd']}" if p.get("max_transaction_usd") else "-",
            f"${p['daily_limit_usd']}" if p.get("daily_limit_usd") else "-",
            f"${p['monthly_limit_usd']}" if p.get("monthly_limit_usd") else "-",
            "Yes" if p.get("is_default") else "No",
        )

    console.print(table)


def print_programs_table(programs: List[Dict[str, Any]]) -> None:
    table = Table(title="Spend Programs")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Name")
    table.add_column("Card Type")
    table.add_column("Limit")
    table.add_column("Team")
    table.add_column("Active")

    for p in programs:
        table.add_row(
            p["id"][:12],
            p["name"],
            p.get("card_type", "-"),
            f"${p['spending_limit_usd']}" if p.get("spending_limit_usd") else "-",
            p.get("team") or "-",
            "Yes" if p.get("is_active") else "No",
        )

    console.print(table)


def print_spend_summary(overview: Dict[str, Any]) -> None:
    table = Table(title="Spend Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("MTD Spend", f"${overview.get('mtd_spend_usd', 0)}")
    table.add_row("Previous MTD", f"${overview.get('previous_mtd_spend_usd', 0)}")

    console.print(table)

    if overview.get("top_providers"):
        providers_table = Table(title="Top Providers")
        providers_table.add_column("Provider")
        providers_table.add_column("Cost", justify="right")
        for p in overview["top_providers"]:
            providers_table.add_row(p["key"], f"${p['total_cost_usd']}")
        console.print(providers_table)
