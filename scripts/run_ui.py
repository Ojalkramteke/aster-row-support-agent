import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.server import start_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    start_server(port)
