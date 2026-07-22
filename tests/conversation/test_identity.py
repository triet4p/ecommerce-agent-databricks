from __future__ import annotations

import pytest

from ecommerce_agent.conversation.identity import (
    TrustedIdentityError,
    normalize_owner,
    trusted_owner_from_headers,
)


def test_normalize_owner_is_canonical() -> None:
    assert normalize_owner(" User@Example.COM ") == "user@example.com"


@pytest.mark.parametrize("value", ["", " unknown@unknown ", "x" * 256])
def test_normalize_owner_rejects_untrusted_values(value: str) -> None:
    with pytest.raises(TrustedIdentityError):
        normalize_owner(value)


def test_forwarded_header_is_the_only_identity_source() -> None:
    assert (
        trusted_owner_from_headers({"X-Forwarded-User": "User@Example.com"})
        == "user@example.com"
    )
    with pytest.raises(TrustedIdentityError):
        trusted_owner_from_headers({"owner": "attacker@example.com"})
