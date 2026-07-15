---
name: near_duplicate_policy_disambiguation
description: >
  Dùng khi search_policy_docs trả về 2+ đoạn chính sách trông giống nhau nhưng
  khác điều kiện áp dụng (thường là mốc thời gian). Ví dụ: policy "wrong product
  claim" có 2 phiên bản 7 ngày vs 10 ngày tùy điều kiện khác.
---

# Near-duplicate policy disambiguation

Khi 2 đoạn chính sách trả về gần giống hệt nhau (cùng chủ đề, khác 1-2 điều kiện):

1. KHÔNG chọn đại 1 đoạn theo độ liên quan (rerank score) — score cao không đồng
   nghĩa điều kiện đó áp dụng cho tình huống của khách.
2. Đọc kỹ điều kiện phân biệt 2 đoạn (thường là: mốc thời gian, loại sản phẩm, hay
   khách đã liên hệ seller trước đó chưa).
3. Đối chiếu điều kiện đó với dữ kiện cụ thể của khách — dùng tool SQL
   (`get_order_status`, `get_customer_order_history`) để lấy dữ kiện thật, không
   hỏi lại khách nếu tool đã trả lời được.
4. Nếu vẫn không đủ dữ kiện để phân biệt, hỏi khách CHÍNH XÁC điều kiện còn thiếu
   (ví dụ: "Bạn đã liên hệ người bán trước khi khiếu nại chưa?"), không trả lời
   nước đôi cả 2 policy.
5. Trích dẫn rõ policy nào áp dụng và vì sao (điều kiện nào khớp), không chỉ nói
   "theo chính sách của chúng tôi".
