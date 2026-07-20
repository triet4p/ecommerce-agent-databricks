"""
ecommerce_agent.tools.python_tools
------------------------------------
UC Functions (Python) for lightweight deterministic calculations that do not
need network egress or model loading. These are defined as plain Python
functions with type hints and docstrings suitable for conversion to
``CREATE FUNCTION ... LANGUAGE PYTHON``.

When configured as "local_function" tools in config.yaml, these are imported
directly and wrapped as LangChain tools without UC registration.

When configured as "uc_function" tools, these serve as the implementation
reference for the UC Python function that must be registered in Unity Catalog.
"""

from datetime import date


def compute_delay_severity(
    estimated_delivery_date: date,
    actual_delivery_date: date | None,
) -> str:
    """Classify the severity of a delivery delay.

    Based on shipping policy thresholds:
    - 'none': delivered on time or early (delay <= 0 days)
    - 'minor': 1-3 days late
    - 'moderate': 4-10 days late
    - 'severe': more than 10 days late, or not yet delivered past the threshold
    - 'unknown': no estimated date provided

    Args:
        estimated_delivery_date: The promised delivery date.
        actual_delivery_date: The actual delivery date, or None if not yet delivered.

    Returns:
        One of 'none', 'minor', 'moderate', 'severe', or 'unknown'.
    """
    if estimated_delivery_date is None:
        return "unknown"

    if actual_delivery_date is None:
        # Not yet delivered - compute based on how far past the estimate we are
        days_late = (date.today() - estimated_delivery_date).days
    else:
        days_late = (actual_delivery_date - estimated_delivery_date).days

    if days_late <= 0:
        return "none"
    elif days_late <= 3:
        return "minor"
    elif days_late <= 10:
        return "moderate"
    else:
        return "severe"


def customer_value_score(
    total_orders: int,
    total_spent: float,
    avg_review_score: float,
) -> float:
    """Calculate a bounded customer value score (0-100).

    Formula (documented — not used to deny service eligibility):
        score = min(100, orders_score + spent_score + review_score)
    where:
        orders_score  = min(30, total_orders * 3)
        spent_score   = min(50, total_spent / 20)
        review_score  = min(20, avg_review_score * 5)

    Args:
        total_orders: Total number of customer orders (must be >= 0).
        total_spent: Total amount spent in BRL (must be >= 0).
        avg_review_score: Average review score (0-5 scale, must be >= 0).

    Returns:
        A float between 0 and 100.

    Raises:
        ValueError: If any input is negative.
    """
    if total_orders < 0:
        raise ValueError(f"total_orders must be >= 0, got {total_orders}")
    if total_spent < 0:
        raise ValueError(f"total_spent must be >= 0, got {total_spent}")
    if avg_review_score < 0:
        raise ValueError(f"avg_review_score must be >= 0, got {avg_review_score}")

    orders_score = min(30, total_orders * 3)
    spent_score = min(50, total_spent / 20)
    review_score = min(20, avg_review_score * 5)

    return min(100.0, orders_score + spent_score + review_score)
