"""Behavior and deployment contracts for synthetic refund policy v1.0.0."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from ecommerce_agent.deploy_refund_policy import (
    CATALOG,
    FULL_FUNCTION_NAME,
    SCHEMA,
    deploy_refund_policy_function,
)
from ecommerce_agent.policies import (
    POLICY_ID,
    POLICY_VERSION,
    check_refund_eligibility,
)


BASE = {
    "order_status": "delivered",
    "claim_type": "damaged",
    "claim_date": date(2026, 8, 10),
    "evaluation_date": date(2026, 8, 10),
    "delivered_date": date(2026, 8, 1),
    "estimated_delivery_date": None,
    "evidence_provided": True,
    "item_opened": False,
    "final_sale": False,
}


def evaluate(**overrides):
    values = BASE | overrides
    return check_refund_eligibility(**values)


def assert_decision(result, decision, code):
    assert result["decision"] == decision
    assert result["decision_code"] == code
    assert result["policy_id"] == POLICY_ID
    assert result["policy_version"] == POLICY_VERSION
    assert set(result) == {
        "decision",
        "decision_code",
        "policy_id",
        "policy_version",
        "claim_type",
        "explanation",
        "reference_date",
        "deadline_date",
        "days_from_reference",
    }


@pytest.mark.parametrize("claim_type", ["damaged", "wrong_item"])
def test_seller_fault_window_is_inclusive_on_day_30(claim_type):
    delivered = date(2026, 7, 17)
    result = evaluate(
        claim_type=claim_type,
        delivered_date=delivered,
        claim_date=delivered + timedelta(days=30),
        evaluation_date=delivered + timedelta(days=30),
    )
    assert_decision(result, "eligible", "WITHIN_CLAIM_WINDOW")


def test_seller_fault_window_expires_on_day_31():
    delivered = date(2026, 7, 17)
    result = evaluate(
        delivered_date=delivered,
        claim_date=delivered + timedelta(days=31),
        evaluation_date=delivered + timedelta(days=31),
    )
    assert_decision(result, "ineligible", "CLAIM_WINDOW_EXPIRED")


def test_seller_fault_requires_evidence_even_inside_window():
    assert_decision(
        evaluate(evidence_provided=False), "ineligible", "EVIDENCE_REQUIRED"
    )


@pytest.mark.parametrize(
    ("days", "decision", "code"),
    [
        (14, "eligible", "WITHIN_CLAIM_WINDOW"),
        (15, "ineligible", "CLAIM_WINDOW_EXPIRED"),
    ],
)
def test_missing_item_boundary(days, decision, code):
    delivered = date(2026, 7, 17)
    assert_decision(
        evaluate(
            claim_type="missing_item",
            delivered_date=delivered,
            claim_date=delivered + timedelta(days=days),
            evaluation_date=delivered + timedelta(days=days),
        ),
        decision,
        code,
    )


@pytest.mark.parametrize(
    ("days", "decision", "code"),
    [
        (7, "eligible", "WITHIN_CLAIM_WINDOW"),
        (8, "ineligible", "CLAIM_WINDOW_EXPIRED"),
    ],
)
def test_remorse_window_boundary(days, decision, code):
    delivered = date(2026, 7, 17)
    assert_decision(
        evaluate(
            claim_type="remorse",
            delivered_date=delivered,
            claim_date=delivered + timedelta(days=days),
            evaluation_date=delivered + timedelta(days=days),
        ),
        decision,
        code,
    )


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"item_opened": True}, "OPENED_ITEM_EXCLUDED"),
        ({"final_sale": True}, "FINAL_SALE_EXCLUDED"),
    ],
)
def test_remorse_restrictions(overrides, code):
    assert_decision(
        evaluate(
            claim_type="remorse",
            claim_date=date(2026, 8, 5),
            evaluation_date=date(2026, 8, 5),
            **overrides,
        ),
        "ineligible",
        code,
    )


@pytest.mark.parametrize(
    ("days", "decision", "code"),
    [
        (6, "ineligible", "DELIVERY_GRACE_ACTIVE"),
        (7, "eligible", "DELIVERY_GRACE_EXPIRED"),
    ],
)
def test_not_delivered_grace_boundary(days, decision, code):
    estimate = date(2026, 7, 20)
    claim = estimate + timedelta(days=days)
    assert_decision(
        evaluate(
            order_status="shipped",
            claim_type="not_delivered",
            delivered_date=None,
            estimated_delivery_date=estimate,
            claim_date=claim,
            evaluation_date=claim,
        ),
        decision,
        code,
    )


def test_future_estimate_is_valid_but_not_yet_eligible():
    assert_decision(
        evaluate(
            order_status="approved",
            claim_type="not_delivered",
            delivered_date=None,
            estimated_delivery_date=date(2026, 8, 20),
        ),
        "ineligible",
        "DELIVERY_ESTIMATE_NOT_REACHED",
    )


def test_seller_canceled_is_immediately_eligible():
    assert_decision(
        evaluate(
            order_status="canceled",
            claim_type="seller_canceled",
            delivered_date=None,
        ),
        "eligible",
        "SELLER_CANCELED",
    )


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"claim_type": "chargeback"}, "UNSUPPORTED_CLAIM_TYPE"),
        ({"order_status": "mystery"}, "UNSUPPORTED_ORDER_STATUS"),
        ({"delivered_date": None}, "MISSING_DELIVERED_DATE"),
        (
            {"claim_date": date(2026, 8, 11)},
            "FUTURE_CLAIM_DATE",
        ),
        (
            {
                "claim_date": date(2026, 7, 16),
                "evaluation_date": date(2026, 7, 17),
            },
            "CLAIM_PREDATES_POLICY",
        ),
        (
            {
                "claim_date": date(2026, 8, 1),
                "delivered_date": date(2026, 8, 2),
            },
            "CLAIM_BEFORE_DELIVERY",
        ),
        ({"order_status": "shipped"}, "CLAIM_STATUS_CONFLICT"),
    ],
)
def test_ambiguous_or_unsupported_inputs_require_manual_review(overrides, code):
    assert_decision(evaluate(**overrides), "manual_review", code)


@pytest.mark.parametrize(
    "missing_flag",
    ["evidence_provided", "item_opened", "final_sale"],
)
def test_missing_boolean_discriminator_requires_manual_review(missing_flag):
    assert_decision(
        evaluate(**{missing_flag: None}),
        "manual_review",
        "MISSING_POLICY_DISCRIMINATOR",
    )


def test_generated_uc_function_uses_supported_python_map_contract():
    from unitycatalog.ai.core.utils.callable_utils import generate_sql_function_body

    ddl = generate_sql_function_body(
        check_refund_eligibility,
        catalog=CATALOG,
        schema=SCHEMA,
        replace=True,
    )
    quoted_name = "`ecommerce_agent`.`agent_layer`.`check_refund_eligibility`"
    assert f"CREATE OR REPLACE FUNCTION {quoted_name}" in ddl
    assert "RETURNS MAP<STRING, STRING>" in ddl
    assert "LANGUAGE PYTHON" in ddl
    assert "SYNTH-REFUND-2026-01" in ddl


def test_deployment_uses_public_function_client_contract():
    calls = []

    class FakeClient:
        def create_python_function(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(full_name=FULL_FUNCTION_NAME)

    result = deploy_refund_policy_function(client=FakeClient())

    assert result.full_name == FULL_FUNCTION_NAME
    assert calls == [
        {
            "func": check_refund_eligibility,
            "catalog": CATALOG,
            "schema": SCHEMA,
            "replace": True,
        }
    ]
