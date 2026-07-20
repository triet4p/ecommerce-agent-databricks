# Databricks notebook source
# MAGIC %md
# MAGIC ## Register system prompt vào MLflow Prompt Registry
# MAGIC Chạy 1 lần (hoặc mỗi khi sửa prompt) để tạo version mới. Sau khi chạy, điền
# MAGIC URI in ra vào `system_prompt_registry_uri` trong `config.yaml` — `agent.py` sẽ
# MAGIC tự load version đó thay vì dùng `system_prompt` inline.

# COMMAND ----------

import mlflow
import yaml

mlflow.set_registry_uri("databricks-uc")

with open("config.yaml") as f:
    raw_config = yaml.safe_load(f)

# Databricks-UC Prompt Registry yêu cầu tên đầy đủ 3 phần catalog.schema.name — KHÔNG
# dùng được tên trần như "ecommerce_support_system_prompt" (khác Prompt Registry OSS).
PROMPT_NAME = f"ecommerce_agent.agent_layer.{raw_config['use_case']}_system_prompt"

# COMMAND ----------

prompt = mlflow.genai.register_prompt(
    name=PROMPT_NAME,
    template=raw_config["system_prompt"],
    commit_message="Initial version — seeded từ config.yaml",
)
print(f"Registered: prompts:/{PROMPT_NAME}/{prompt.version}")

# COMMAND ----------
# Gắn alias "production" — cho phép rollback bằng cách trỏ alias sang version khác,
# không cần sửa config.yaml.

mlflow.genai.set_prompt_alias(
    name=PROMPT_NAME, alias="production", version=prompt.version
)
print(f"system_prompt_registry_uri: prompts:/{PROMPT_NAME}@production")
