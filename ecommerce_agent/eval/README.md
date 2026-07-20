# Eval

Bộ 15 eval query đã có sẵn trong bảng `ecommerce_agent.bronze_layer.eval_queries` (không
duplicate ra file JSONL ở đây để tránh lệch nguồn). Cột `evaluation_logic` sẽ được
dùng cho MLflow Agent Evaluation (chấm câu trả lời cuối cùng của agent) — xem mục 5
(Next steps) trong handoff doc: bước "Run MLflow Agent Evaluation".

`eval_queries_ingest_and_test.py` (ở project root, không nằm trong src/) vẫn giữ
nguyên vai trò test riêng cho retrieval recall/rank/latency của `search-and-rerank-endpoint`.
