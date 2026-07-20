"""Static contract for the Olist gold fields consumed by UC tool functions."""

from pathlib import Path


NOTEBOOK = Path(__file__).parents[2] / "data-processing" / "TransformOlistData.py"


def test_order_summary_materializes_seller_and_delivery_fields():
    source = NOTEBOOK.read_text(encoding="utf-8")

    assert 'alias("primary_seller_id")' in source
    assert 'alias("delivery_delay_days")' in source
    assert 'alias("seller_state")' in source
    assert 'gold_target = f"{CATALOG}.{GOLD_SCHEMA}.order_summary"' in source


def test_order_summary_is_one_row_per_order_before_gold_write():
    source = NOTEBOOK.read_text(encoding="utf-8")

    assert 'items_s.groupBy("order_id").agg(' in source
    assert 'payments_s.groupBy("order_id").agg(' in source
    assert ".saveAsTable(gold_target)" in source
