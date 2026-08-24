import sys, os
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.app import SupportAgent, create_session

agent = SupportAgent()
session = create_session()

queries = [
    "What is the return policy?",
    "What about TrailPlus members?",
]

for q in queries:
    out = agent.handle_message(session, q)
    print('QUERY:', q)
    print('RESPONSE:', out.get('response'))
    print('RETRIEVED:', [r.get('filename') for r in out.get('retrieved', [])])
    for r in out.get('retrieved', []) or []:
        print('  -', r.get('filename'), 'authoritative=', r.get('authoritative'))
    print('---')
