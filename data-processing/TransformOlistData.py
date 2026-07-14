# Databricks notebook source
# MAGIC %md
# MAGIC # Olist E-commerce Ingestion: Bronze -> Silver -> Gold
# MAGIC
# MAGIC **Mục đích:** Ingest raw CSV (Olist Brazilian E-commerce dataset) vào Unity Catalog,
# MAGIC clean thành Silver tables, và build 1 bảng Gold tổng hợp (`order_summary`) phục vụ
# MAGIC trực tiếp cho UC Function (SQL) của Agent.
# MAGIC
# MAGIC **Catalog structure:**
# MAGIC ```
# MAGIC ecommerce-agent
# MAGIC ├── bronze_layer   (raw, 1-1 với CSV gốc, thêm cột _ingested_at, _source_file)
# MAGIC ├── silver_layer   (cleaned: dedup, type-cast, xử lý null)
# MAGIC └── gold_layer     (order_summary: flat table cho SQL tool)
# MAGIC ```
# MAGIC
# MAGIC **Input:** CSV gốc nằm ở `/Volumes/ecommerce_agent/bronze_layer/raw_data/olist` (đổi path ở widget nếu khác).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Config & Widgets

# COMMAND ----------

# Define widgets
dbutils.widgets.text("raw_volume_path", "/Volumes/ecommerce_agent/bronze_layer/raw_data/olist", "Path chứa CSV gốc")
dbutils.widgets.dropdown("use_autoloader", "false", ["true", "false"], "Dùng Autoloader thay vì spark.read.csv?")

# Constants
CATALOG = "ecommerce_agent"
RAW_PATH = dbutils.widgets.get("raw_volume_path")
USE_AUTOLOADER = dbutils.widgets.get("use_autoloader") == "true"

BRONZE_SCHEMA = "bronze_layer"
SILVER_SCHEMA = "silver_layer"
GOLD_SCHEMA = "gold_layer"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Bronze Layer - Raw ingestion
# MAGIC
# MAGIC Mỗi file CSV gốc -> 1 bronze table, giữ nguyên schema string-first, chưa ép kiểu ở bước này.
# MAGIC Thêm 2 cột lineage: `_ingested_at` và `_source_file`.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StructType

BRONZE_FILES = {
    "olist_orders_dataset.csv": "orders_raw",
    "olist_order_items_dataset.csv": "order_items_raw",
    "olist_order_payments_dataset.csv": "order_payments_raw",
    "olist_order_reviews_dataset.csv": "order_reviews_raw",
    "olist_customers_dataset.csv": "customers_raw",
    "olist_products_dataset.csv": "products_raw",
    "olist_sellers_dataset.csv": "sellers_raw",
    "olist_geolocation_dataset.csv": "geolocation_raw",
    "product_category_name_translation.csv": "category_translation_raw",
}

def ingest_csv_batch(file_name: str, table_name: str):
    """Đọc 1 CSV bằng spark.read.csv, ghi vào bronze Delta table (overwrite mỗi lần chạy).
    Phù hợp cho dataset tĩnh, ingest 1 lần / định kỳ full-refresh."""

    full_path = f"{RAW_PATH}/{file_name}"
    df = (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .option("multiLine", "true")
        .option("escape", '"')
        .csv(full_path)
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit(file_name))
    )
    target = f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}"
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(target)
    print(f"[bronze] {file_name} -> {target} ({df.count()} rows)")

def ingest_csv_autoloader(file_name: str, table_name: str):
    """Alternative: Autoloader (cloudFiles) — dùng khi muốn ingest incremental
    (VD: CSV mới được thêm dần vào volume theo thời gian, không phải load 1 lần).
    Cần 1 checkpoint location riêng cho mỗi stream."""

    full_path = f"{RAW_PATH}/{file_name}"
    checkpoint_path = f"{RAW_PATH}/_checkpoints/{table_name}"
    target = f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}"

    stream_df = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaLocation", checkpoint_path)
        .load(full_path)
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit(file_name))
    )

    query = (
        stream_df.writeStream.format("delta")
        .option("checkpointLocation", checkpoint_path)
        .trigger(availableNow=True)
        .table(target)
    )

    query.awaitTermination()
    print(f"[bronze/autoloader] {file_name} -> {target}")

# COMMAND ----------

for file_name, table_name in BRONZE_FILES.items():
    if USE_AUTOLOADER:
        ingest_csv_autoloader(file_name, table_name)
    else:
        ingest_csv_batch(file_name, table_name)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Silver Layer — Clean: dedup, type-cast, xử lý null

