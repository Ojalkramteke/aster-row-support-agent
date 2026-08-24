from typing import Dict, Any, List


def contains_any(text: str, substrs: List[str]) -> bool:
    if not substrs:
        return True
    # normalize by removing punctuation and collapsing whitespace
    import re
    norm = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    norm = re.sub(r"\s+", " ", norm)
    for s in substrs:
        s_norm = re.sub(r"[^a-z0-9\s]", " ", s.lower())
        s_norm = re.sub(r"\s+", " ", s_norm)
        if s_norm in norm:
            return True
    return False


def contains_all(text: str, substrs: List[str]) -> bool:
    import re
    norm = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    norm = re.sub(r"\s+", " ", norm)
    for s in substrs:
        s_norm = re.sub(r"[^a-z0-9\s]", " ", s.lower())
        s_norm = re.sub(r"\s+", " ", s_norm)
        if s_norm not in norm:
            return False
    return True


def check_required_sources(retrieved: List[Dict[str, Any]], required: List[str]) -> (bool, List[str]):
    found = set(r.get("filename") for r in (retrieved or []))
    missing = [s for s in required if s not in found]
    return (len(missing) == 0, missing)
