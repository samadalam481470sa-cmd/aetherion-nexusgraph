"""Simple HMAC-safe demo API-key gate, not a replacement for enterprise OIDC."""
from __future__ import annotations

import hmac
import os
import re
from dataclasses import dataclass

from fastapi import Header, HTTPException

from nexusgraph.identity import verify_token

IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


@dataclass(frozen=True)
class Principal:
    tenant: str
    actor: str


def principal(
    x_api_key: str | None = Header(default=None),
    x_tenant_id: str = Header(default="demo"),
    x_actor_id: str = Header(default="local"),
) -> Principal:
    secret = os.getenv("NEXUSGRAPH_API_KEY")
    mode = os.getenv("NEXUSGRAPH_MODE", "demo")
    if mode not in ("demo", "protected", "oidc"):
        raise HTTPException(status_code=503, detail="Invalid server security mode")
    if mode == "oidc":
        # In OIDC mode identity is derived only from the verified bearer token.
        raise HTTPException(status_code=503, detail="Use bearer principal for OIDC")
    if mode == "protected" and (not secret or len(secret) < 24):
        raise HTTPException(status_code=503, detail="Protected mode requires a strong API key")
    if secret and not hmac.compare_digest(x_api_key or "", secret):
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not IDENTIFIER.fullmatch(x_tenant_id) or not IDENTIFIER.fullmatch(x_actor_id):
        raise HTTPException(status_code=400, detail="Invalid tenant or actor identifier")
    if mode == "protected" and x_tenant_id == "demo":
        raise HTTPException(status_code=400, detail="Specify a non-demo tenant")
    return Principal(tenant=x_tenant_id, actor=x_actor_id)


def authenticated_principal(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_tenant_id: str = Header(default="demo"),
    x_actor_id: str = Header(default="local"),
) -> Principal:
    if os.getenv("NEXUSGRAPH_MODE", "demo") == "oidc":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token required")
        identity = verify_token(authorization[7:])
        return Principal(tenant=identity.tenant, actor=identity.actor)
    return principal(x_api_key, x_tenant_id, x_actor_id)