# COMMAND ----------

def write_silver(df, table_name: str, dedup_keys: list):
    """Dedup theo key, ghi vào silver schema."""
    if dedup_keys:
        df = df.dropDuplicates(dedup_keys)
    target = f"{CATALOG}.{SILVER_SCHEMA}.{table_name}"
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(target)
    print(f"[silver] -> {target} ({df.count()} rows)")
 
 
# ---- orders ----
orders_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.orders_raw")
orders_silver = (
    orders_bronze
    .withColumn("order_purchase_timestamp", F.to_timestamp("order_purchase_timestamp"))
    .withColumn("order_approved_at", F.to_timestamp("order_approved_at"))
    .withColumn("order_delivered_carrier_date", F.to_timestamp("order_delivered_carrier_date"))
    .withColumn("order_delivered_customer_date", F.to_timestamp("order_delivered_customer_date"))
    .withColumn("order_estimated_delivery_date", F.to_timestamp("order_estimated_delivery_date"))
    .withColumn("order_status", F.lower(F.trim(F.col("order_status"))))
    .filter(F.col("order_id").isNotNull())
    .select(
        "order_id", "customer_id", "order_status",
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    )
)
write_silver(orders_silver, "orders", dedup_keys=["order_id"])
 
# ---- order_items ----
order_items_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.order_items_raw")
order_items_silver = (
    order_items_bronze
    .withColumn("price", F.col("price").cast("double"))
    .withColumn("freight_value", F.col("freight_value").cast("double"))
    .withColumn("order_item_id", F.col("order_item_id").cast("int"))
    .withColumn("shipping_limit_date", F.to_timestamp("shipping_limit_date"))
    .filter(F.col("order_id").isNotNull() & F.col("product_id").isNotNull())
    .fillna({"price": 0.0, "freight_value": 0.0})
    .select(
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    )
)
write_silver(order_items_silver, "order_items", dedup_keys=["order_id", "order_item_id"])
 
# ---- order_payments ----
order_payments_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.order_payments_raw")
order_payments_silver = (
    order_payments_bronze
    .withColumn("payment_sequential", F.col("payment_sequential").cast("int"))
    .withColumn("payment_installments", F.col("payment_installments").cast("int"))
    .withColumn("payment_value", F.col("payment_value").cast("double"))
    .withColumn("payment_type", F.lower(F.trim(F.col("payment_type"))))
    .filter(F.col("order_id").isNotNull())
    .fillna({"payment_installments": 1, "payment_value": 0.0})
    .select(
        "order_id", "payment_sequential", "payment_type",
        "payment_installments", "payment_value",
    )
)
write_silver(order_payments_silver, "order_payments", dedup_keys=["order_id", "payment_sequential"])
 
# ---- order_reviews ----
order_reviews_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.order_reviews_raw")
order_reviews_silver = (
    order_reviews_bronze
    .withColumn("review_score", F.col("review_score").cast("int"))
    .withColumn("review_creation_date", F.to_timestamp("review_creation_date"))
    .withColumn("review_answer_timestamp", F.to_timestamp("review_answer_timestamp"))
    .withColumn(
        "review_comment_message",
        F.when(F.col("review_comment_message").isNull(), F.lit(""))
        .otherwise(F.trim(F.col("review_comment_message"))),
    )
    .filter(F.col("order_id").isNotNull() & F.col("review_score").isNotNull())
    .select(
        "review_id", "order_id", "review_score",
        "review_comment_title", "review_comment_message",
        "review_creation_date", "review_answer_timestamp",
    )
)
# Một order có thể có nhiều review do khách gửi lại -> giữ review mới nhất theo order_id
from pyspark.sql.window import Window
w = Window.partitionBy("order_id").orderBy(F.col("review_creation_date").desc())
order_reviews_silver = (
    order_reviews_silver.withColumn("_rn", F.row_number().over(w))
    .filter(F.col("_rn") == 1)
    .drop("_rn")
)
write_silver(order_reviews_silver, "order_reviews", dedup_keys=["review_id"])
 
# ---- customers ----
customers_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.customers_raw")
customers_silver = (
    customers_bronze
    .withColumn("customer_state", F.upper(F.trim(F.col("customer_state"))))
    .withColumn("customer_city", F.lower(F.trim(F.col("customer_city"))))
    .filter(F.col("customer_id").isNotNull())
    .select(
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    )
)
write_silver(customers_silver, "customers", dedup_keys=["customer_id"])
 
