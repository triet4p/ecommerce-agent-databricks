"""Credentialed UC-function contracts, enabled only when explicitly requested."""

import os

import pytest


pytestmark = pytest.mark.databricks
HAS_DATABRICKS_SQL_CREDENTIALS = bool(
    os.getenv("RUN_DATABRICKS_TESTS") == "1"
    and os.getenv("DATABRICKS_SQL_WAREHOUSE_ID")
)


@pytest.mark.skipif(
    not HAS_DATABRICKS_SQL_CREDENTIALS,
    reason=(
        "set RUN_DATABRICKS_TESTS=1 and DATABRICKS_SQL_WAREHOUSE_ID to run "
        "credentialed UC-function tests"
    ),
)
def test_unknown_order_returns_empty_result() -> None:
    """The order-status table function returns no rows, not an execution error."""
    warehouse_id = os.environ["DATABRICKS_SQL_WAREHOUSE_ID"]
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementState

    response = WorkspaceClient().statement_execution.execute_statement(
        statement=(
            "SELECT COUNT(*) FROM "
            "ecommerce_agent.agent_layer.get_order_status('__unknown_order__')"
        ),
        warehouse_id=warehouse_id,
        catalog="ecommerce_agent",
        schema="agent_layer",
        wait_timeout="50s",
    )
    assert response.status is not None
    assert response.status.state == StatementState.SUCCEEDED
    assert response.result is not None
    assert response.result.data_array == [["0"]]


@pytest.mark.skipif(
    not HAS_DATABRICKS_SQL_CREDENTIALS,
    reason=(
        "set RUN_DATABRICKS_TESTS=1 and DATABRICKS_SQL_WAREHOUSE_ID to run "
        "credentialed UC-function tests"
    ),
)
def test_refund_policy_returns_three_explicit_decision_states() -> None:
    """The deployed synthetic policy preserves eligible/ineligible/unknown."""
    warehouse_id = os.environ["DATABRICKS_SQL_WAREHOUSE_ID"]
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementState

    response = WorkspaceClient().statement_execution.execute_statement(
        statement="""
        SELECT 'boundary_eligible' AS case_name,
               ecommerce_agent.agent_layer.check_refund_eligibility(
                 'delivered', 'damaged', DATE '2026-08-16', DATE '2026-08-16',
                 DATE '2026-07-17', CAST(NULL AS DATE), true, false, false
               )['decision'] AS decision
        UNION ALL
        SELECT 'boundary_expired',
               ecommerce_agent.agent_layer.check_refund_eligibility(
                 'delivered', 'damaged', DATE '2026-08-17', DATE '2026-08-17',
                 DATE '2026-07-17', CAST(NULL AS DATE), true, false, false
               )['decision']
        UNION ALL
        SELECT 'unsupported',
               ecommerce_agent.agent_layer.check_refund_eligibility(
                 'delivered', 'chargeback', DATE '2026-08-10', DATE '2026-08-10',
                 DATE '2026-08-01', CAST(NULL AS DATE), true, false, false
               )['decision']
        UNION ALL
        SELECT 'missing_discriminator',
               ecommerce_agent.agent_layer.check_refund_eligibility(
                 'delivered', 'damaged', DATE '2026-08-10', DATE '2026-08-10',
                 DATE '2026-08-01', CAST(NULL AS DATE),
                 CAST(NULL AS BOOLEAN), false, false
               )['decision']
        ORDER BY case_name
        """,
        warehouse_id=warehouse_id,
        catalog="ecommerce_agent",
        schema="agent_layer",
        wait_timeout="50s",
    )
    assert response.status is not None
    assert response.status.state == StatementState.SUCCEEDED
    assert response.result is not None
    assert response.result.data_array == [
        ["boundary_eligible", "eligible"],
        ["boundary_expired", "ineligible"],
        ["missing_discriminator", "manual_review"],
        ["unsupported", "manual_review"],
    ]
