"""Synthetic, versioned refund policy used by the learning project."""

from __future__ import annotations

from datetime import date
from typing import Optional

POLICY_ID = "SYNTH-REFUND-2026-01"
POLICY_VERSION = "1.0.0"
POLICY_EFFECTIVE_DATE = date(2026, 7, 17)


def check_refund_eligibility(
    order_status: str,
    claim_type: str,
    claim_date: date,
    evaluation_date: date,
    delivered_date: Optional[date],
    estimated_delivery_date: Optional[date],
    evidence_provided: bool,
    item_opened: bool,
    final_sale: bool,
) -> dict[str, str]:
    """Evaluate a demo refund claim under synthetic policy SYNTH-REFUND-2026-01.

    This function is for training and demonstration only. It does not represent
    an Olist policy or legal advice. Consumers must branch on the returned
    ``decision`` and ``decision_code`` fields rather than parsing the explanation.

    Args:
        order_status: Normalized commerce order state such as delivered or shipped.
        claim_type: One of damaged, wrong_item, missing_item, remorse,
            not_delivered, or seller_canceled.
        claim_date: Calendar date on which the customer submitted the claim.
        evaluation_date: Explicit date on which this deterministic decision runs.
        delivered_date: Actual delivery date when the claim depends on delivery.
        estimated_delivery_date: Promised delivery date for not-delivered claims.
        evidence_provided: Whether required evidence accompanies the claim.
        item_opened: Whether the item was opened; relevant to remorse returns.
        final_sale: Whether the item was sold as final sale; relevant to remorse.

    Returns:
        A stable string map containing decision, decision_code, policy metadata,
        explanation, reference date, deadline, and elapsed calendar days.
    """
    from datetime import date as _date
    from datetime import timedelta

    policy_id = "SYNTH-REFUND-2026-01"
    policy_version = "1.0.0"
    policy_effective_date = _date(2026, 7, 17)

    # Keep the nested helper annotation-free: ``create_python_function`` sends
    # this function body, not module-level imports, to the UC Python sandbox.
    def result(
        decision,
        code,
        explanation,
        *,
        reference=None,
        deadline=None,
        elapsed_days=None,
    ):
        return {
            "decision": decision,
            "decision_code": code,
            "policy_id": policy_id,
            "policy_version": policy_version,
            "claim_type": normalized_claim_type,
            "explanation": explanation,
            "reference_date": reference.isoformat() if reference else "",
            "deadline_date": deadline.isoformat() if deadline else "",
            "days_from_reference": (
                str(elapsed_days) if elapsed_days is not None else ""
            ),
        }

    normalized_status = (order_status or "").strip().lower()
    normalized_claim_type = (claim_type or "").strip().lower()

    if not normalized_status:
        return result(
            "manual_review",
            "MISSING_ORDER_STATUS",
            "An order status is required for a policy-backed decision.",
        )
    if not normalized_claim_type:
        return result(
            "manual_review",
            "MISSING_CLAIM_TYPE",
            "A claim type is required for a policy-backed decision.",
        )
    if claim_date is None or evaluation_date is None:
        return result(
            "manual_review",
            "MISSING_DECISION_DATE",
            "Both claim_date and evaluation_date are required.",
        )
    if evidence_provided is None or item_opened is None or final_sale is None:
        return result(
            "manual_review",
            "MISSING_POLICY_DISCRIMINATOR",
            "Evidence, opened-item, and final-sale flags must be explicitly supplied.",
        )
    if claim_date > evaluation_date:
        return result(
            "manual_review",
            "FUTURE_CLAIM_DATE",
            "The claim date is after the explicit evaluation date.",
        )
    if claim_date < policy_effective_date:
        return result(
            "manual_review",
            "CLAIM_PREDATES_POLICY",
            "This synthetic policy was not effective on the claim date.",
        )
    if delivered_date is not None and delivered_date > evaluation_date:
        return result(
            "manual_review",
            "FUTURE_DELIVERY_DATE",
            "The delivered date is after the explicit evaluation date.",
            reference=delivered_date,
        )
    if (
        estimated_delivery_date is not None
        and estimated_delivery_date > evaluation_date
        and normalized_claim_type == "not_delivered"
    ):
        return result(
            "ineligible",
            "DELIVERY_ESTIMATE_NOT_REACHED",
            "The estimated delivery date has not been reached.",
            reference=estimated_delivery_date,
            deadline=estimated_delivery_date + timedelta(days=7),
            elapsed_days=(claim_date - estimated_delivery_date).days,
        )

    supported_claim_types = {
        "damaged",
        "wrong_item",
        "missing_item",
        "remorse",
        "not_delivered",
        "seller_canceled",
    }
    supported_statuses = {
        "created",
        "approved",
        "processing",
        "invoiced",
        "shipped",
        "delivered",
        "canceled",
        "unavailable",
    }
    if normalized_claim_type not in supported_claim_types:
        return result(
            "manual_review",
            "UNSUPPORTED_CLAIM_TYPE",
            "The claim type is not covered by this synthetic policy version.",
        )
    if normalized_status not in supported_statuses:
        return result(
            "manual_review",
            "UNSUPPORTED_ORDER_STATUS",
            "The order status is not covered by this synthetic policy version.",
        )

    if normalized_claim_type == "seller_canceled":
        if normalized_status != "canceled":
            return result(
                "manual_review",
                "CLAIM_STATUS_CONFLICT",
                "A seller-canceled claim requires a canceled order state.",
            )
        return result(
            "eligible",
            "SELLER_CANCELED",
            "A seller-canceled order is immediately eligible under the demo policy.",
            reference=claim_date,
            deadline=claim_date,
            elapsed_days=0,
        )

    delivered_claims = {"damaged", "wrong_item", "missing_item", "remorse"}
    if normalized_claim_type in delivered_claims:
        if normalized_status != "delivered":
            return result(
                "manual_review",
                "CLAIM_STATUS_CONFLICT",
                "This claim type requires a delivered order state.",
            )
        if delivered_date is None:
            return result(
                "manual_review",
                "MISSING_DELIVERED_DATE",
                "The delivered date is required for this claim type.",
            )
        if delivered_date > claim_date:
            return result(
                "manual_review",
                "CLAIM_BEFORE_DELIVERY",
                "The claim date is before the supplied delivered date.",
                reference=delivered_date,
            )

        elapsed_days = (claim_date - delivered_date).days
        windows = {
            "damaged": 30,
            "wrong_item": 30,
            "missing_item": 14,
            "remorse": 7,
        }
        window_days = windows[normalized_claim_type]
        deadline = delivered_date + timedelta(days=window_days)
        if elapsed_days > window_days:
            return result(
                "ineligible",
                "CLAIM_WINDOW_EXPIRED",
                f"The {window_days}-day inclusive claim window has expired.",
                reference=delivered_date,
                deadline=deadline,
                elapsed_days=elapsed_days,
            )
        if normalized_claim_type in {"damaged", "wrong_item", "missing_item"}:
            if not evidence_provided:
                return result(
                    "ineligible",
                    "EVIDENCE_REQUIRED",
                    "This seller-fulfillment claim requires evidence.",
                    reference=delivered_date,
                    deadline=deadline,
                    elapsed_days=elapsed_days,
                )
        if normalized_claim_type == "remorse":
            if final_sale:
                return result(
                    "ineligible",
                    "FINAL_SALE_EXCLUDED",
                    "Final-sale items are excluded from remorse returns.",
                    reference=delivered_date,
                    deadline=deadline,
                    elapsed_days=elapsed_days,
                )
            if item_opened:
                return result(
                    "ineligible",
                    "OPENED_ITEM_EXCLUDED",
                    "Opened items are excluded from remorse returns.",
                    reference=delivered_date,
                    deadline=deadline,
                    elapsed_days=elapsed_days,
                )
        return result(
            "eligible",
            "WITHIN_CLAIM_WINDOW",
            "The claim satisfies the applicable synthetic policy conditions.",
            reference=delivered_date,
            deadline=deadline,
            elapsed_days=elapsed_days,
        )

    if normalized_status in {"delivered", "canceled"}:
        return result(
            "manual_review",
            "CLAIM_STATUS_CONFLICT",
            "A not-delivered claim conflicts with the supplied order state.",
        )
    allowed_in_flight_statuses = {"approved", "processing", "invoiced", "shipped"}
    if normalized_status not in allowed_in_flight_statuses:
        return result(
            "manual_review",
            "CLAIM_STATUS_CONFLICT",
            "The order state does not establish an in-flight delivery.",
        )
    if estimated_delivery_date is None:
        return result(
            "manual_review",
            "MISSING_ESTIMATED_DELIVERY_DATE",
            "The estimated delivery date is required for a not-delivered claim.",
        )

    elapsed_days = (claim_date - estimated_delivery_date).days
    deadline = estimated_delivery_date + timedelta(days=7)
    if elapsed_days < 7:
        return result(
            "ineligible",
            "DELIVERY_GRACE_ACTIVE",
            "The seven-day delivery grace period is still active.",
            reference=estimated_delivery_date,
            deadline=deadline,
            elapsed_days=elapsed_days,
        )
    return result(
        "eligible",
        "DELIVERY_GRACE_EXPIRED",
        "The order is at least seven days past its estimated delivery date.",
        reference=estimated_delivery_date,
        deadline=deadline,
        elapsed_days=elapsed_days,
    )
