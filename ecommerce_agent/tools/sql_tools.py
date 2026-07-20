"""
ecommerce_agent.tools.sql_tools
---------------------------------
Unity Catalog SQL function DDL for the ``ecommerce_agent.agent_layer`` schema.
These are executed on a Databricks SQL Warehouse or in a notebook
``%sql`` cell — they are NOT imported into Python agent code.

After ``CREATE FUNCTION``, the agent discovers these through managed MCP
or an explicit UCFunctionToolkit adapter.
"""

# Canonical UC namespace. The data pipeline owns table creation; these
# functions only read its published gold-layer contract.
CATALOG = "ecommerce_agent"
FUNCTION_SCHEMA = "agent_layer"
GOLD_SCHEMA = "gold_layer"

CATALOG_SCHEMA = f"{CATALOG}.{FUNCTION_SCHEMA}"

DDL_GET_ORDER_STATUS = f"""
CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_order_status(order_id STRING)
RETURNS TABLE (status STRING, delivery_delay_days INT, estimated_delivery_date DATE)
COMMENT 'Return status and delivery delay for a single order'
RETURN
  SELECT order_status AS status, delivery_delay_days, order_estimated_delivery_date
  FROM {CATALOG}.{GOLD_SCHEMA}.order_summary
  WHERE order_id = get_order_status.order_id;
"""

DDL_GET_CUSTOMER_ORDER_HISTORY = f"""
CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_customer_order_history(customer_id STRING, limit_n INT DEFAULT 10)
RETURNS TABLE (order_id STRING, order_status STRING, order_purchase_timestamp TIMESTAMP)
COMMENT 'Return the N most recent orders for a customer'
RETURN
  SELECT order_id, order_status, order_purchase_timestamp
  FROM (
    SELECT
      order_id,
      order_status,
      order_purchase_timestamp,
      ROW_NUMBER() OVER (ORDER BY order_purchase_timestamp DESC) AS row_num
    FROM {CATALOG}.{GOLD_SCHEMA}.order_summary
    WHERE customer_id = get_customer_order_history.customer_id
  )
  WHERE row_num <= get_customer_order_history.limit_n;
"""

DDL_GET_SELLER_PERFORMANCE = f"""
CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_seller_performance(seller_id STRING)
RETURNS TABLE (avg_rating DOUBLE, late_delivery_rate DOUBLE, total_orders INT)
COMMENT 'Return performance metrics for a seller'
RETURN
  SELECT avg_rating, late_delivery_rate, total_orders
  FROM (
    SELECT
      AVG(CAST(review_score AS DOUBLE)) AS avg_rating,
      AVG(CASE WHEN delivery_delay_days > 0 THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
      COUNT(*) AS total_orders
    FROM {CATALOG}.{GOLD_SCHEMA}.order_summary
    WHERE primary_seller_id = get_seller_performance.seller_id
  );
"""

DDL_GET_SHIPPING_DELAY_STATS = f"""
CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_shipping_delay_stats(seller_id STRING)
RETURNS TABLE (avg_delay_days DOUBLE, max_delay_days INT, total_orders INT)
COMMENT 'Return shipping delay statistics for a seller'
RETURN
  SELECT AVG(delivery_delay_days) AS avg_delay_days,
         MAX(delivery_delay_days) AS max_delay_days,
         COUNT(*) AS total_orders
  FROM {CATALOG}.{GOLD_SCHEMA}.order_summary
  WHERE primary_seller_id = get_shipping_delay_stats.seller_id
    AND delivery_delay_days IS NOT NULL;
"""

ALL_DDL = [
    DDL_GET_ORDER_STATUS,
    DDL_GET_CUSTOMER_ORDER_HISTORY,
    DDL_GET_SELLER_PERFORMANCE,
    DDL_GET_SHIPPING_DELAY_STATS,
]
