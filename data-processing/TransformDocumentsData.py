# Databricks notebook source
# MAGIC %md
# MAGIC # Transform Documents Data from Markdown to Vector

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Config

# COMMAND ----------

dbutils.widgets.text("raw_volume_path", "/Volumes/ecommerce_agent/bronze_layer/raw_data/documents", "Path chứa file .md gốc")

CATALOG = "ecommerce_agent"
RAW_PATH = dbutils.widgets.get("raw_volume_path")

BRONZE_SCHEMA = "bronze_layer"
SILVER_SCHEMA = "silver_layer"
GOLD_SCHEMA = "gold_layer"
AGENT_SCHEMA = "agent_layer"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Define chunker

# COMMAND ----------

import re
from pydantic import BaseModel, Field
from typing import Optional
import yaml


HEADER_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?", re.DOTALL)


class HeaderNode(BaseModel):
    level: int
    header_text: str
    header_line: str
    own_content: list[str] = Field(default_factory=list)
    children: list["HeaderNode"] = Field(default_factory=list)
    parent: Optional["HeaderNode"] = None 


def parse_frontmatter(raw_text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from the markdown body.
    Returns (metadata_dict, body_without_frontmatter)."""
    match = FRONTMATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text
    yaml_block = match.group(1)
    metadata = yaml.safe_load(yaml_block) or {}
    body = raw_text[match.end():]
    return metadata, body


def build_header_tree(body: str) -> HeaderNode:
    """Parse markdown body into a header tree. Returns a synthetic root node
    (level 0) whose children are the top-level headers (usually the single H1)."""
    root = HeaderNode(level=0, header_text="", header_line="")
    stack: list[HeaderNode] = [root]

    for raw_line in body.split("\n"):
        header_match = HEADER_RE.match(raw_line)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2).strip()
            node = HeaderNode(
                level=level,
                header_text=text,
                header_line=raw_line.strip()
            )

            while stack[-1].level >= level:
                stack.pop()

            parent = stack[-1]
            node.parent = parent
            parent.children.append(node)
            stack.append(node)
        else:
            current = stack[-1]
            if current.level == 0 and raw_line.strip() == "":
                continue
            current.own_content.append(raw_line)

    return root

def _clean_own_content(lines: list[str]) -> str:
    """Trim leading/trailing blank lines from a section's own content, keep
    internal blank lines (paragraph breaks) intact."""
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return "\n".join(lines[start:end])

def _ancestor_header_lines(node: HeaderNode) -> list[str]:
    """Header lines from the top-most ancestor down to (but excluding) `node`."""
    chain = []
    cur = node.parent
    while cur is not None and cur.level > 0:
        chain.append(cur.header_line)
        cur = cur.parent
    chain.reverse()
    return chain


def generate_chunks(node: HeaderNode, chunks: list[dict], doc_metadata: dict, section_path: list[str]):
    """Recursively walk the tree. Emit a chunk for any node that has non-empty
    own_content (this includes true leaves and containers that also carry their
    own intro text). Containers with no own_content emit nothing but still pass
    their header down as injected context for descendants."""
    own_text = _clean_own_content(node.own_content) if node.level > 0 else ""
 
    if node.level > 0 and own_text:
        ancestor_lines = _ancestor_header_lines(node)
        content_parts = ancestor_lines + [node.header_line, "", own_text]
        chunk_markdown = "\n".join(content_parts).strip() + "\n"
 
        chunks.append(
            {
                "section_title": node.header_text,
                "header_level": node.level,
                "section_path": section_path + [node.header_text],
                "content": chunk_markdown,
                **doc_metadata,  # doc_type, category, last_updated, etc.
            }
        )
 
    next_path = section_path + [node.header_text] if node.level > 0 else section_path
    for child in node.children:
        generate_chunks(child, chunks, doc_metadata, next_path)

def chunk_markdown_document(raw_text: str, source_file: str | None = None) -> list[dict]:
    """Entry point: raw .md text (with YAML frontmatter) -> list of chunk dicts,
    each ready to be written to `silver.policy_chunks`."""
    metadata, body = parse_frontmatter(raw_text)
    if source_file:
        metadata = {**metadata, "source_file": source_file}
 
    tree = build_header_tree(body)
    chunks: list[dict] = []
    generate_chunks(tree, chunks, metadata, section_path=[])
    return chunks

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Đọc file từ Volume

# COMMAND ----------

from pyspark.sql import functions as F

raw_docs_df = (
    spark.read.format("text")
    .option("wholetext", "true")
    .load(f"{RAW_PATH}/*.md")
    .withColumn("source_file", F.element_at(F.split(F.col("_metadata.file_path"), "/"), -1))
    .withColumnRenamed("value", "raw_text")
    .select("source_file", 'raw_text')
)

raw_docs_df.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.{BRONZE_SCHEMA}.raw_docs")
display(raw_docs_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Chunking

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, IntegerType
 
CHUNK_SCHEMA = StructType(
    [
        StructField("chunk_id", StringType(), False),
        StructField("source_file", StringType(), False),
        StructField("section_title", StringType(), True),
        StructField("header_level", IntegerType(), True),
        StructField("section_path", StringType(), True),  # JSON-serialized list
        StructField("content", StringType(), False),
        StructField("doc_type", StringType(), True),
        StructField("category", StringType(), True),
        StructField("last_updated", StringType(), True),
    ]
)

# COMMAND ----------

def chunk_partition(pdf_iter):
    import pandas as pd
    import json
    from uuid import uuid4
 
    for pdf in pdf_iter:
        rows = []
        for _, row in pdf.iterrows():
            file_chunks = chunk_markdown_document(row["raw_text"], source_file=row["source_file"])
            for i, chunk in enumerate(file_chunks):
                rows.append(
                    {
                        "chunk_id": f"{str(uuid4())}{row['source_file']}::{i:03d}",
                        "source_file": chunk.get("source_file", row["source_file"]),
                        "section_title": chunk.get("section_title"),
                        "header_level": chunk.get("header_level"),
                        "section_path": json.dumps(chunk.get("section_path", []), ensure_ascii=False),
                        "content": chunk["content"],
                        "doc_type": chunk.get("doc_type"),
                        "category": chunk.get("category"),
                        "last_updated": str(chunk.get("last_updated")) if chunk.get("last_updated") else None,
                    }
                )
        yield pd.DataFrame(rows) if rows else pd.DataFrame(columns=[f.name for f in CHUNK_SCHEMA.fields])
 
 
policy_chunks_df = raw_docs_df.mapInPandas(chunk_partition, schema=CHUNK_SCHEMA)
policy_chunks_df.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.{SILVER_SCHEMA}.policy_chunks")
display(policy_chunks_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Vector Search Endpoints

# COMMAND ----------

spark.sql(f"ALTER TABLE {CATALOG}.{SILVER_SCHEMA}.policy_chunks SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

# COMMAND ----------

from databricks.ai_search.client import VectorSearchClient

vsc = VectorSearchClient(disable_notice=True)

ENDPOINT_NAME = "ecommerce-agent-policy-vs-endpoints"

# 1. Tạo endpoint trước (nếu chưa có) -- endpoint là hạ tầng compute cho Vector Search,
#    tách biệt hoàn toàn với index (1 endpoint có thể chứa nhiều index).
existing_endpoints = [e["name"] for e in vsc.list_endpoints().get("endpoints", [])]

if ENDPOINT_NAME not in existing_endpoints:
    vsc.create_endpoint_and_wait(
        name=ENDPOINT_NAME,
        endpoint_type="STANDARD",  # hoặc "STORAGE_OPTIMIZED" tuỳ nhu cầu
    )
    print(f"Đã tạo endpoint: {ENDPOINT_NAME}")
else:
    print(f"Endpoint {ENDPOINT_NAME} đã tồn tại, bỏ qua bước tạo.")

# COMMAND ----------

# 2. Sau khi endpoint đã sẵn sàng (status ONLINE), mới tạo index
index_name = f"{CATALOG}.{GOLD_SCHEMA}.policy_docs_index"
if vsc.index_exists(index_name=index_name):
    print(f"Index {index_name} đã tồn tại, bỏ qua bước tạo.")
else:
    print(f"Đang tạo index {index_name}...")
    vsc.create_delta_sync_index(
        endpoint_name=ENDPOINT_NAME,
        index_name=index_name,
        source_table_name=f"{CATALOG}.{SILVER_SCHEMA}.policy_chunks",
        primary_key="chunk_id",
        embedding_source_column="content",
        embedding_model_endpoint_name="databricks-gte-large-en",
        pipeline_type="TRIGGERED",
        columns_to_sync=[
            "chunk_id",
            "content",
            "source_file",
            "section_title",
            "header_level",
            "section_path",
            "doc_type",
            "category",
            "last_updated",
        ],
    )

# COMMAND ----------

index = vsc.get_index(index_name=index_name)
print(index.describe())

# COMMAND ----------

query_text = "Hi, I bought a smartphone for R$ 1,200 on June 5, 2018. It recently suffered a severe screen crack after it accidentally slipped out of my hand. Since it's still within the 12-month active coverage period for Electronics, I want to open a claim to get a free repair or replacement. Can you assist me with this?"
results = index.similarity_search(
    query_text=query_text,
    columns=['chunk_id', 'content', 'source_file', 'section_path'],
    num_results=5
)

display(results)

# COMMAND ----------

results['result'].keys()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Search-with-rerank Model

# COMMAND ----------

import mlflow
import pandas as pd
from mlflow.pyfunc import PythonModel


class SearchAndRerankModel(PythonModel):
    def load_context(self, context):
        from sentence_transformers import CrossEncoder
        from databricks.ai_search.client import VectorSearchClient

        self.reranker = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        self.vsc = VectorSearchClient(disable_notice=True)
        self.index = self.vsc.get_index(
            index_name=f"{CATALOG}.{GOLD_SCHEMA}.policy_docs_index",
        )

    def predict(self, context, model_input: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        import json

        results = []
        for _, row in model_input.iterrows():
            query = row['query_text']
            top_k = int(row.get("top_k", 3))
            over_fetch_k = int(row.get('over_fetch_k', 15))

            raw = self.index.similarity_search(
                query_text=query,
                columns=['chunk_id', 'content', 'source_file', 'section_path', 'section_title', 'doc_type', 'category'],
                num_results=over_fetch_k
            )

            candidates = raw['result']['data_array']
            if not candidates:
                results.append({
                    "query_text": query,
                    "results_json": "[]"
                })
                continue

            pairs = [(query, c[1]) for c in candidates]
            scores = self.reranker.predict(pairs)

            reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:top_k]

            payload = [{
                "chunk_id": c[0],
                "content": c[1],
                "source_file": c[2],
                "section_path": c[3],
                "section_title": c[4],
                "doc_type": c[5],
                "category": c[6],
                "rerank_score": float(score),
            } for c, score in reranked]

            results.append({"query_text": query, "results_json": json.dumps(payload, ensure_ascii=False)})
 
        return pd.DataFrame(results)



# COMMAND ----------

from mlflow.models.resources import DatabricksVectorSearchIndex

mlflow.set_registry_uri("databricks-uc")
MODEL_NAME = f"{CATALOG}.{AGENT_SCHEMA}.search_and_rerank_model"

FORCE_CREATE = False
if FORCE_CREATE:
    with mlflow.start_run(run_name="search_and_rerank_model"):
        example_input = pd.DataFrame({
            "query_text": ["Hi, I bought a smartphone for R$ 1,200 on June 5, 2018. It recently suffered a severe screen crack after it accidentally slipped out of my hand. Since it's still within the 12-month active coverage period for Electronics, I want to open a claim to get a free repair or replacement. Can you assist me with this?"],
            "top_k": [5],
            "over_fetch_k": [15]
        })

        model_info = mlflow.pyfunc.log_model(
            name="search_and_rerank_model",
            python_model=SearchAndRerankModel(),
            input_example=example_input,
            pip_requirements=["mlflow", "mlflow-skinny[databricks]", "sentence-transformers", "databricks-ai-search"],
            registered_model_name=MODEL_NAME,
            resources=[
                DatabricksVectorSearchIndex(index_name=index_name),
            ],
        )
    
    print(f"Registered model: {MODEL_NAME}, version info: {model_info.registered_model_version}")

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedModelInput
from databricks.sdk.errors import NotFound

w = WorkspaceClient()

SERVING_ENDPOINT_NAME = "search-and-rerank-endpoint"
# Get the latest model version from Unity Catalog
versions = list(w.model_versions.list(MODEL_NAME))
if not versions:
    raise ValueError(f"No versions found for model {MODEL_NAME}")

# Get the highest version number
NEW_MODEL_VERSION = str(max([int(v.version) for v in versions]))
print(f"Using model version: {NEW_MODEL_VERSION}")

new_served_model = ServedModelInput(
    model_name=MODEL_NAME,
    model_version=NEW_MODEL_VERSION,
    workload_size="Small",
    scale_to_zero_enabled=True,
)

try:
    endpoint = w.serving_endpoints.get(SERVING_ENDPOINT_NAME)
    exists = True
except NotFound:
    exists = False

if not exists:
    # Chưa từng tạo -> tạo mới hoàn toàn
    print(f"Endpoint {SERVING_ENDPOINT_NAME} chưa tồn tại -> tạo mới.")
    w.serving_endpoints.create(
        name=SERVING_ENDPOINT_NAME,
        config=EndpointCoreConfigInput(served_models=[new_served_model]),
    )

else:
    state = endpoint.state.ready if endpoint.state else None
    config_update = endpoint.state.config_update if endpoint.state else None

    # QUAN TRỌNG: state/config_update là Enum (EndpointStateReady, EndpointStateConfigUpdate).
    # str(state) trả về "EndpointStateReady.NOT_READY" (kèm tên class), không phải "NOT_READY"
    # -> phải dùng .value hoặc so sánh trực tiếp với enum member, KHÔNG so sánh bằng str().
    state_val = state.value if state else None
    config_update_val = config_update.value if config_update else None

    if config_update_val == "UPDATE_FAILED" or state_val == "NOT_READY":
        # Case đúng với lỗi bạn gặp: config version cũ deploy failed
        # -> KHÔNG dùng create (sẽ báo lỗi endpoint đã tồn tại), phải update_config
        # để đẩy lên 1 config version mới, trỏ vào model version mới đã fix.
        print(f"Endpoint {SERVING_ENDPOINT_NAME} đang ở trạng thái lỗi ({config_update_val}/{state_val}) -> update_config với model version mới.")
        w.serving_endpoints.update_config(
            name=SERVING_ENDPOINT_NAME,
            served_models=[new_served_model],
        )

    elif state_val == "READY":
        # Endpoint đang chạy tốt nhưng bạn muốn deploy version mới (rolling update)
        print(f"Endpoint {SERVING_ENDPOINT_NAME} đang READY -> update_config để rollout model version mới.")
        w.serving_endpoints.update_config(
            name=SERVING_ENDPOINT_NAME,
            served_models=[new_served_model],
        )

    else:
        # Đang trong lúc PROVISIONING/UPDATING dở dang -> không nên bắn thêm update chồng lên
        print(f"Endpoint {SERVING_ENDPOINT_NAME} đang ở trạng thái trung gian ({state_val}/{config_update_val}) "
              f"-> chờ rồi kiểm tra lại, không update ngay để tránh xung đột config version.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test with Eval Queries
# MAGIC
# MAGIC Với mỗi query: gọi endpoint -> parse `results_json` -> lấy danh sách `source_file`
# MAGIC trả về -> so khớp với `target_docs` để tính:
# MAGIC - `hit`: có ít nhất 1 target doc xuất hiện trong top-k trả về không
# MAGIC - `hit_rank`: vị trí đầu tiên (1-based) mà 1 target doc xuất hiện (None nếu miss)
# MAGIC - `matched_docs`: những target doc thực sự được tìm thấy
# MAGIC - `latency_sec`: thời gian gọi endpoint

# COMMAND ----------

from importlib.metadata import version
print(version('databricks-sdk'))

# COMMAND ----------

import time 
import json
from databricks.sdk.service.serving import DataframeSplitInput

def query_rerank_endpoint(query_text: str, top_k: int, over_fetch_k: int) -> dict:
    """Gọi Serving endpoint, trả về (results, latency_sec, error)."""
    start = time.time()
    try:
        response = w.serving_endpoints.query(
            name=SERVING_ENDPOINT_NAME,
            dataframe_split=DataframeSplitInput(
                columns=["query_text", "top_k", "over_fetch_k"],
                data=[[query_text, top_k, over_fetch_k]],
            ),
        )
        latency = time.time() - start
        prediction = response.predictions[0]
        # Phòng trường hợp SDK trả về object thay vì dict thuần (tuỳ version)
        results_json = prediction["results_json"] if isinstance(prediction, dict) else prediction.results_json
        chunks = json.loads(results_json)
        return {"chunks": chunks, "latency_sec": latency, "error": None}
    except Exception as e:
        latency = time.time() - start
        return {"chunks": [], "latency_sec": latency, "error": str(e)}

# COMMAND ----------

def evaluate_retrieval(target_docs: list, chunks: list) -> dict:
    """So khớp source_file trong các chunk trả về với target_docs mong đợi."""
    returned_docs = [c.get("source_file") for c in chunks]
    matched = [d for d in target_docs if d in returned_docs]
 
    hit_rank = None
    for i, doc in enumerate(returned_docs, start=1):
        if doc in target_docs:
            hit_rank = i
            break
 
    return {
        "hit": len(matched) > 0,
        "hit_rank": hit_rank,
        "matched_docs": matched,
        "missed_docs": [d for d in target_docs if d not in matched],
        "returned_docs": returned_docs,
    }

# COMMAND ----------

eval_rows = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.eval_queries").collect()
display(eval_rows)

# COMMAND ----------

results = []

TOP_K = 5
OVER_FETCH_K = 15

for row in eval_rows:
    print(f"Testing {row['query_id']}...", end=" ")
    query_result = query_rerank_endpoint(row["query_text"], top_k=TOP_K, over_fetch_k=OVER_FETCH_K)
 
    if query_result["error"]:
        print(f"FAIL ({query_result['error'][:80]})")
        results.append(
            {
                "query_id": row["query_id"],
                "query_text": row["query_text"],
                "target_docs": row["target_docs"],
                "hit": False,
                "hit_rank": None,
                "matched_docs": [],
                "missed_docs": row["target_docs"],
                "returned_docs": [],
                "latency_sec": query_result["latency_sec"],
                "error": query_result["error"],
            }
        )
        continue
 
    eval_result = evaluate_retrieval(row["target_docs"], query_result["chunks"])
    status = "OK " if eval_result["hit"] else "MISS"
    print(f"{status} (rank={eval_result['hit_rank']}, latency={query_result['latency_sec']:.2f}s)")
 
    results.append(
        {
            "query_id": row["query_id"],
            "query_text": row["query_text"],
            "target_docs": row["target_docs"],
            "hit": eval_result["hit"],
            "hit_rank": eval_result["hit_rank"],
            "matched_docs": eval_result["matched_docs"],
            "missed_docs": eval_result["missed_docs"],
            "returned_docs": eval_result["returned_docs"],
            "latency_sec": query_result["latency_sec"],
            "error": None,
        }
    )

# COMMAND ----------

from pyspark.sql.types import ArrayType, StructType, StructField, StringType

RESULTS_SCHEMA = StructType(
    [
        StructField("query_id", StringType(), False),
        StructField("query_text", StringType(), False),
        StructField("target_docs", ArrayType(StringType()), False),
        StructField("hit", StringType(), True),  # lưu string "true"/"false" để tránh vấn đề bool<->None
        StructField("hit_rank", StringType(), True),
        StructField("matched_docs", ArrayType(StringType()), True),
        StructField("missed_docs", ArrayType(StringType()), True),
        StructField("returned_docs", ArrayType(StringType()), True),
        StructField("latency_sec", StringType(), True),
        StructField("error", StringType(), True),
    ]
)
 
# Chuẩn hoá kiểu dữ liệu trước khi tạo DataFrame (tránh None-type inference lỗi)
normalized_results = [
    {
        **r,
        "hit": str(r["hit"]),
        "hit_rank": str(r["hit_rank"]) if r["hit_rank"] is not None else None,
        "latency_sec": str(round(r["latency_sec"], 3)),
    }
    for r in results
]
 
results_df = spark.createDataFrame(normalized_results, schema=RESULTS_SCHEMA)
 
results_table = f"{CATALOG}.{BRONZE_SCHEMA}.rerank_eval_results"
(
    results_df.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(results_table)
)
print(f"[bronze] -> {results_table} ({results_df.count()} rows)")
 
# COMMAND ----------
 
display(
    spark.table(results_table).select(
        "query_id", "hit", "hit_rank", "latency_sec", "matched_docs", "missed_docs", "error"
    )
)

# COMMAND ----------

from pyspark.sql import functions as F
 
summary = spark.table(results_table).agg(
    F.count("*").alias("total_queries"),
    F.sum(F.when(F.col("hit") == "True", 1).otherwise(0)).alias("total_hits"),
    F.round(F.avg(F.col("latency_sec").cast("double")), 3).alias("avg_latency_sec"),
    F.round(F.max(F.col("latency_sec").cast("double")), 3).alias("max_latency_sec"),
)
summary_row = summary.collect()[0]
recall = summary_row["total_hits"] / summary_row["total_queries"]
 
print(f"Recall@{TOP_K}: {recall:.2%} ({summary_row['total_hits']}/{summary_row['total_queries']})")
print(f"Avg latency: {summary_row['avg_latency_sec']}s | Max latency: {summary_row['max_latency_sec']}s")
 
display(summary)

# COMMAND ----------


