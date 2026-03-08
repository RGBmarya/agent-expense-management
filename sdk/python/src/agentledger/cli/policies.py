"""Policy management CLI commands."""

from __future__ import annotations

from typing import List, Optional

import httpx
import typer

from agentledger.cli.auth import get_api_key, get_endpoint
from agentledger.cli.output import console, print_policies_table

policies_app = typer.Typer(name="policies", help="Spend policy management")


def _api(method: str, path: str, **kwargs):
    api_key = get_api_key()
    endpoint = get_endpoint()
    if not api_key:
        console.print("[red]Not authenticated. Run 'agentledger login' first.[/red]")
        raise typer.Exit(1)
    resp = httpx.request(
        method,
        f"{endpoint}/v1{path}",
        headers={"X-API-Key": api_key},
        **kwargs,
    )
    resp.raise_for_status()
    if resp.status_code == 204:
        return None
    return resp.json()


@policies_app.command("create")
def create(
    name: str = typer.Option(..., "--name", "-n"),
    max_txn: Optional[float] = typer.Option(None, "--max-txn"),
    daily_limit: Optional[float] = typer.Option(None, "--daily-limit"),
    monthly_limit: Optional[float] = typer.Option(None, "--monthly-limit"),
    allowed_mccs: Optional[List[str]] = typer.Option(None, "--allowed-mccs"),
    blocked_mccs: Optional[List[str]] = typer.Option(None, "--blocked-mccs"),
    require_approval_above: Optional[float] = typer.Option(None, "--require-approval-above"),
    is_default: bool = typer.Option(False, "--default"),
):
    """Create a new spend policy."""
    body = {"name": name}
    if max_txn is not None:
        body["max_transaction_usd"] = max_txn
    if daily_limit is not None:
        body["daily_limit_usd"] = daily_limit
    if monthly_limit is not None:
        body["monthly_limit_usd"] = monthly_limit
    if allowed_mccs:
        body["allowed_mccs"] = allowed_mccs
    if blocked_mccs:
        body["blocked_mccs"] = blocked_mccs
    if require_approval_above is not None:
        body["require_approval_above_usd"] = require_approval_above
    if is_default:
        body["is_default"] = True

    data = _api("POST", "/policies", json=body)
    console.print(f"[green]Policy created:[/green] {data['id']}")


@policies_app.command("list")
def list_policies():
    """List all spend policies."""
    data = _api("GET", "/policies")
    if not data:
        console.print("[dim]No policies found.[/dim]")
        return
    print_policies_table(data)


@policies_app.command("attach")
def attach(
    policy_id: str = typer.Argument(...),
    card_id: str = typer.Argument(...),
):
    """Attach a policy to a card."""
    _api("POST", f"/policies/{policy_id}/attach", json={"card_ids": [card_id]})
    console.print(f"[green]Policy {policy_id[:12]} attached to card {card_id[:12]}.[/green]")


@policies_app.command("detach")
def detach(
    policy_id: str = typer.Argument(...),
    card_id: str = typer.Argument(...),
):
    """Detach a policy from a card."""
    _api("POST", f"/policies/{policy_id}/detach", json={"card_ids": [card_id]})
    console.print(f"[yellow]Policy {policy_id[:12]} detached from card {card_id[:12]}.[/yellow]")
