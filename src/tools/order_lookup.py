import json
import os
import re
from typing import Any, Dict, Optional


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DEFAULT_ORDERS_PATH = os.path.join(ROOT, "data", "orders.json")


def _normalize_order_id(raw_id: Optional[str]) -> Optional[str]:
    if raw_id is None:
        return None
    s = raw_id.strip()
    # remove surrounding punctuation like .,;:!?
    s = re.sub(r"^[\W_]+|[\W_]+$", "", s)
    s = s.upper()
    # accept forms like ORD1007, ORD-1007, ord-1007, ORDER 1007, ORDER #1007, 1007
    m = re.match(r"^(?:ORD(?:ER)?[\s\-_#]*)?(\d{3,})$", s)
    if not m:
        return None
    digits = m.group(1)
    return f"ORD-{digits}"


def _load_orders(orders_path: str) -> Dict[str, Any]:
    with open(orders_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    orders = data.get("orders", [])
    return {o.get("order_id"): o for o in orders}


def _sanitize_order_for_customer(order: Dict[str, Any]) -> Dict[str, Any]:
    # Only include fields allowed by data/orders-data-dictionary.md
    allowed = {
        "order_id": order.get("order_id"),
        "membership_tier": order.get("membership_tier"),
        "items": [
            {
                "name": it.get("name"),
                "quantity": it.get("quantity"),
                "final_sale": it.get("final_sale"),
            }
            for it in order.get("items", [])
        ],
        "placed_at": order.get("placed_at"),
        "status": order.get("status"),
        "status_updated_at": order.get("status_updated_at"),
        "shipped_at": order.get("shipped_at"),
        "delivered_at": order.get("delivered_at"),
        "carrier": order.get("carrier"),
        "tracking_number": order.get("tracking_number"),
        "estimated_delivery": order.get("estimated_delivery"),
        "customer_safe_message": order.get("customer_safe_message"),
    }

    # status precedence: cancelled/returned -> do not expose carrier/tracking/eta
    if allowed.get("status") in ("cancelled", "returned"):
        allowed["carrier"] = None
        allowed["tracking_number"] = None
        allowed["estimated_delivery"] = None

    return allowed


def lookup_order(raw_order_id: Optional[str], orders_path: Optional[str] = None) -> Dict[str, Any]:
    """Lookup an order by ID and return a sanitized customer-safe result.

    Returns a dict with the shape:
      - found: bool
      - order: { ... } (only when found)
      - error: str (only when not found)
      - message: str (human-friendly)
    """
    if orders_path is None:
        orders_path = DEFAULT_ORDERS_PATH

    if raw_order_id is None or (isinstance(raw_order_id, str) and raw_order_id.strip() == ""):
        return {
            "found": False,
            "error": "missing_order_id",
            "message": "Order ID is required. Please provide an order ID like 'ORD-1007'.",
        }

    norm = _normalize_order_id(raw_order_id)
    if norm is None:
        return {
            "found": False,
            "error": "malformed_order_id",
            "message": "The provided order ID appears malformed. Expected form like 'ORD-1007'.",
        }

    orders = _load_orders(orders_path)
    order = orders.get(norm)
    if order is None:
        return {
            "found": False,
            "error": "not_found",
            "message": f"The order was not found for {norm}. Please check the order ID or contact support for assistance.",
        }

    sanitized = _sanitize_order_for_customer(order)

    return {"found": True, "order": sanitized}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python order_lookup.py ORD-1007")
        raise SystemExit(2)
    res = lookup_order(sys.argv[1])
    print(json.dumps(res, indent=2))
