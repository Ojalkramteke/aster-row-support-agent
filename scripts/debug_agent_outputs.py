import sys, os
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.app import SupportAgent, create_session

cases = [
    "What is my return window if I have TrailPlus membership?",
    "A final-sale bag arrived with a broken zipper yesterday. Am I completely out of luck?",
    "Do you ship internationally?",
    "What about Canada, and how long does it take?",
    "Please check ORD-9999.",
    "When did I place ORD-1006?",
    "Cancel my order ORD-1002",
]

agent = SupportAgent()
session = create_session()
for c in cases:
    out = agent.handle_message(session, c)
    print('INPUT:', c)
    print('OUTPUT RESPONSE:', out.get('response'))
    print('RETRIEVED:', out.get('retrieved'))
    print('ORDER:', out.get('order'))
    print('---')
