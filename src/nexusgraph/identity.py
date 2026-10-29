"""OIDC/JWT verification with trusted claim-derived tenant and actor identity."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class Identity:
    tenant: str
    actor: str


@lru_cache(maxsize=4)
def jwks_client(url: str) -> PyJWKClient:
    if not url.startswith("https://"):
        raise ValueError("OIDC JWKS URL must use HTTPS")
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=3)


def verify_token(token: str) -> Identity:
    issuer = os.getenv("NEXUSGRAPH_OIDC_ISSUER")
    audience = os.getenv("NEXUSGRAPH_OIDC_AUDIENCE")
    jwks_url = os.getenv("NEXUSGRAPH_OIDC_JWKS_URL")
    if not issuer or not audience or not jwks_url:
        raise HTTPException(status_code=503, detail="OIDC not configured")
    try:
        key = jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=30,
        )
    except (jwt.PyJWTError, ValueError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=401, detail="Invalid identity token") from exc
    tenant = claims.get("tenant_id")
    actor = claims.get("sub")
    if not isinstance(tenant, str) or not IDENTIFIER.fullmatch(tenant):
        raise HTTPException(status_code=403, detail="Missing or invalid tenant claim")
    if not isinstance(actor, str) or not 1 <= len(actor) <= 200:
        raise HTTPException(status_code=403, detail="Missing or invalid subject claim")
    return Identity(tenant=tenant, actor=actor)


def bearer_identity(authorization: str | None = Header(default=None)) -> Identity:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    return verify_token(authorization[7:])
