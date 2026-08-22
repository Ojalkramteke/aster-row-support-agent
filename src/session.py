import re
from typing import List, Optional


class Session:
    """In-memory session store for a single conversation."""

    def __init__(self):
        self.history = []  # list of {'role': 'user'|'assistant', 'text': str}
        self._last_order_id = None
        self.last_intent = None
        self.last_kb_query = None

    def add_user_message(self, text: str):
        self.history.append({"role": "user", "text": text})
        # detect an explicit order id like ORD-1007
        m = re.search(r"ord[-\s]?(\d{3,})", text, flags=re.I)
        if m:
            oid = f"ORD-{m.group(1)}"
            self._last_order_id = oid

    def add_assistant_message(self, text: str):
        self.history.append({"role": "assistant", "text": text})

    def set_order_context(self, order_id: str):
        self._last_order_id = order_id

    def get_order_context(self) -> Optional[str]:
        return self._last_order_id

    def get_conversation(self) -> List[dict]:
        return list(self.history)

    def clear(self):
        self.history = []
        self._last_order_id = None
        self.last_intent = None
        self.last_kb_query = None
