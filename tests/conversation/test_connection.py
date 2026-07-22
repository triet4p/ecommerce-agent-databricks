"""Tests for Lakebase connection module (S3-B3, S3-B4)."""

from __future__ import annotations

import pytest

from ecommerce_agent.conversation.connection import (
    LakebaseConnectionError,
    _get_connection_params,
)


class TestConnectionParams:
    """S3-B3: Connection parameter resolution from runtime-injected PG* env vars."""

    def test_missing_params_raises(self):
        """Without env vars, should raise LakebaseConnectionError."""
        with pytest.raises(LakebaseConnectionError):
            _get_connection_params()

    def test_reads_from_pg_env(self, monkeypatch):
        """PGHOST, PGDATABASE, PGUSER are read from the runtime-injected env."""
        monkeypatch.setenv("PGHOST", "my-host.example.com")
        monkeypatch.setenv("PGDATABASE", "my-db")
        monkeypatch.setenv("PGUSER", "my-user")
        monkeypatch.setenv("PGPORT", "6543")

        params = _get_connection_params()
        assert params["host"] == "my-host.example.com"
        assert params["dbname"] == "my-db"
        assert params["user"] == "my-user"
        assert params["port"] == "6543"

    def test_default_port(self, monkeypatch):
        """Default port is 5432 when PGPORT is not set."""
        monkeypatch.setenv("PGHOST", "host")
        monkeypatch.setenv("PGDATABASE", "db")
        monkeypatch.setenv("PGUSER", "user")

        params = _get_connection_params()
        assert params["port"] == "5432"

    def test_falls_back_to_local_env(self, monkeypatch):
        """Uses LAKEBASE_LOCAL_* when PG* env vars are absent."""
        monkeypatch.setenv("LAKEBASE_LOCAL_HOST", "localhost")
        monkeypatch.setenv("LAKEBASE_LOCAL_DATABASE", "test-db")
        monkeypatch.setenv("LAKEBASE_LOCAL_USER", "test-user")

        params = _get_connection_params()
        assert params["host"] == "localhost"
        assert params["dbname"] == "test-db"
        assert params["user"] == "test-user"

    def test_missing_host_raises(self, monkeypatch):
        """Raises if PGHOST is missing and no local fallback."""
        monkeypatch.setenv("PGDATABASE", "db")
        monkeypatch.setenv("PGUSER", "user")
        with pytest.raises(LakebaseConnectionError):
            _get_connection_params()
