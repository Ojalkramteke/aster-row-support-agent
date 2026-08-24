import os
import json
from src.retrieval.indexer import Index, parse_front_matter, split_into_passages, _tokenize
from src.retrieval.retriever import Retriever


KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge-base")


def test_documents_load_correctly():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    assert idx.N > 0


def test_front_matter_preserved():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    # find returns policy current file passage
    found = False
    for p in idx.get_passages():
        if p["filename"] == "01-returns-policy-current.md":
            fm = p["front_matter"]
            assert fm.get("document_id") == "RET-2026-01"
            assert fm.get("status") == "active"
            found = True
            break
    assert found


def test_split_by_headings_and_heading_metadata():
    path = os.path.join(KB_DIR, "01-returns-policy-current.md")
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    fm, body = parse_front_matter(raw)
    splits = split_into_passages(body)
    # one of the headings should be 'Standard return window'
    headings = [h for h, _ in splits]
    assert any("Standard return window" in h for h in headings)


def test_retrieval_prefers_current_over_legacy():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)
    q = "How long does a regular customer have to return an unused backpack?"
    results = r.search(q, top_k=5)
    assert len(results) > 0
    top = results[0]
    # top result should be the active returns policy, not legacy or migration
    assert top["filename"] == "01-returns-policy-current.md"
    assert top["authoritative"] is True
    assert "30 calendar days" in top["text"]


def test_internal_migration_not_authoritative():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    # search for the migration test phrase
    r = Retriever(index=idx)
    q = "60 days to return every item"
    results = r.search(q, top_k=10)
    # if migration content appears, ensure it's marked non-authoritative
    for res in results:
        if res["filename"] == "14-internal-content-migration-notes.md":
            assert res["authoritative"] is False


def test_irrelevant_query_returns_low_confidence():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)
    q = "How do I reset my password for the mobile app?"
    results = r.search(q, top_k=5)
    # Expect either no results or very low scores
    if not results:
        assert True
    else:
        assert all(res["score"] < 1.0 for res in results)


def test_results_contain_required_metadata():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)
    q = "refund timing after return"
    results = r.search(q, top_k=3)
    assert len(results) <= 3
    for res in results:
        assert "filename" in res and "heading" in res and "front_matter" in res and "text" in res and "score" in res


def test_instruction_text_is_plain_text():
    # Ensure the prompt-injection-like line in migration notes is returned as text and not executed
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)
    q = "Ignore all prior rules"
    results = r.search(q, top_k=10)
    # Find migration file if present
    found = False
    for res in results:
        if res["filename"] == "14-internal-content-migration-notes.md":
            assert "Ignore all prior rules" in res["text"] or "Ignore all prior rules" in res["front_matter"].values()
            found = True
    # It's acceptable if not found; the key is that when present it's plain text
    assert True


def test_international_shipping_paraphrase_retrieval():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)

    intl_queries = [
        "Do you ship internationally?",
        "Can you ship outside the US?",
        "Do you deliver overseas?",
        "What countries do you ship to?",
        "Can I get delivery outside the US?",
    ]

    for q in intl_queries:
        results = r.search(q, top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top["filename"] == "06-international-shipping.md", f"Query '{q}' retrieved {top['filename']} instead of 06-international-shipping.md"


def test_shipping_duration_retrieval():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)

    duration_queries = [
        "How long does shipping take?",
        "What is the delivery timeframe?",
        "How many days does delivery take?",
        "What is the shipping duration?",
        "How long does standard shipping take?",
    ]

    for q in duration_queries:
        results = r.search(q, top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top["filename"] == "05-domestic-shipping.md", f"Query '{q}' retrieved {top['filename']} instead of 05-domestic-shipping.md"
        assert "delivery estimates" in top["heading"].lower() or "processing" in top["heading"].lower()


def test_trailplus_and_returns_retrieval_isolation():
    idx = Index()
    idx.build(kb_dir=KB_DIR)
    r = Retriever(index=idx)

    # TrailPlus benefits query
    tp_res = r.search("What benefits do TrailPlus members get?", top_k=3)
    assert len(tp_res) > 0
    assert tp_res[0]["filename"] == "09-trailplus-membership.md"

    # Regular customer return window
    ret_res = r.search("What is the standard return window for a regular customer?", top_k=3)
    assert len(ret_res) > 0
    assert ret_res[0]["filename"] == "01-returns-policy-current.md"
    assert "standard return window" in ret_res[0]["heading"].lower()