# ---- products ----
products_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.products_raw")
category_translation = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.category_translation_raw")
products_silver = (
    products_bronze
    .join(category_translation, on="product_category_name", how="left")
    .withColumn(
        "product_category_name_english",
        F.coalesce(F.col("product_category_name_english"), F.lit("unknown")),
    )
    .withColumn("product_weight_g", F.col("product_weight_g").cast("double"))
    .fillna({"product_category_name_english": "unknown", "product_weight_g": 0.0})
    .filter(F.col("product_id").isNotNull())
    .select(
        "product_id", "product_category_name", "product_category_name_english",
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
    )
)
write_silver(products_silver, "products", dedup_keys=["product_id"])
 
# ---- sellers ----
sellers_bronze = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.sellers_raw")
sellers_silver = (
    sellers_bronze
    .withColumn("seller_state", F.upper(F.trim(F.col("seller_state"))))
    .withColumn("seller_city", F.lower(F.trim(F.col("seller_city"))))
    .filter(F.col("seller_id").isNotNull())
    .select("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state")
)
write_silver(sellers_silver, "sellers", dedup_keys=["seller_id"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Gold Layer
# MAGIC Join orders + items (aggregate theo order) + payments (aggregate) + reviews + customers + sellers thành 1 bảng phẳng, 1 dòng / order_id — tối ưu cho SQL UC Function (SELECT/WHERE đơn giản, không cần agent tool tự viết JOIN phức tạp).

# COMMAND ----------

orders_s = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.orders")
items_s = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.order_items")
payments_s = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.order_payments")
reviews_s = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.order_reviews")
customers_s = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.customers")
sellers_s = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.sellers")
 
# Aggregate items: tổng giá trị, số lượng item, seller chính (seller của item đầu tiên - đơn giản hoá cho demo)
items_agg = items_s.groupBy("order_id").agg(
    F.sum("price").alias("total_item_price"),
    F.sum("freight_value").alias("total_freight_value"),
    F.count("*").alias("num_items"),
    F.first("seller_id").alias("primary_seller_id"),
    F.first("product_id").alias("primary_product_id"),
)
 
# Aggregate payments: tổng giá trị thanh toán, phương thức chính, số kỳ trả góp tối đa
payments_agg = payments_s.groupBy("order_id").agg(
    F.sum("payment_value").alias("total_payment_value"),
    F.max("payment_installments").alias("max_installments"),
    F.first("payment_type").alias("primary_payment_type"),
)
 
order_summary = (
    orders_s.alias("o")
    .join(items_agg.alias("i"), on="order_id", how="left")
    .join(payments_agg.alias("p"), on="order_id", how="left")
    .join(reviews_s.alias("r"), on="order_id", how="left")
    .join(customers_s.alias("c"), on="customer_id", how="left")
    .join(sellers_s.alias("s"), F.col("i.primary_seller_id") == F.col("s.seller_id"), how="left")
    .select(
        F.col("o.order_id"),
        F.col("o.customer_id"),
        F.col("c.customer_state"),
        F.col("c.customer_city"),
        F.col("o.order_status"),
        F.col("o.order_purchase_timestamp"),
        F.col("o.order_delivered_customer_date"),
        F.col("o.order_estimated_delivery_date"),
        # Số ngày trễ so với ước tính: dương = giao trễ, âm/0 = đúng hoặc sớm hạn
        F.datediff(
            F.col("o.order_delivered_customer_date"), F.col("o.order_estimated_delivery_date")
        ).alias("delivery_delay_days"),
        F.col("i.num_items"),
        F.col("i.total_item_price"),
        F.col("i.total_freight_value"),
        F.col("i.primary_seller_id"),
        F.col("s.seller_state").alias("seller_state"),
        F.col("i.primary_product_id"),
        F.col("p.total_payment_value"),
        F.col("p.primary_payment_type"),
        F.col("p.max_installments"),
        F.col("r.review_score"),
        F.col("r.review_comment_message"),
    )
)
 
gold_target = f"{CATALOG}.{GOLD_SCHEMA}.order_summary"
(
    order_summary.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(gold_target)
)
print(f"[gold] -> {gold_target} ({order_summary.count()} rows)")

# COMMAND ----------

display(spark.table(f"{CATALOG}.{GOLD_SCHEMA}.order_summary").limit(10))

# COMMAND ----------


