---
name: delayed_delivery_escalation
description: >
  Dùng khi khách hàng khiếu nại về giao hàng trễ hoặc chưa nhận được đơn hàng.
  Hướng dẫn thứ tự tool cần gọi và cách phân loại mức độ nghiêm trọng trước khi
  đề xuất hướng xử lý.
---

# Delayed delivery escalation

Thứ tự xử lý khi khách báo giao hàng trễ:

1. `get_order_status(order_id)` — lấy trạng thái hiện tại + `delivery_delay_days`.
2. Nếu `delivery_delay_days` <= 0: đơn chưa thực sự trễ so với ước tính, giải thích
   ngày giao dự kiến, KHÔNG xử lý như khiếu nại trễ.
3. Nếu trễ thật: gọi `compute_delay_severity` để phân loại mức độ (none/minor/
   moderate/severe).
4. Mức độ `severe`: ưu tiên đề xuất `check_refund_eligibility` ngay trong câu trả
   lời đầu tiên, không bắt khách hỏi lại.
5. Mức độ `minor`/`moderate`: giải thích tình trạng, đưa mốc thời gian còn lại theo
   policy shipping trước khi đề cập hoàn tiền.
6. Luôn kiểm tra `get_seller_performance(seller_id)` nếu seller có tỷ lệ trễ cao —
   dùng thông tin này để quyết định có nên chủ động đề xuất đổi seller lần mua sau
   hay không (không nói thẳng "seller này thường xuyên trễ" với khách).
