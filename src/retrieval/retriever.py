from typing import List, Dict, Any
import math

from .indexer import Index, build_default_index


class Retriever:
    def __init__(self, index: Index = None):
        self.index = index or build_default_index()

    def _passage_authoritative(self, passage: Dict[str, Any]) -> bool:
        fm = passage.get("front_matter", {})
        return fm.get("policy_authority", "").lower() == "official" and fm.get("status", "").lower() == "active"

    def score(self, query: str, passage: Dict[str, Any]) -> float:
        qtokens = [t for t in __import__("re").findall(r"\w+", query.lower())]
        # filter common stopwords to reduce accidental matches on generic queries
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "is",
            "are",
            "of",
            "to",
            "for",
            "in",
            "on",
            "do",
            "how",
            "i",
            "you",
            "my",
            "be",
            "with",
            "that",
            "it",
        }
        qtokens = [t for t in qtokens if t not in stopwords and len(t) > 2]
        if not qtokens:
            return 0.0
        score = 0.0
        for t in qtokens:
            tf = passage["tf"].get(t, 0)
            if tf == 0:
                continue
            idf = self.index.idf(t)
            score += tf * idf

        # length normalization
        if passage["length"] > 0:
            score = score / math.log(2 + passage["length"])

        # authority boosting / demotion
        if self._passage_authoritative(passage):
            score *= 1.8
        else:
            # demote known non-authoritative files (legacy, migration, internal)
            fname = passage.get("filename", "").lower()
            if "legacy" in fname or "migration" in fname or "internal" in fname:
                score *= 0.35

        # topical boosting: prefer returns-related authoritative docs for return queries
        returns_terms = {"return", "returns", "refund", "refunds"}
        if any(t in qtokens for t in returns_terms):
            fm = passage.get("front_matter", {})
            fname = passage.get("filename", "").lower()
            heading = passage.get("heading", "").lower()
            docid = fm.get("document_id", "").upper()
            if docid.startswith("RET"):
                # strong boost for official returns policies
                score *= 2.5
            elif "returns" in fname or "return" in heading:
                score *= 1.5
            else:
                # demote non-returns docs for return queries
                score *= 0.7

        return float(score)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        scores = []
        for p in self.index.get_passages():
            sc = self.score(query, p)
            if sc > 0:
                scores.append((sc, p))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sc, p in scores[:top_k]:
            results.append(
                {
                    "score": sc,
                    "text": p["text"],
                    "filename": p["filename"],
                    "heading": p["heading"],
                    "front_matter": p["front_matter"],
                    "authoritative": self._passage_authoritative(p),
                }
            )
        return results
