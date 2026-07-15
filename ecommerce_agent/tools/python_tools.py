"""
projects.ecommerce_support.tools.python_tools
-------------------------------------------------
UC Functions (Python) tính toán nhẹ — không network egress, không load model, nên đủ
điều kiện chạy trong sandbox UC Python Function. Định nghĩa ở đây dưới dạng plain
Python function với type hint + docstring rõ ràng để convert thành
`CREATE FUNCTION ... LANGUAGE PYTHON` (qua DatabricksFunctionClient.create_python_function).

STATUS: TODO — chưa register vào Unity Catalog, đang ở bước khởi tạo structure.
"""

from datetime import date


def check_refund_eligibility(order_status: str, delivery_date: date, claim_type: str) -> bool:
    """Kiểm tra đơn hàng có đủ điều kiện hoàn tiền không, dựa trên policy return/shipping.

    Args:
        order_status: trạng thái đơn hàng hiện tại (vd 'delivered', 'shipped').
        delivery_date: ngày giao hàng thực tế.
        claim_type: loại khiếu nại (vd 'wrong_product', 'damaged', 'not_received').

    Returns:
        True nếu đủ điều kiện hoàn tiền theo chính sách tương ứng.
    """
    # TODO: implement theo mốc thời gian trong policy docs (vd 7 ngày vs 10 ngày tùy claim_type)
    raise NotImplementedError


def compute_delay_severity(estimated_delivery_date: date, actual_delivery_date: date | None) -> str:
    """Phân loại mức độ nghiêm trọng của việc giao hàng trễ.

    Returns:
        Một trong 'none', 'minor', 'moderate', 'severe'.
    """
    # TODO: implement dựa trên delivery_delay_days đã có sẵn trong gold.order_summary
    raise NotImplementedError


def customer_value_score(total_orders: int, total_spent: float, avg_review_score: float) -> float:
    """Tính điểm giá trị khách hàng (dùng để ưu tiên xử lý khiếu nại).

    Returns:
        Điểm số 0-100.
    """
    # TODO: implement công thức scoring
    raise NotImplementedError
