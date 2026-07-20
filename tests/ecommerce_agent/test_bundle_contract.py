"""Deployment invariants for the singleton-App / two-endpoint topology."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def test_bundle_declares_an_app_and_never_creates_a_model_serving_endpoint():
    bundle = yaml.safe_load((ROOT / "databricks.yml").read_text(encoding="utf-8"))

    assert set(bundle["resources"]) == {"apps", "experiments"}
    app = bundle["resources"]["apps"]["ecommerce_agent"]
    assert app["name"] == "${var.app_name}"
    assert app["source_code_path"] == "."


def test_bundle_resources_are_least_privilege_and_use_canonical_uc_names():
    bundle = yaml.safe_load((ROOT / "databricks.yml").read_text(encoding="utf-8"))
    resources = bundle["resources"]["apps"]["ecommerce_agent"]["resources"]

    endpoints = [
        item["serving_endpoint"] for item in resources if "serving_endpoint" in item
    ]
    assert endpoints == [
        {"name": "${var.llm_endpoint_name}", "permission": "CAN_QUERY"},
        {"name": "${var.reranker_endpoint_name}", "permission": "CAN_QUERY"},
    ]
    functions = [item["uc_securable"] for item in resources if "uc_securable" in item]
    assert {function["securable_full_name"] for function in functions} == {
        "ecommerce_agent.agent_layer.get_order_status",
        "ecommerce_agent.agent_layer.get_customer_order_history",
        "ecommerce_agent.agent_layer.get_seller_performance",
        "ecommerce_agent.agent_layer.get_shipping_delay_stats",
        "ecommerce_agent.agent_layer.check_refund_eligibility",
    }
    assert {function["permission"] for function in functions} == {"EXECUTE"}


def test_root_app_uses_locked_uv_dependencies_and_serverless_port():
    app_config = yaml.safe_load((ROOT / "app.yaml").read_text(encoding="utf-8"))

    assert app_config["command"][:2] == ["sh", "-c"]
    assert "uv run --frozen" in app_config["command"][2]
    assert "DATABRICKS_APP_PORT" in app_config["command"][2]
    assert not (ROOT / "requirements.txt").exists()
