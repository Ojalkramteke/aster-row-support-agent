from typing import List, Dict, Any, Optional
from src.session import Session


SAFE_FIELDS = {
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


def _abstain(text: str) -> Dict[str, Any]:
    return {"response": f"I don't have enough information to answer that. {text}"}


def _refuse_system_prompt() -> Dict[str, Any]:
    return {"response": "I can't share system prompts or hidden instructions."}


def _refuse_sensitive(field: str) -> Dict[str, Any]:
    return {"response": f"I can't share customers' {field}."}


def generate_order_response(order: Dict[str, Any]) -> Dict[str, Any]:
    # order is already sanitized by the lookup tool; only include safe fields
    if not order:
        return _abstain("")

    status = order.get("status", "unknown").lower()
    parts = [f"Order {order.get('order_id')} is currently {status}."]

    if status in ("cancelled", "returned"):
        parts.append(order.get("customer_safe_message", ""))
        # do not mention carrier, ETA or tracking for cancelled/returned
        return {"response": " ".join([p for p in parts if p])}

    if status == "exception":
        parts.append("This shipment has an exception and requires human support review.")
        parts.append(order.get("customer_safe_message", ""))
        return {"response": " ".join([p for p in parts if p])}

    # shipped but no ETA
    if status == "shipped" and not order.get("estimated_delivery"):
        parts.append("The order has shipped, but an estimated delivery date is not currently available.")
        if order.get("carrier"):
            parts.append(f"Carrier: {order.get('carrier')}.")
        return {"response": " ".join([p for p in parts if p])}

    # general case: include ETA and carrier if present
    if order.get("carrier"):
        parts.append(f"Carrier: {order.get('carrier')}.")
    if order.get("tracking_number"):
        parts.append(f"Tracking: {order.get('tracking_number')}.")
    if order.get("estimated_delivery"):
        parts.append(f"Estimated delivery: {order.get('estimated_delivery')}.")

    if order.get("customer_safe_message"):
        parts.append(order.get("customer_safe_message"))

    return {"response": " ".join([p for p in parts if p])}


def generate_kb_response(passages: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    if not passages:
        return _abstain("")
    # deterministic: list top passage and source
    top = passages[0]
    src = f"According to {top.get('filename')} → {top.get('heading') or 'Overview'}:"
    text = top.get('text')
    resp = f"{src} {text}"
    return {"response": resp, "source": {"filename": top.get('filename'), "heading": top.get('heading'), "score": top.get('score')}}


def enforce_safety_on_order_request(field: Optional[str]) -> Optional[Dict[str, Any]]:
    # refuse sensitive customer fields
    if field and field.lower() in ("email", "name", "shipping_address"):
        return _refuse_sensitive(field)
    return None
