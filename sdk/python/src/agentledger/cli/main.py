"""AgentLedger CLI — AI expense management from the terminal.

Entry point: agentledger
"""

from __future__ import annotations

import json
from typing import Optional

import typer

from agentledger.cli.auth import clear_config, get_api_key, get_endpoint, save_api_key
from agentledger.cli.cards import cards_app
from agentledger.cli.output import console, print_programs_table, print_spend_summary
from agentledger.cli.policies import policies_app

app = typer.Typer(
    name="agentledger",
    help="AgentLedger — AI expense management CLI",
    no_args_is_help=True,
)
app.add_typer(cards_app, name="cards")
app.add_typer(policies_app, name="policies")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.command()
def login(
    api_key: str = typer.Option(..., "--api-key", "-k", prompt="API Key"),
    endpoint: str = typer.Option("", "--endpoint", "-e"),
):
    """Store API key for authentication."""
    save_api_key(api_key, endpoint)
    console.print("[green]Logged in successfully.[/green]")


@app.command()
def logout():
    """Remove stored credentials."""
    clear_config()
    console.print("[dim]Logged out.[/dim]")


# ---------------------------------------------------------------------------
# Programs (inline — small enough to not warrant separate file)
# ---------------------------------------------------------------------------

programs_app = typer.Typer(name="programs", help="Spend program management")
app.add_typer(programs_app, name="programs")


def _api(method: str, path: str, **kwargs):
    import httpx
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


@programs_app.command("create")
def create_program(
    name: str = typer.Option(..., "--name", "-n"),
    limit: Optional[float] = typer.Option(None, "--limit"),
    policy: Optional[str] = typer.Option(None, "--policy", "-p"),
    team: Optional[str] = typer.Option(None, "--team"),
    auto_expire_days: Optional[int] = typer.Option(None, "--auto-expire-days"),
):
    """Create a spend program template."""
    body = {"name": name}
    if limit is not None:
        body["spending_limit_usd"] = limit
    if policy:
        body["policy_id"] = policy
    if team:
        body["team"] = team
    if auto_expire_days is not None:
        body["auto_expire_days"] = auto_expire_days

    data = _api("POST", "/programs", json=body)
    console.print(f"[green]Program created:[/green] {data['id']}")


@programs_app.command("list")
def list_programs():
    """List spend programs."""
    data = _api("GET", "/programs")
    if not data:
        console.print("[dim]No programs found.[/dim]")
        return
    print_programs_table(data)


@programs_app.command("issue")
def issue_from_program(
    program_id: str = typer.Argument(...),
    agent_id: Optional[str] = typer.Option(None, "--agent-id"),
    label: Optional[str] = typer.Option(None, "--label", "-l"),
):
    """Issue a card from a spend program."""
    body = {}
    if agent_id:
        body["agent_id"] = agent_id
    if label:
        body["label"] = label

    data = _api("POST", f"/programs/{program_id}/issue", json=body)
    console.print(f"[green]Card issued:[/green] {data['id']}")


# ---------------------------------------------------------------------------
# Spend commands
# ---------------------------------------------------------------------------

spend_app = typer.Typer(name="spend", help="Spend overview and export")
app.add_typer(spend_app, name="spend")


@spend_app.command("summary")
def spend_summary():
    """Show unified LLM + card spend summary."""
    data = _api("GET", "/dashboard/overview")
    print_spend_summary(data)


@spend_app.command("export")
def spend_export(
    start_date: Optional[str] = typer.Option(None, "--start"),
    end_date: Optional[str] = typer.Option(None, "--end"),
    output: str = typer.Option("spend_export.csv", "--output", "-o"),
):
    """Export spend data as CSV."""
    import httpx
    api_key = get_api_key()
    endpoint = get_endpoint()
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    resp = httpx.get(
        f"{endpoint}/v1/reports/csv",
        params=params,
        headers={"X-API-Key": api_key},
    )
    resp.raise_for_status()
    with open(output, "w") as f:
        f.write(resp.text)
    console.print(f"[green]Exported to {output}[/green]")


# ---------------------------------------------------------------------------
# MCP setup helper
# ---------------------------------------------------------------------------

@app.command("setup-mcp")
def setup_mcp():
    """Print MCP server configuration JSON for Claude Desktop."""
    raw_key = get_api_key()
    if raw_key and len(raw_key) > 10:
        display_key = raw_key[:6] + "..." + raw_key[-4:]
    else:
        display_key = "<your-api-key>"

    config = {
        "mcpServers": {
            "agentledger": {
                "command": "agentledger-mcp",
                "env": {
                    "AGENTLEDGER_API_KEY": display_key,
                    "AGENTLEDGER_ENDPOINT": get_endpoint(),
                },
            }
        }
    }
    console.print_json(json.dumps(config))
    if raw_key:
        console.print(
            "[dim]Note: API key is redacted above. "
            "Set AGENTLEDGER_API_KEY env var with your full key.[/dim]"
        )


if __name__ == "__main__":
    app()
