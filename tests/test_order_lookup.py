import os
import json
from src.tools.order_lookup import lookup_order


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ORDERS_PATH = os.path.join(DATA_DIR, "orders.json")


def test_valid_order_lookup_ord_1007():
    res = lookup_order("ORD-1007", orders_path=ORDERS_PATH)
    assert res["found"] is True
    order = res["order"]
    assert order["status"] == "shipped"
    assert order["carrier"] == "UPS"
    assert order["estimated_delivery"] == "2026-08-22"
    # internal/customer fields must not be present
    assert "internal" not in order
    assert "customer" not in order


def test_missing_order_id():
    res = lookup_order(None, orders_path=ORDERS_PATH)
    assert res["found"] is False
    assert res["error"] == "missing_order_id"


def test_malformed_order_id():
    res = lookup_order("INVALID123", orders_path=ORDERS_PATH)
    assert res["found"] is False
    assert res["error"] == "malformed_order_id"


def test_unknown_order():
    res = lookup_order("ORD-9999", orders_path=ORDERS_PATH)
    assert res["found"] is False
    assert res["error"] == "not_found"


def test_cancelled_order_stale_eta():
    res = lookup_order("ORD-1004", orders_path=ORDERS_PATH)
    assert res["found"] is True
    order = res["order"]
    assert order["status"] == "cancelled"
    # Should not expose stale carrier/eta for cancelled orders
    assert order["carrier"] is None
    assert order["estimated_delivery"] is None


def test_shipped_without_eta():
    res = lookup_order("ORD-1011", orders_path=ORDERS_PATH)
    assert res["found"] is True
    order = res["order"]
    assert order["status"] == "shipped"
    assert order["carrier"] == "Canada Post"
    assert order["estimated_delivery"] is None


def test_privacy_no_internal_fields():
    res = lookup_order("ORD-1007", orders_path=ORDERS_PATH)
    order = res["order"]
    # Ensure nothing sensitive leaked at top-level
    forbidden = ["customer", "internal", "risk_score", "warehouse_note", "support_tags", "email"]
    for f in forbidden:
        assert f not in order


def test_order_id_normalization_variants():
    variants = ["ord-1007", "  ORD-1007  ", "ORD1007"]
    results = []
    for v in variants:
        res = lookup_order(v, orders_path=ORDERS_PATH)
        assert res["found"] is True
        results.append(res["order"]["order_id"])
    # All should resolve to the same canonical order id
    assert len(set(results)) == 1 and results[0] == "ORD-1007"


def test_returned_order_behavior():
    # Find a real returned order in the dataset
    with open(ORDERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    returned = None
    for o in data.get("orders", []):
        if o.get("status") == "returned":
            returned = o
            break
    assert returned is not None, "No returned order found in dataset"
    oid = returned.get("order_id")
    res = lookup_order(oid, orders_path=ORDERS_PATH)
    assert res["found"] is True
    order = res["order"]
    assert order["status"] == "returned"
    # Stale carrier/tracking/eta must not be exposed
    assert order.get("carrier") is None
    assert order.get("tracking_number") is None
    assert order.get("estimated_delivery") is None


def test_privacy_recursive_and_allowed_fields_only():
    # Use ORD-1007 as sample
    res = lookup_order("ORD-1007", orders_path=ORDERS_PATH)
    assert res["found"]
    order = res["order"]
    # Allowed keys per data dictionary
    allowed_keys = {
        "order_id",
        "membership_tier",
        "items",
        "placed_at",
        "status",
        "status_updated_at",
        "shipped_at",
        "delivered_at",
        "carrier",
        "tracking_number",
        "estimated_delivery",
        "customer_safe_message",
    }
    assert set(order.keys()).issubset(allowed_keys)

    # Collect sensitive values from the original order and ensure none appear
    with open(ORDERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # find same order in source
    src = None
    for o in data.get("orders", []):
        if o.get("order_id") == order.get("order_id"):
            src = o
            break
    assert src is not None
    sensitive_values = []
    cust = src.get("customer", {})
    sensitive_values.extend([cust.get("name", ""), cust.get("email", ""), cust.get("shipping_address", "")])
    internal = src.get("internal", {})
    sensitive_values.extend([str(internal.get("risk_score", "")), internal.get("warehouse_note", ""), str(internal.get("support_tags", ""))])

    repr_text = json.dumps(order)
    for sv in sensitive_values:
        if sv:
            assert sv not in repr_text


def test_shipped_order_without_eta_not_invented():
    # ORD-1011 in dataset is shipped with estimated_delivery = null
    res = lookup_order("ORD-1011", orders_path=ORDERS_PATH)
    assert res["found"] is True
    order = res["order"]
    assert order["status"] == "shipped"
    assert order["estimated_delivery"] is None


    def test_order_id_normalization_variants():
        variants = ["ord-1007", "  ORD-1007  ", "ORD1007"]
        results = []
        for v in variants:
            res = lookup_order(v, orders_path=ORDERS_PATH)
            assert res["found"] is True
            results.append(res["order"]["order_id"])
        # All should resolve to the same canonical order id
        assert len(set(results)) == 1 and results[0] == "ORD-1007"


    def test_returned_order_behavior():
        # Find a real returned order in the dataset
        with open(ORDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        returned = None
        for o in data.get("orders", []):
            if o.get("status") == "returned":
                returned = o
                break
        assert returned is not None, "No returned order found in dataset"
        oid = returned.get("order_id")
        res = lookup_order(oid, orders_path=ORDERS_PATH)
        assert res["found"] is True
        order = res["order"]
        assert order["status"] == "returned"
        # Stale carrier/tracking/eta must not be exposed
        assert order.get("carrier") is None
        assert order.get("tracking_number") is None
        assert order.get("estimated_delivery") is None


    def test_privacy_recursive_and_allowed_fields_only():
        # Use ORD-1007 as sample
        res = lookup_order("ORD-1007", orders_path=ORDERS_PATH)
        assert res["found"]
        order = res["order"]
        # Allowed keys per data dictionary
        allowed_keys = {
            "order_id",
            "membership_tier",
            "items",
            "placed_at",
            "status",
            "status_updated_at",
            "shipped_at",
            "delivered_at",
            "carrier",
            "tracking_number",
            "estimated_delivery",
            "customer_safe_message",
        }
        assert set(order.keys()).issubset(allowed_keys)

        # Collect sensitive values from the original order and ensure none appear
        with open(ORDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # find same order in source
        src = None
        for o in data.get("orders", []):
            if o.get("order_id") == order.get("order_id"):
                src = o
                break
        assert src is not None
        sensitive_values = []
        cust = src.get("customer", {})
        sensitive_values.extend([cust.get("name", ""), cust.get("email", ""), cust.get("shipping_address", "")])
        internal = src.get("internal", {})
        sensitive_values.extend([str(internal.get("risk_score", "")), internal.get("warehouse_note", ""), str(internal.get("support_tags", ""))])

        repr_text = json.dumps(order)
        for sv in sensitive_values:
            if sv:
                assert sv not in repr_text


    def test_shipped_order_without_eta_not_invented():
        # ORD-1011 in dataset is shipped with estimated_delivery = null
        res = lookup_order("ORD-1011", orders_path=ORDERS_PATH)
        assert res["found"] is True
        order = res["order"]
        assert order["status"] == "shipped"
        assert order["estimated_delivery"] is None
