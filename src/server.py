import http.server
import json
import os
import sys
import threading
from typing import Dict
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.app import SupportAgent, create_session
from src.session import Session

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")

# Global singleton agent and session registry
_AGENT = SupportAgent()
_SESSIONS: Dict[str, Session] = {}
_SESSIONS_LOCK = threading.Lock()


def get_or_create_session(session_id: str) -> Session:
    with _SESSIONS_LOCK:
        if not session_id:
            session_id = "default"
        if session_id not in _SESSIONS:
            _SESSIONS[session_id] = create_session()
        return _SESSIONS[session_id]


def reset_session(session_id: str) -> None:
    with _SESSIONS_LOCK:
        if not session_id:
            session_id = "default"
        _SESSIONS[session_id] = create_session()


class ChatbotHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep terminal output clean
        pass

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            if os.path.exists(INDEX_PATH):
                with open(INDEX_PATH, "r", encoding="utf-8") as f:
                    html = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return
            else:
                self.send_error(404, "index.html not found")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        if path == "/api/chat":
            user_message = body.get("message", "").strip()
            session_id = body.get("session_id", "default")

            if not user_message:
                self._send_json(400, {"error": "Message cannot be empty"})
                return

            session = get_or_create_session(session_id)
            result = _AGENT.handle_message(session, user_message)

            # If user sent exit/quit/end, reset session context for subsequent turns
            if user_message.lower() in ("exit", "quit", "end", "bye", "goodbye"):
                reset_session(session_id)

            self._send_json(200, {
                "response": result.get("response", ""),
                "handoff": result.get("handoff", False),
                "tool_called": result.get("tool_called", False),
                "session_id": session_id
            })
            return

        elif path == "/api/reset":
            session_id = body.get("session_id", "default")
            reset_session(session_id)
            self._send_json(200, {"status": "ok", "session_id": session_id})
            return

        self.send_error(404, "Not Found")


def start_server(port: int = 8000):
    server_address = ("", port)
    server_cls = getattr(http.server, "ThreadingHTTPServer", http.server.HTTPServer)
    httpd = server_cls(server_address, ChatbotHTTPRequestHandler)
    print("==================================================")
    print(" Aster & Row Support Agent - Web UI Server")
    print(f" URL: http://localhost:{port}")
    print(" Press Ctrl+C to stop the server.")
    print("==================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    start_server(port)
