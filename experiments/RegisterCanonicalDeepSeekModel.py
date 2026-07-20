# Databricks notebook source
# MAGIC %md
# MAGIC # Register the verified DeepSeek artifact in the canonical UC catalog
# MAGIC
# MAGIC This notebook deliberately does not log Python model source. It
# MAGIC registers the already verified Linux-built artifact from version 4 under
# MAGIC the production Unity Catalog name, avoiding any Windows local path in
# MAGIC `MLmodel`. Run it on Databricks, then inspect the JSON emitted by the
# MAGIC final cell before reconciling the singleton endpoint.

# COMMAND ----------

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import mlflow

SOURCE_MODEL = "workspace.gold_layer.deepseek_v4_streaming_agent"
SOURCE_VERSION = "4"
CANONICAL_MODEL = "ecommerce_agent.gold_layer.deepseek_v4_streaming_agent"

mlflow.set_registry_uri("databricks-uc")

# The source is the artifact that already passed the two-turn DeepSeek tool and
# reasoning contract on Databricks serverless. Registering from models:/ copies
# its immutable artifact rather than regenerating source on the notebook client.
registered = mlflow.register_model(
    model_uri=f"models:/{SOURCE_MODEL}/{SOURCE_VERSION}",
    name=CANONICAL_MODEL,
    await_registration_for=600,
)

# COMMAND ----------

with TemporaryDirectory() as temporary_directory:
    artifact_directory = Path(
        mlflow.artifacts.download_artifacts(
            artifact_uri=f"models:/{CANONICAL_MODEL}/{registered.version}",
            dst_path=temporary_directory,
        )
    )
    mlmodel = (artifact_directory / "MLmodel").read_text(encoding="utf-8")

assert "C:\\" not in mlmodel and "F:\\" not in mlmodel, (
    "Canonical model artifact unexpectedly contains a Windows local path"
)

print(
    json.dumps(
        {
            "status": "REGISTERED",
            "source_model": SOURCE_MODEL,
            "source_version": SOURCE_VERSION,
            "canonical_model": CANONICAL_MODEL,
            "canonical_version": str(registered.version),
            "windows_paths_absent": True,
            "next_step": "Reconcile deepseek-v4-streaming-agent-lab in place only after this output passes.",
        }
    )
)
