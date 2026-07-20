---
name: delayed_delivery_escalation
description: >
  Dùng khi khách hàng khiếu nại về giao hàng trễ hoặc chưa nhận được đơn hàng.
  Hướng dẫn thứ tự tool cần gọi và cách phân loại mức độ nghiêm trọng trước khi
  đề xuất hướng xử lý.
---

# Delayed delivery escalation

Thứ tự xử lý khi khách báo giao hàng trễ:

1. `compute_delay_severity(estimated_delivery_date, actual_delivery_date)` — phân
   loại mức độ trễ dựa trên ngày giao dự kiến và thực tế (none/minor/moderate/severe).
2. Nếu `severe`: ưu tiên đề xuất `search_policy_docs` để tra cứu policy hoàn tiền
   ngay trong câu trả lời đầu tiên, không bắt khách hỏi lại.
3. Nếu `minor`/`moderate`: giải thích tình trạng, đưa mốc thời gian còn lại dựa
   trên kết quả của `compute_delay_severity`.
4. Luôn tra cứu `search_policy_docs` với từ khóa liên quan đến shipping/refund policy
   để cung cấp thông tin chính xác cho khách.
5. Khi managed MCP được bật (xem mcp_servers trong config.yaml):
   a. `get_order_status(order_id)` — lấy trạng thái hiện tại + `delivery_delay_days`.
   b. `get_seller_performance(seller_id)` — kiểm tra tỷ lệ trễ của seller.
   c. `check_refund_eligibility(...)` — chỉ gọi sau khi đã có đủ claim type,
      claim/evaluation date, trạng thái đơn, các ngày giao liên quan và các cờ
      evidence/opened/final-sale theo policy `SYNTH-REFUND-2026-01`. Nếu kết quả
      là `manual_review`, không được diễn giải thành từ chối hoàn tiền.
   d. Nếu seller có tỷ lệ trễ cao, dùng thông tin này để quyết định có nên chủ động
      đề xuất đổi seller lần mua sau hay không (không nói thẳng "seller này thường
      xuyên trễ" với khách).
