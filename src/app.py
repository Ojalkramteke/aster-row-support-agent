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

        # conversational greetings / polite inquiries
        stripped = (message or "").strip().lower()
        if re.match(r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b[!\.\?]*$", stripped):
            resp = {
                "response": "Hello! How can I help you with Aster & Row orders, shipping, or store policies today?",
                "handoff": False
            }
            session.add_assistant_message(resp["response"])
            return resp

        if re.match(r"^(how\s+are\s+you(\s+doing)?|how's\s+it\s+going|how\s+are\s+things)\b[!\.\?]*$", stripped):
            resp = {
                "response": "I'm doing well, thank you! How can I assist you with Aster & Row customer support today?",
                "handoff": False
            }
            session.add_assistant_message(resp["response"])
            return resp

        if re.match(r"^(thank\s+you|thanks|thank\s+you\s+so\s+much)\b[!\.\?]*$", stripped):
            resp = {
                "response": "You're very welcome! Let me know if there is anything else I can help you with.",
                "handoff": False
            }
            session.add_assistant_message(resp["response"])
            return resp

        if re.match(r"^(exit|quit|end|bye|goodbye)\b[!\.\?]*$", stripped):
            resp = {
                "response": "Thanks for chatting with Aster & Row Support! Goodbye.",
                "handoff": False
            }
            session.add_assistant_message(resp["response"])
            session.set_order_context(None)
            session.last_kb_query = None
            return resp

        # determine if order-related
        order_id = None

        # 1. Explicit ORD format: ORD-1007, ORD 1007, ORD1007, ORD_1007
        m_ord = re.search(r"\bord[-\s_]?(\d{3,})\b", message, flags=re.I)
        if m_ord:
            order_id = f"ORD-{m_ord.group(1)}"
            session.set_order_context(order_id)

        # 2. 'order' or 'order number' / 'order #' / 'order id': order 1006, order number 1006, order #1006, order no. 1006
        if not order_id:
            m_order_num = re.search(r"\border(?:\s*(?:number|no\.?|id|#))?[\s\-_#:]*(\d{3,})\b", message, flags=re.I)
            if m_order_num:
                order_id = f"ORD-{m_order_num.group(1)}"
                session.set_order_context(order_id)

        # 3. Direct status / track / lookup / where is of a number: status of 1006, track 1006, where is 1006, check 1006
        if not order_id:
            m_status_num = re.search(r"\b(?:status\s+of|track|tracking|lookup|where\s+is|where's|check|for|about)\s+#?(\d{4,})\b", message, flags=re.I)
            if m_status_num:
                order_id = f"ORD-{m_status_num.group(1)}"
                session.set_order_context(order_id)

        # 4. Standalone number or hashtag: "1006", "#1006"
        if not order_id:
            m_standalone = re.search(r"^\s*#?(\d{3,})\s*[!\.\?]?$", message)
            if m_standalone:
                order_id = f"ORD-{m_standalone.group(1)}"
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
            resp = {
                "response": "I can't perform that action. I can only look up order status. Please contact support for cancellations or order changes."
            }
            session.add_assistant_message(resp["response"])
            return resp

        if order_id:
            # call existing lookup tool; only pass sanitized result
            lookup = lookup_order(order_id)

            if lookup.get("found"):
                order_result = lookup.get("order")
            else:
                # not found, respond accordingly
                resp_text = lookup.get("message", "The order was not found. Please check the order ID or contact support.")
                if "contact support" not in resp_text.lower():
                    resp_text = resp_text + " Please contact support for help."
                session.add_assistant_message(resp_text)
                return {"response": resp_text, "handoff": True}

        # determine if knowledge-base retrieval needed
        from src.prompting import detect_topic
        topic = detect_topic(message)
        kb_needed = topic is not None

        passages = []
        if kb_needed:
            # if follow-up to KB, combine with last KB query for context
            query = message
            # combine with prior KB query for short follow-ups like "What about Canada?"
            is_follow_up = False
            if session.last_kb_query:
                low = message.strip().lower()
                if not detect_topic(message):
                    is_follow_up = True
                if low.startswith("what about") or low.startswith("what about the") or len(low.split()) <= 4:
                    is_follow_up = True
            if is_follow_up and session.last_kb_query:
                query = session.last_kb_query + " " + message
            results = self.retriever.search(query, top_k=5)
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
            order_resp = generate_order_response(order_result, message)
            kb_resp = generate_kb_response(passages, message) if passages else None
            combined = order_resp.get("response", "")
            if kb_resp:
                combined = combined + "\n\n" + kb_resp.get("response", "")
                # include handoff suggestion if KB recommends it
                if kb_resp.get("handoff"):
                    combined = combined + " Please contact support for help with this."
            session.add_assistant_message(combined)
            out = {"response": combined, "order": order_result, "retrieved": passages}
            # include structured tool_called
            out["tool_called"] = True
            return out

        if order_result:
            resp = generate_order_response(order_result, message)
            session.add_assistant_message(resp["response"])
            out = {"response": resp["response"], "order": order_result}
            out["tool_called"] = True
            if resp.get("handoff"):
                out["handoff"] = True
            return out

        if kb_needed:
            resp = generate_kb_response(passages, message)
            reply = resp.get("response", "")
            if resp.get("handoff") and "contact support" not in reply.lower():
                reply = reply + " Please contact support for help with this."
            session.add_assistant_message(reply)
            out = {"response": reply, "retrieved": passages}
            if resp.get("handoff"):
                out["handoff"] = True
            return out

        # default: abstain
        resp = {
            "response": "I don't have enough information to answer that. The supplied information is insufficient, and human confirmation is required. Please contact support for help.",
            "handoff": True
        }
        session.add_assistant_message(resp["response"])
        return resp


def create_session() -> Session:
    return Session()


def interactive_chat():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    agent = SupportAgent()
    session = create_session()

    print("==================================================")
    print(" Aster & Row Support Agent - Interactive Chat")
    print(" (Type 'exit' or 'quit' to end the conversation)")
    print("==================================================\n")

    while True:
        try:
            user_input = input("User: ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! Have a great day.")
            break

        cleaned = user_input.strip()
        if not cleaned:
            continue

        if cleaned.lower() in ("exit", "quit"):
            print("\nGoodbye! Have a great day.")
            break

        result = agent.handle_message(session, cleaned)
        response_text = result.get("response", "")
        print(f"Bot:  {response_text}\n")


if __name__ == "__main__":
    interactive_chat()
