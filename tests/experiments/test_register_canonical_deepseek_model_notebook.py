from pathlib import Path


def test_canonical_registration_notebook_reuses_verified_artifact() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "RegisterCanonicalDeepSeekModel.py"
    ).read_text(encoding="utf-8")

    assert 'SOURCE_MODEL = "workspace.gold_layer.deepseek_v4_streaming_agent"' in source
    assert 'CANONICAL_MODEL = "ecommerce_agent.gold_layer.deepseek_v4_streaming_agent"' in source
    assert "mlflow.register_model(" in source
    assert "pyfunc.log_model" not in source
    assert '"C:\\\\" not in mlmodel' in source
