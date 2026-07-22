"""Tests for schema migrations (S3-B5, S3-B6, S3-B7)."""

from __future__ import annotations

from ecommerce_agent.conversation.schema import MIGRATIONS, SCHEMA_VERSION


class TestMigrationDefinitions:
    """S3-B5: Migrations for conversations, turns, conversation_items."""

    def test_schema_version_is_positive(self):
        assert SCHEMA_VERSION >= 1

    def test_migrations_are_ordered(self):
        """Migrations should be in strictly increasing version order."""
        versions = [m[0] for m in MIGRATIONS]
        assert versions == sorted(versions)
        assert len(versions) == len(set(versions))

    def test_migrations_have_descriptions(self):
        for version, description, _ in MIGRATIONS:
            assert isinstance(description, str)
            assert len(description) > 0

    def test_migrations_have_sql_statements(self):
        for version, _, statements in MIGRATIONS:
            assert len(statements) > 0
            for sql in statements:
                assert isinstance(sql, str)
                assert len(sql) > 0

    def test_migration_1_creates_conversations_table(self):
        """Migration 1 should include CREATE TABLE for conversations."""
        _, _, statements = MIGRATIONS[0]
        combined = " ".join(statements)
        assert "CREATE SCHEMA IF NOT EXISTS conversations" in combined
        assert "CREATE TABLE IF NOT EXISTS conversations.conversations" in combined
        assert "CREATE TABLE IF NOT EXISTS conversations.turns" in combined
        assert "CREATE TABLE IF NOT EXISTS conversations.conversation_items" in combined

    def test_migration_1_creates_indexes(self):
        """S3-B6: Indexes for owner listing and session loading."""
        _, _, statements = MIGRATIONS[0]
        combined = " ".join(statements)
        assert "idx_conversations_owner" in combined
        assert "idx_items_conversation" in combined
        assert "idx_items_turn" in combined
        assert "idx_turns_conversation" in combined

    def test_migration_1_creates_schema_version_table(self):
        """Migration lock and tracking table."""
        _, _, statements = MIGRATIONS[0]
        combined = " ".join(statements)
        assert "_schema_version" in combined
        assert "version" in combined
