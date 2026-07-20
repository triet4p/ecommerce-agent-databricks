"""
Tests for ecommerce agent Python tools (Sprint 1 tasks E11, E13).

Verifies:
- compute_delay_severity: early, on-time, each delay boundary, undelivered
- customer_value_score: negative inputs, zero history, score bounds, monotonicity
"""

from datetime import date, timedelta

import pytest

from ecommerce_agent.tools.python_tools import (
    compute_delay_severity,
    customer_value_score,
)


class TestComputeDelaySeverity:
    def test_early_delivery(self):
        """Delivery before estimated date is 'none'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 1, 5),
        )
        assert result == "none"

    def test_on_time_delivery(self):
        """Delivery exactly on estimated date is 'none'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 1, 10),
        )
        assert result == "none"

    def test_minor_delay_lower_bound(self):
        """1 day late is 'minor'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 1, 11),
        )
        assert result == "minor"

    def test_minor_delay_upper_bound(self):
        """3 days late is 'minor'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 1, 13),
        )
        assert result == "minor"

    def test_moderate_delay_lower_bound(self):
        """4 days late is 'moderate'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 1, 14),
        )
        assert result == "moderate"

    def test_moderate_delay_upper_bound(self):
        """10 days late is 'moderate'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 1, 20),
        )
        assert result == "moderate"

    def test_severe_delay(self):
        """11 days late is 'severe'."""
        result = compute_delay_severity(
            estimated_delivery_date=date(2024, 1, 10),
            actual_delivery_date=date(2024, 2, 1),
        )
        assert result == "severe"

    def test_not_delivered_none(self):
        """Not yet delivered on estimated date is 'none'."""
        result = compute_delay_severity(
            estimated_delivery_date=date.today() + timedelta(days=5),
            actual_delivery_date=None,
        )
        assert result == "none"

    def test_not_delivered_severe(self):
        """Not delivered well past estimate is 'severe'."""
        past_date = date.today() - timedelta(days=30)
        result = compute_delay_severity(
            estimated_delivery_date=past_date,
            actual_delivery_date=None,
        )
        assert result == "severe"

    def test_unknown_no_estimated_date(self):
        """No estimated date returns 'unknown'."""
        result = compute_delay_severity(
            estimated_delivery_date=None,
            actual_delivery_date=date(2024, 1, 10),
        )
        assert result == "unknown"


class TestCustomerValueScore:
    def test_zero_history(self):
        """Zero orders, zero spent, zero score should yield a low score."""
        score = customer_value_score(
            total_orders=0, total_spent=0.0, avg_review_score=0.0
        )
        assert score == 0.0

    def test_negative_orders_raises(self):
        with pytest.raises(ValueError, match="total_orders"):
            customer_value_score(
                total_orders=-1, total_spent=100.0, avg_review_score=4.0
            )

    def test_negative_spent_raises(self):
        with pytest.raises(ValueError, match="total_spent"):
            customer_value_score(
                total_orders=5, total_spent=-50.0, avg_review_score=4.0
            )

    def test_negative_review_score_raises(self):
        with pytest.raises(ValueError, match="avg_review_score"):
            customer_value_score(
                total_orders=5, total_spent=100.0, avg_review_score=-1.0
            )

    def test_score_within_bounds(self):
        """Score must be between 0 and 100."""
        score = customer_value_score(
            total_orders=50, total_spent=10000.0, avg_review_score=5.0
        )
        assert 0 <= score <= 100

    def test_score_is_bounded_at_100(self):
        """Very high inputs should be capped at 100."""
        score = customer_value_score(
            total_orders=1000, total_spent=100000.0, avg_review_score=5.0
        )
        assert score <= 100.0

    def test_monotonicity_more_orders(self):
        """More orders should not decrease score (all else equal)."""
        score_low = customer_value_score(
            total_orders=1, total_spent=100.0, avg_review_score=3.0
        )
        score_high = customer_value_score(
            total_orders=10, total_spent=100.0, avg_review_score=3.0
        )
        assert score_high >= score_low

    def test_monotonicity_more_spent(self):
        """More spending should not decrease score (all else equal)."""
        score_low = customer_value_score(
            total_orders=5, total_spent=50.0, avg_review_score=3.0
        )
        score_high = customer_value_score(
            total_orders=5, total_spent=500.0, avg_review_score=3.0
        )
        assert score_high >= score_low

    def test_monotonicity_higher_review(self):
        """Higher review score should not decrease score (all else equal)."""
        score_low = customer_value_score(
            total_orders=5, total_spent=100.0, avg_review_score=2.0
        )
        score_high = customer_value_score(
            total_orders=5, total_spent=100.0, avg_review_score=5.0
        )
        assert score_high >= score_low

    def test_typical_customer(self):
        """A typical customer with moderate history."""
        score = customer_value_score(
            total_orders=10, total_spent=500.0, avg_review_score=4.0
        )
        assert 0 < score < 100  # reasonable range
