from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from nexusgraph.identity import verify_token


def test_rejects_missing_config(monkeypatch):
    monkeypatch.delenv("NEXUSGRAPH_OIDC_ISSUER", raising=False)
    with pytest.raises(HTTPException) as error:
        verify_token("invalid")
    assert error.value.status_code == 503


def test_validated_claims_not_user_headers(monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("NEXUSGRAPH_OIDC_AUDIENCE", "nexusgraph")
    monkeypatch.setenv("NEXUSGRAPH_OIDC_JWKS_URL", "https://issuer.example/jwks")
    claims = {"tenant_id": "tenantA", "sub": "subject-123"}
    with patch("nexusgraph.identity.jwks_client") as client:
        client.return_value.get_signing_key_from_jwt.return_value.key = "test-key"
        with patch("nexusgraph.identity.jwt.decode", return_value=claims) as decode:
            identity = verify_token("signed")
            assert identity.tenant == "tenantA"
            assert identity.actor == "subject-123"
            assert decode.call_args.kwargs["algorithms"] == ["RS256"]
            assert set(decode.call_args.kwargs["options"]["require"]) == {
                "exp", "iat", "iss", "aud", "sub"
            }


def test_claim_validation(monkeypatch):
    monkeypatch.setenv("NEXUSGRAPH_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("NEXUSGRAPH_OIDC_AUDIENCE", "nexusgraph")
    monkeypatch.setenv("NEXUSGRAPH_OIDC_JWKS_URL", "https://issuer.example/jwks")
    with patch("nexusgraph.identity.jwks_client") as client:
        client.return_value.get_signing_key_from_jwt.return_value.key = "test-key"
        with patch("nexusgraph.identity.jwt.decode", return_value={"tenant_id": "../bad", "sub": "x"}):
            with pytest.raises(HTTPException) as error:
                verify_token("signed")
            assert error.value.status_code == 403
        with patch("nexusgraph.identity.jwt.decode", side_effect=jwt.InvalidSignatureError):
            with pytest.raises(HTTPException) as error:
                verify_token("signed")
            assert error.value.status_code == 401
