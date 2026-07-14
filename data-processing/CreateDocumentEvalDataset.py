# Databricks notebook source
# MAGIC %md
# MAGIC # RAG Eval Dataset: Ingest + Test Serving Endpoint
# MAGIC
# MAGIC 1. Nạp 15 test query (kèm target_docs + evaluation_logic) vào `bronze_layer.eval_queries`
# MAGIC    -- bảng này sẽ được tái sử dụng khi build Agent Evaluation (MLflow) sau này.
# MAGIC 2. Gọi `search-and-rerank-endpoint` cho từng query, đo recall (có tìm đúng target
# MAGIC    doc không) + rank vị trí + latency, ghi kết quả vào `bronze_layer.rerank_eval_results`.

# COMMAND ----------

SERVING_ENDPOINT_NAME = 'search-and-rerank-endpoint'

CATALOG = "ecommerce_agent"

BRONZE_SCHEMA = "bronze_layer"
SILVER_SCHEMA = "silver_layer"
GOLD_SCHEMA = "gold_layer"
AGENT_SCHEMA = "agent_layer"


# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Định nghĩa 15 test query -> bảng `bronze_layer.eval_queries`

# COMMAND ----------

EVAL_QUERIES = [
    {
        "query_id": "Q01",
        "query_text": "Hi, I bought a smartphone for R$ 1,200 on June 5, 2018. It recently suffered a severe screen crack after it accidentally slipped out of my hand. Since it's still within the 12-month active coverage period for Electronics, I want to open a claim to get a free repair or replacement. Can you assist me with this?",
        "target_docs": ["07_warranty-policy-by-category.md"],
        "evaluation_logic": "Agent must acknowledge the 12-month coverage but firmly deny the claim because cracked smartphone screens caused by drops are explicitly excluded.",
    },
    {
        "query_id": "Q02",
        "query_text": "I placed an order on November 22, 2017. The merchant is located in SP and my delivery address is in Manaus, Amazonas (which is in the Norte region). The merchant took 70 hours to hand the package to Correios. Did the merchant violate the handling SLA? Also, what is the maximum number of business days my standard shipping should take?",
        "target_docs": ["08_internal-announcement-peak-season-sla.md", "02_shipping-sla-by-region.md"],
        "evaluation_logic": "Agent must calculate that 70h is within the 72h Peak Season SLA. Standard shipping to Norte (14-22 days) + Peak Season extension (8 days) = Max 30 business days.",
    },
    {
        "query_id": "Q03",
        "query_text": "I am a merchant on your platform. I just realized I have a stockout for an order worth R$ 400. I found an alternative product with superior specs, but its market value is R$ 480. Since it's more expensive, can I charge the buyer the extra R$ 80? If I decide to just cancel the order instead, exactly what penalties will hit my account?",
        "target_docs": ["13_seller-stockout-guide.md", "05_seller-code-of-conduct.md"],
        "evaluation_logic": "Agent must state the seller cannot charge the buyer. The R$ 80 difference exceeds the 15% (R$ 60) absorption limit. If cancelled, the penalty is 15% of the order value and a 0.5 point deduction.",
    },
    {
        "query_id": "Q04",
        "query_text": "Hi, 3 days ago I ordered a custom-dimension wooden dining table for my new apartment. Yesterday, the seller changed the status to 'In Production' and uploaded the manufacturing proof. However, today I found a cheaper table at a local mall. Since it hasn't even shipped yet, I want to use my 7-day Right of Regret under the CDC to cancel this order immediately. Please process this.",
        "target_docs": ["01_return-refund-policy.md"],
        "evaluation_logic": "Agent must deny the Right of Regret because custom/tailored items marked as 'In Production' are completely excluded from the 7-day rule.",
    },
    {
        "query_id": "Q05",
        "query_text": "I'm a customer who opened a dispute yesterday because the seller sent me a broken item. The agent asked me for photos. I'm too busy and don't want to provide them. What happens if I just ignore the agent's request for evidence over the next 4 days?",
        "target_docs": ["15_customer-seller-mediation-process.md", "06_guide-damaged-wrong-product-claims.md"],
        "evaluation_logic": "Agent must inform the customer that without digital media evidence within the 4-day window, the ticket will be closed as an 'Unverified Claim' or a decision will be made strictly on available files (favoring the merchant).",
    },
    {
        "query_id": "Q06",
        "query_text": "I bought a TV using a credit card and chose a 12x installment plan. I cancelled the order while it was still 'Awaiting Payment' and it went through. Will I get the full amount refunded at once, or will my bank keep charging me monthly and crediting it back?",
        "target_docs": ["01_return-refund-policy.md"],
        "evaluation_logic": "Agent must clarify that the refund display depends entirely on the card issuer. It may refund at once or credit monthly; the platform has no operational control over this specific banking behavior.",
    },
    {
        "query_id": "Q07",
        "query_text": "I am a seller and my average rating just dropped to 3.6 stars because I had some late shipments. What exactly happens to my account and my active listings now? And what do I need to do to get my account restored?",
        "target_docs": ["05_seller-code-of-conduct.md"],
        "evaluation_logic": "Agent must identify this as Tier 3 (3.5 to 3.7 stars). Account is suspended for 15 days, active listings deactivated, and funds frozen. Seller must submit a Corrective Action Plan (CAP) within 5 business days and undergo an audit (ERP integration + private carrier).",
    },
    {
        "query_id": "Q08",
        "query_text": "My order to Salvador, Bahia (Nordeste region) has been stuck without any tracking updates for 20 consecutive business days. Is it officially classified as 'Lost in Transit' yet? If it is lost, what is the maximum amount the seller can be reimbursed?",
        "target_docs": ["10_lost-in-transit-policy.md"],
        "evaluation_logic": "Agent must note that for Nordeste, stagnation requires 25 consecutive business days, so it is not yet officially lost. If it were, the maximum insurance payout is R$ 10,000.00.",
    },
    {
        "query_id": "Q09",
        "query_text": "Under the LGPD, I want to completely delete all my data from your platform, including the invoice details of a purchase I made 2 years ago. Can your DPO wipe my fiscal invoice data within the 15-day statutory window?",
        "target_docs": ["12_lgpd-data-protection-policy.md"],
        "evaluation_logic": "Agent must state that fiscal/transactional data cannot be deleted within 2 years. Tax law mandates a 5-year retention period, which overrides the LGPD deletion request.",
    },
    {
        "query_id": "Q10",
        "query_text": "My package was shipped yesterday and is currently in transit with Correios. I just realized I bought the wrong model and need to cancel. Can you cancel the delivery right now in the system so it doesn't arrive? If not, what should I do when the delivery guy shows up?",
        "target_docs": ["04_order-cancellation-policy.md"],
        "evaluation_logic": "Agent must state that physical interception is impossible once handed to Correios. The customer must be instructed to perform a 'Refusal of Delivery' (Recusa de Entrega) at the doorstep.",
    },
    {
        "query_id": "Q11",
        "query_text": "The seller marked my order as shipped 5 hours ago and gave me the tracking code PP987654321BR. I've been checking the Correios website but it says 'Object Not Found'. Is this a fake tracking number? Should I open a dispute?",
        "target_docs": ["09_faq-order-tracking.md"],
        "evaluation_logic": "Agent must reassure the user that it takes up to 24 hours for Correios to scan and index new tracking codes. They should not open a dispute yet and wait for 48 business hours.",
    },
    {
        "query_id": "Q12",
        "query_text": "I live in São Paulo (Sudeste) and my cart total is R$ 800. The items are mostly home furniture and the total weight is 35kg. Will I qualify for the promotional free shipping since I'm well over the R$ 250 threshold and live in a qualifying region?",
        "target_docs": ["14_faq-shipping-fees-free-threshold.md"],
        "evaluation_logic": "Agent must deny free shipping. Even though the price and region qualify, the package exceeds the strict 15kg weight limit for promotions and will require custom private freight.",
    },
    {
        "query_id": "Q13",
        "query_text": "I paid for my order using a Boleto Bancário, but I returned the item 2 days ago. The item was inspected and approved today. My friend has a Nubank account, can you just transfer the refund to his account since I don't have a checking account?",
        "target_docs": ["01_return-refund-policy.md"],
        "evaluation_logic": "Agent must firmly reject this request. Third-party bank transfers are explicitly prohibited. The checking account must match the exact name and CPF of the purchaser.",
    },
    {
        "query_id": "Q14",
        "query_text": "I received my order 10 days ago, but I just opened the box today and realized the seller sent me a size M shirt instead of size L. Can you send me the 9-digit Correios authorization code to return it?",
        "target_docs": ["06_guide-damaged-wrong-product-claims.md"],
        "evaluation_logic": "Agent must deny the automated reverse logistics. The rule strictly mandates claims for wrong items be filed within 7 calendar days. At 10 days, the standard automated return path is closed.",
    },
    {
        "query_id": "Q15",
        "query_text": "As a merchant, the mediation team just ruled against me in a dispute regarding a defective blender. What exactly happens to the funds for this transaction, and are there any extra fees deducted from my Conta Olist?",
        "target_docs": ["15_customer-seller-mediation-process.md"],
        "evaluation_logic": "Agent must explain that a 'Forced Financial Refund' is executed. The total transaction value is clawed back via a debit to the Conta Olist, PLUS an additional flat dispute mediation fee of R$ 75.00.",
    },
]

print(f"Tổng số query: {len(EVAL_QUERIES)}")

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, ArrayType

EVAL_QUERIES_SCHEMA = StructType(
    [
        StructField("query_id", StringType(), False),
        StructField("query_text", StringType(), False),
        StructField("target_docs", ArrayType(StringType()), False),
        StructField("evaluation_logic", StringType(), False),
    ]
)

eval_queries_df = spark.createDataFrame(EVAL_QUERIES, schema=EVAL_QUERIES_SCHEMA)

target_table = f"{CATALOG}.{BRONZE_SCHEMA}.eval_queries"
(
    eval_queries_df.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(target_table)
)
print(f"[bronze] -> {target_table} ({eval_queries_df.count()} rows)")
display(spark.table(target_table))

# COMMAND ----------

# MAGIC %sql
# MAGIC UPDATE ecommerce_agent.bronze_layer.eval_queries
# MAGIC SET target_docs = transform(target_docs, x -> concat('rag_docs_', x));

# COMMAND ----------


