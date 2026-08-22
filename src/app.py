import re
from typing import Optional, Dict, Any, List

from src.session import Session
from src.prompting import (
    generate_order_response,
    generate_kb_response,
    enforce_safety_on_order_request,
)
from src.tools.order_lookup import lookup_order
from src.retrieval.retriever import Retriever


class SupportAgent:
    def __init__(self):
        self.retriever = Retriever()

    def handle_message(self, session: Session, message: str) -> Dict[str, Any]:
        session.add_user_message(message)

        # detect explicit request to reveal system prompt
        if re.search(r"system prompt|system instructions|developer instructions", message, flags=re.I):
            resp = {"response": "I can't share system prompts or hidden instructions."}
            session.add_assistant_message(resp["response"])
            return resp

        # detect if user asks to reveal a sensitive customer field
        m_sensitive = re.search(r"customer(?:'s)?\s+(email|name|shipping_address)", message, flags=re.I)
        if m_sensitive:
            res = enforce_safety_on_order_request(m_sensitive.group(1))
            session.add_assistant_message(res["response"])
            return res

        # determine if order-related
        order_id = None
        m = re.search(r"ord[-\s]?(\d{3,})", message, flags=re.I)
        if m:
            order_id = f"ORD-{m.group(1)}"
            session.set_order_context(order_id)

        # if message mentions 'order' but no id, and we have context, use contextual id
        if not order_id and re.search(r"\border\b", message, flags=re.I):
            order_id = session.get_order_context()

        # follow-up detection: if the user asks about delivery/status/tracking without mentioning 'order'
        if not order_id and session.get_order_context() and re.search(r"\b(arrive|arrival|delivery|when|status|track|tracking|where)\b", message, flags=re.I):
            order_id = session.get_order_context()

        order_result = None
        # detect unsupported actions (no API available)
        if re.search(r"\bcancel|refund|replace|change address|address change|escalate\b", message, flags=re.I):
            resp = {"response": "I can't perform that action. I can only look up order status. Please contact support for cancellations or refunds."}
            session.add_assistant_message(resp["response"])
            return resp

        if order_id:
            # call existing lookup tool; only pass sanitized result
            lookup = lookup_order(order_id)
            if lookup.get("found"):
                order_result = lookup.get("order")
            else:
                # not found, respond accordingly
                resp_text = lookup.get("message", "I couldn't find that order.")
                session.add_assistant_message(resp_text)
                return {"response": resp_text}

        # determine if knowledge-base retrieval needed
        kb_needed = bool(re.search(r"return|refund|policy|membership|TrailPlus|shipping|warranty", message, flags=re.I))

        passages = []
        if kb_needed:
            # if follow-up to KB, combine with last KB query for context
            query = message
            if session.last_kb_query and not re.search(r"return|refund|policy|membership|TrailPlus", message, flags=re.I):
                query = session.last_kb_query + " " + message
            results = self.retriever.search(query, top_k=3)
            passages = results
            session.last_kb_query = query

        # If order was requested but we have no id, ask for it
        if re.search(r"\border\b", message, flags=re.I) and not order_result:
            resp = {"response": "Which order ID should I look up? Please provide an ORD- number."}
            session.add_assistant_message(resp["response"])
            return resp

        # Generate deterministic response based on what we obtained
        if order_result and kb_needed:
            # prefer order info first, then KB
            order_resp = generate_order_response(order_result)
            kb_resp = generate_kb_response(passages, message) if passages else None
            combined = order_resp["response"]
            if kb_resp:
                combined = combined + "\n\n" + kb_resp["response"]
            session.add_assistant_message(combined)
            return {"response": combined, "order": order_result, "retrieved": passages}

        if order_result:
            resp = generate_order_response(order_result)
            session.add_assistant_message(resp["response"])
            return {"response": resp["response"], "order": order_result}

        if kb_needed:
            resp = generate_kb_response(passages, message)
            session.add_assistant_message(resp["response"])
            return {"response": resp.get("response"), "retrieved": passages}

        # default: abstain
        resp = {"response": "I don't have enough information to answer that."}
        session.add_assistant_message(resp["response"])
        return resp


def create_session() -> Session:
    return Session()
