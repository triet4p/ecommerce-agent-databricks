"""
projects.ecommerce_support.tools.sql_tools
---------------------------------------------
UC Functions (SQL) trên `gold.order_summary`. Đây là DDL, không phải Python tool —
chạy trực tiếp trên Databricks SQL Warehouse / notebook %sql cell, KHÔNG import vào agent.py.
Sau khi CREATE FUNCTION, agent chỉ cần liệt kê full_name trong config.yaml.

STATUS: TODO — chưa chạy, đang ở bước khởi tạo structure.
"""

CATALOG_SCHEMA = "ecommerce_demo.agent"

DDL_GET_ORDER_STATUS = f"""
CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_order_status(order_id STRING)
RETURNS TABLE (status STRING, delivery_delay_days INT, estimated_delivery_date DATE)
COMMENT 'Trả về trạng thái và độ trễ giao hàng của 1 đơn hàng theo order_id'
RETURN
  SELECT order_status AS status, delivery_delay_days, order_estimated_delivery_date
  FROM ecommerce_demo.gold.order_summary
  WHERE order_id = get_order_status.order_id;
"""

DDL_GET_CUSTOMER_ORDER_HISTORY = f"""
CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_customer_order_history(customer_id STRING, limit_n INT DEFAULT 10)
RETURNS TABLE (order_id STRING, order_status STRING, order_purchase_timestamp TIMESTAMP)
COMMENT 'Trả về lịch sử N đơn hàng gần nhất của 1 khách hàng'
RETURN
  SELECT order_id, order_status, order_purchase_timestamp
  FROM ecommerce_demo.gold.order_summary
  WHERE customer_id = get_customer_order_history.customer_id
  ORDER BY order_purchase_timestamp DESC
  LIMIT get_customer_order_history.limit_n;
"""

# TODO: cần build gold.seller_performance trước khi viết 2 function dưới đây
DDL_GET_SELLER_PERFORMANCE = f"""
-- CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_seller_performance(seller_id STRING)
-- RETURNS TABLE (avg_rating DOUBLE, late_delivery_rate DOUBLE, total_orders INT)
-- COMMENT 'Trả về chỉ số hiệu suất của 1 seller'
-- RETURN
--   SELECT avg_rating, late_delivery_rate, total_orders
--   FROM ecommerce_demo.gold.seller_performance
--   WHERE seller_id = get_seller_performance.seller_id;
"""

DDL_GET_SHIPPING_DELAY_STATS = f"""
-- CREATE OR REPLACE FUNCTION {CATALOG_SCHEMA}.get_shipping_delay_stats(seller_id STRING)
-- RETURNS TABLE (avg_delay_days DOUBLE, max_delay_days INT)
-- COMMENT 'Thống kê độ trễ giao hàng của 1 seller'
-- RETURN ...
"""

ALL_DDL = [
    DDL_GET_ORDER_STATUS,
    DDL_GET_CUSTOMER_ORDER_HISTORY,
    DDL_GET_SELLER_PERFORMANCE,
    DDL_GET_SHIPPING_DELAY_STATS,
]
