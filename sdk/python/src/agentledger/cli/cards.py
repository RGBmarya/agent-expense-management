"""Card management CLI commands."""

from __future__ import annotations

from typing import Optional

import typer

from agentledger.cli.auth import get_api_key, get_endpoint
from agentledger.cli.output import (
    console,
    print_balance,
    print_card_detail,
    print_cards_table,
)

cards_app = typer.Typer(name="cards", help="Virtual card management")


def _get_client():
    from agentledger.cards import CardClient
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Not authenticated. Run 'agentledger login' first.[/red]")
        raise typer.Exit(1)
    return CardClient(api_key=api_key, endpoint=get_endpoint())


@cards_app.command("create")
def create(
    label: Optional[str] = typer.Option(None, "--label", "-l"),
    limit: Optional[float] = typer.Option(None, "--limit"),
    daily_limit: Optional[float] = typer.Option(None, "--daily-limit"),
    monthly_limit: Optional[float] = typer.Option(None, "--monthly-limit"),
    single_use: bool = typer.Option(False, "--single-use"),
    team: Optional[str] = typer.Option(None, "--team"),
    project: Optional[str] = typer.Option(None, "--project"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id"),
    program: Optional[str] = typer.Option(None, "--program", "-p"),
):
    """Create a new virtual card."""
    client = _get_client()
    card = client.create(
        label=label,
        agent_id=agent_id,
        spending_limit_usd=limit,
        daily_limit_usd=daily_limit,
        monthly_limit_usd=monthly_limit,
        single_use=single_use,
        team=team,
        project=project,
        spend_program_id=program,
    )
    console.print(f"[green]Card created:[/green] {card.id}")
    print_card_detail({"id": card.id, "label": card.label, "status": card.status,
                       "card_type": card.card_type, "last4": card.last4,
                       "spending_limit_usd": str(card.spending_limit_usd) if card.spending_limit_usd else None,
                       "daily_limit_usd": str(card.daily_limit_usd) if card.daily_limit_usd else None,
                       "monthly_limit_usd": str(card.monthly_limit_usd) if card.monthly_limit_usd else None,
                       "agent_id": card.agent_id, "team": card.team,
                       "project": card.project, "created_at": card.created_at})


@cards_app.command("list")
def list_cards(
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    team: Optional[str] = typer.Option(None, "--team"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id"),
):
    """List virtual cards."""
    client = _get_client()
    cards = client.list(status=status, agent_id=agent_id, team=team)
    if not cards:
        console.print("[dim]No cards found.[/dim]")
        return
    print_cards_table([
        {"id": c.id, "label": c.label, "status": c.status, "card_type": c.card_type,
         "last4": c.last4,
         "spending_limit_usd": str(c.spending_limit_usd) if c.spending_limit_usd else None,
         "team": c.team, "agent_id": c.agent_id}
        for c in cards
    ])


@cards_app.command("details")
def details(card_id: str = typer.Argument(...)):
    """Show card details."""
    client = _get_client()
    card = client.get(card_id)
    print_card_detail({
        "id": card.id, "label": card.label, "status": card.status,
        "card_type": card.card_type, "last4": card.last4,
        "spending_limit_usd": str(card.spending_limit_usd) if card.spending_limit_usd else None,
        "daily_limit_usd": str(card.daily_limit_usd) if card.daily_limit_usd else None,
        "monthly_limit_usd": str(card.monthly_limit_usd) if card.monthly_limit_usd else None,
        "agent_id": card.agent_id, "team": card.team,
        "project": card.project, "created_at": card.created_at,
    })


@cards_app.command("balance")
def balance(card_id: str = typer.Argument(...)):
    """Check card balance."""
    client = _get_client()
    bal = client.balance(card_id)
    print_balance({
        "card_id": bal.card_id,
        "spending_limit_usd": str(bal.spending_limit_usd) if bal.spending_limit_usd else None,
        "total_spent_usd": str(bal.total_spent_usd),
        "remaining_usd": str(bal.remaining_usd) if bal.remaining_usd is not None else None,
        "daily_spent_usd": str(bal.daily_spent_usd),
        "monthly_spent_usd": str(bal.monthly_spent_usd),
    })


@cards_app.command("freeze")
def freeze(card_id: str = typer.Argument(...)):
    """Freeze a card."""
    client = _get_client()
    card = client.freeze(card_id)
    console.print(f"[yellow]Card {card.id} frozen.[/yellow]")


@cards_app.command("unfreeze")
def unfreeze(card_id: str = typer.Argument(...)):
    """Unfreeze a card."""
    client = _get_client()
    card = client.unfreeze(card_id)
    console.print(f"[green]Card {card.id} unfrozen.[/green]")


@cards_app.command("close")
def close(card_id: str = typer.Argument(...)):
    """Permanently close a card."""
    client = _get_client()
    card = client.close(card_id)
    console.print(f"[red]Card {card.id} closed.[/red]")


@cards_app.command("fund")
def fund(amount: float = typer.Option(..., "--amount", "-a")):
    """Create a funding session for card balance."""
    import httpx
    api_key = get_api_key()
    endpoint = get_endpoint()
    resp = httpx.post(
        f"{endpoint}/v1/cards/fund",
        json={"amount_usd": amount},
        headers={"X-API-Key": api_key},
    )
    resp.raise_for_status()
    data = resp.json()
    console.print(f"[green]Funding session created.[/green]")
    console.print(f"Open this URL to complete funding: {data['checkout_url']}")
