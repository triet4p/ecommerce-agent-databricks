"""
SQL DDL contract tests (Sprint 1 task E5).

Verifies that the SQL function DDL strings are syntactically valid SQL
and conform to expected naming conventions.
"""

import re

import pytest

from ecommerce_agent.tools.sql_tools import (
    ALL_DDL,
    CATALOG_SCHEMA,
    DDL_GET_ORDER_STATUS,
    DDL_GET_CUSTOMER_ORDER_HISTORY,
    DDL_GET_SELLER_PERFORMANCE,
    DDL_GET_SHIPPING_DELAY_STATS,
)


class TestAllDDLPresent:
    def test_four_ddl_statements(self):
        assert len(ALL_DDL) == 4

    def test_each_ddl_is_non_empty(self):
        for ddl in ALL_DDL:
            assert ddl and len(ddl.strip()) > 0


class TestGetOrderStatusDDL:
    def test_creates_function(self):
        assert "CREATE OR REPLACE FUNCTION" in DDL_GET_ORDER_STATUS

    def test_correct_schema(self):
        assert CATALOG_SCHEMA in DDL_GET_ORDER_STATUS

    def test_has_return_type(self):
        assert "RETURNS TABLE" in DDL_GET_ORDER_STATUS

    def test_has_comment(self):
        assert "COMMENT" in DDL_GET_ORDER_STATUS

    def test_references_correct_table(self):
        assert "ecommerce_agent.gold_layer.order_summary" in DDL_GET_ORDER_STATUS

    def test_param_name(self):
        assert "order_id STRING" in DDL_GET_ORDER_STATUS


class TestGetCustomerOrderHistoryDDL:
    def test_creates_function(self):
        assert "CREATE OR REPLACE FUNCTION" in DDL_GET_CUSTOMER_ORDER_HISTORY

    def test_has_default_param(self):
        assert (
            "DEFAULT 10" in DDL_GET_CUSTOMER_ORDER_HISTORY
            or "default 10" in DDL_GET_CUSTOMER_ORDER_HISTORY
        )

    def test_orders_by_timestamp_desc_without_dynamic_limit(self):
        assert "ORDER BY" in DDL_GET_CUSTOMER_ORDER_HISTORY
        assert "DESC" in DDL_GET_CUSTOMER_ORDER_HISTORY
        assert "ROW_NUMBER" in DDL_GET_CUSTOMER_ORDER_HISTORY
        assert (
            "LIMIT get_customer_order_history.limit_n"
            not in DDL_GET_CUSTOMER_ORDER_HISTORY
        )


class TestGetSellerPerformanceDDL:
    def test_creates_function(self):
        assert "CREATE OR REPLACE FUNCTION" in DDL_GET_SELLER_PERFORMANCE

    def test_returns_performance_metrics(self):
        assert "avg_rating" in DDL_GET_SELLER_PERFORMANCE
        assert "total_orders" in DDL_GET_SELLER_PERFORMANCE

    def test_derives_metrics_from_published_order_summary(self):
        assert "ecommerce_agent.gold_layer.order_summary" in DDL_GET_SELLER_PERFORMANCE
        assert "primary_seller_id" in DDL_GET_SELLER_PERFORMANCE

    def test_not_commented_out(self):
        assert not DDL_GET_SELLER_PERFORMANCE.strip().startswith("--")


class TestGetShippingDelayStatsDDL:
    def test_creates_function(self):
        assert "CREATE OR REPLACE FUNCTION" in DDL_GET_SHIPPING_DELAY_STATS

    def test_has_aggregations(self):
        assert (
            "AVG" in DDL_GET_SHIPPING_DELAY_STATS
            or "avg" in DDL_GET_SHIPPING_DELAY_STATS
        )
        assert (
            "MAX" in DDL_GET_SHIPPING_DELAY_STATS
            or "max" in DDL_GET_SHIPPING_DELAY_STATS
        )

    def test_has_return_columns(self):
        assert "avg_delay_days" in DDL_GET_SHIPPING_DELAY_STATS
        assert "max_delay_days" in DDL_GET_SHIPPING_DELAY_STATS

    def test_not_commented_out(self):
        assert not DDL_GET_SHIPPING_DELAY_STATS.strip().startswith("--")


@pytest.mark.parametrize(
    "ddl",
    ALL_DDL,
    ids=lambda d: d.split(".")[-1].split("(")[0] if "get_" in d else "ddl",
)
def test_ddl_has_catalog_schema_prefix(ddl):
    """All DDLs should reference functions in the correct catalog.schema."""
    pattern = re.escape(CATALOG_SCHEMA)
    matches = re.findall(pattern, ddl)
    assert len(matches) >= 1, f"DDL does not reference {CATALOG_SCHEMA}"


@pytest.mark.parametrize("ddl", ALL_DDL)
def test_ddl_is_valid_sql_syntax(ddl):
    """Basic SQL syntax check: function keyword present."""
    assert "FUNCTION" in ddl
    assert "RETURN" in ddl or "RETURNS" in ddl or "RETURNS TABLE" in ddl
