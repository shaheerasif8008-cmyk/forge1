from __future__ import annotations

import os
import json
import typing as t

import httpx
import typer
from rich.console import Console
from rich.table import Table


app = typer.Typer(add_completion=False, help="Forge 1 Admin CLI")
console = Console()


def _api() -> httpx.Client:
    base_url = os.getenv("FORGE1_API_URL", "http://localhost:8000/api/v1").rstrip("/")
    token = os.getenv("FORGE1_ADMIN_JWT", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=base_url, headers=headers, timeout=20.0)


def _print_rows(rows: t.Sequence[t.Mapping[str, t.Any]], columns: list[str]) -> None:
    table = Table(show_header=True, header_style="bold")
    for c in columns:
        table.add_column(c)
    for r in rows:
        table.add_row(*[str(r.get(c, "")) for c in columns])
    console.print(table)


@app.command("tenant:list")
def tenant_list() -> None:
    """List tenants for current admin scope.

    There is no dedicated endpoint; use /admin/users to infer tenant id and name via current membership.
    """
    with _api() as client:
        me = client.get("/auth/me")
        me.raise_for_status()
        tenant_id = me.json().get("tenant_id")
        # Name may not be present in /auth/me; present minimal info
        _print_rows([{"id": tenant_id, "name": "(current)"}], ["id", "name"])


@app.command("tenant:create")
def tenant_create(name: str = typer.Argument(..., help="Tenant name")) -> None:
    """Create a new tenant using auth v2 registration flow.

    This uses /auth/register requiring password; for admin automation, create via DB migrations or add a dedicated admin endpoint.
    """
    with _api() as client:
        r = client.post("/auth/register", json={"email": f"admin+{name}@example.invalid", "password": "ChangeMe123!", "tenant_name": name})
        if r.status_code >= 400:
            console.print(f"[red]Failed to create tenant: {r.text}")
            raise typer.Exit(code=1)
        console.print("[green]Requested tenant creation. Check email verification flow.")


@app.command("key:create")
def key_create(employee_id: str = typer.Argument(...),) -> None:
    """Create an employee API key and print the secret once.
    Endpoint: POST /admin/keys/employees/{employee_id}/keys
    """
    with _api() as client:
        r = client.post(f"/admin/keys/employees/{employee_id}/keys")
        r.raise_for_status()
        data = r.json()
        console.print_json(json.dumps(data))


@app.command("key:revoke")
def key_revoke(key_id: str = typer.Argument(...)) -> None:
    """Revoke an employee API key.
    Endpoint: POST /admin/keys/{key_id}/revoke
    """
    with _api() as client:
        r = client.post(f"/admin/keys/{key_id}/revoke")
        r.raise_for_status()
        console.print_json(r.text)


@app.command("flags:list")
def flags_list(tenant_id: str = typer.Option(None, help="Tenant ID (default: current)")) -> None:
    with _api() as client:
        if not tenant_id:
            me = client.get("/auth/me").json()
            tenant_id = me.get("tenant_id")
        r = client.get(f"/admin/flags/list", params={"tenant_id": tenant_id})
        r.raise_for_status()
        rows = r.json()
        _print_rows(rows, ["tenant_id", "flag", "enabled", "updated_at"])


@app.command("flags:set")
def flags_set(flag: str, enabled: bool, tenant_id: str = typer.Option(None, help="Tenant ID (default: current)")) -> None:
    with _api() as client:
        if not tenant_id:
            me = client.get("/auth/me").json()
            tenant_id = me.get("tenant_id")
        r = client.post("/admin/flags/set", json={"tenant_id": tenant_id, "flag": flag, "enabled": enabled})
        r.raise_for_status()
        console.print("[green]ok")


@app.command("runs:replay")
def runs_replay(failure_id: int, reason: str = typer.Option(None), policy: str = typer.Option(None, help="JSON string for policy_override")) -> None:
    """Replay a failed run via DLQ.
    Endpoint: POST /admin/runs/{failure_id}/replay
    """
    policy_override: dict[str, t.Any] | None = json.loads(policy) if policy else None
    with _api() as client:
        r = client.post(f"/admin/runs/{failure_id}/replay", json={"reason": reason, "policy_override": policy_override})
        r.raise_for_status()
        console.print_json(r.text)


if __name__ == "__main__":
    app()


