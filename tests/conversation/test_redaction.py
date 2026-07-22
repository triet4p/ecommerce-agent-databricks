"""Tests for payload redaction and size validation (S3-C10, S3-A7)."""

from __future__ import annotations

import json

from ecommerce_agent.conversation.redaction import (
    compute_payload_size,
    redact_payload,
    validate_payload_size,
)


class TestRedactPayload:
    """S3-A7 / S3-C10: Fields that must never be stored."""

    def test_redact_reasoning_content(self):
        payload = {
            "type": "message",
            "id": "msg_123",
            "content": [{"type": "output_text", "text": "Hello"}],
            "reasoning_content": "raw provider reasoning here",
        }
        result = redact_payload(payload)
        assert result["reasoning_content"] == "<redacted>"

    def test_redact_reasoning_field(self):
        payload = {
            "type": "message",
            "reasoning": "deep think about this",
        }
        result = redact_payload(payload)
        assert result["reasoning"] == "<redacted>"

    def test_redact_authorization(self):
        payload = {"authorization": "Bearer fake-token"}
        result = redact_payload(payload)
        assert result["authorization"] == "<redacted>"

    def test_redact_token_key(self):
        payload = {"access_token": "abc123", "type": "message"}
        result = redact_payload(payload)
        assert result["access_token"] == "<redacted>"

    def test_redact_secret_key(self):
        payload = {"secret": "my-secret", "type": "message"}
        result = redact_payload(payload)
        assert result["secret"] == "<redacted>"

    def test_redact_password_key(self):
        payload = {"password": "hunter2"}
        result = redact_payload(payload)
        assert result["password"] == "<redacted>"

    def test_redact_credential_key(self):
        payload = {"credential": "some-cred"}
        result = redact_payload(payload)
        assert result["credential"] == "<redacted>"

    def test_redact_nested_sensitive_keys(self):
        payload = {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": "Hello",
                    "internal_token": "should-be-redacted",
                }
            ],
        }
        result = redact_payload(payload)
        assert result["content"][0]["internal_token"] == "<redacted>"

    def test_redact_list_of_dicts(self):
        payload = {
            "items": [
                {"name": "tool1", "secret_key": "redact-this"},
                {"name": "tool2"},
            ]
        }
        result = redact_payload(payload)
        assert result["items"][0]["secret_key"] == "<redacted>"
        assert result["items"][1]["name"] == "tool2"

    def test_preserve_normal_fields(self):
        payload = {
            "type": "message",
            "id": "msg_123",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hello world"}],
        }
        result = redact_payload(payload)
        assert result["type"] == "message"
        assert result["id"] == "msg_123"
        assert result["role"] == "assistant"
        assert result["content"][0]["text"] == "Hello world"

    def test_redact_from_json_string(self):
        payload_str = json.dumps({"type": "message", "secret": "sensitive"})
        result = redact_payload(payload_str)
        assert result["secret"] == "<redacted>"

    def test_redact_non_dict_fallback(self):
        result = redact_payload("just a string")
        assert "redacted" in result
        assert result["redacted"] is True


class TestValidatePayloadSize:
    """S3-C10: Maximum item-size validation."""

    def test_small_payload_passes(self):
        payload = {"type": "message", "text": "Hello"}
        assert validate_payload_size(payload) is True

    def test_large_payload_fails(self, monkeypatch):
        # Temporarily lower the limit
        import ecommerce_agent.conversation.redaction as R
        monkeypatch.setattr(R, "_MAX_PAYLOAD_BYTES", 10)
        payload = {"type": "message", "data": "x" * 1000}
        assert validate_payload_size(payload) is False

    def test_compute_payload_size(self):
        payload = {"type": "message"}
        size = compute_payload_size(payload)
        assert isinstance(size, int)
        assert size > 0
