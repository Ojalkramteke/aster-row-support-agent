import os
import re
import math
from typing import Dict, List, Tuple, Any


KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge-base")


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    # Simple YAML front-matter parser for key: value lines between --- markers
    fm = {}
    rest = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1]
            rest = parts[2]
            for line in raw_fm.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
    return fm, rest.lstrip()


def split_into_passages(text: str) -> List[Tuple[str, str]]:
    # Returns list of (heading, passage_text). Use markdown headings as boundaries.
    lines = text.splitlines()
    passages = []
    current_heading = ""  # document-level or empty
    buffer = []
    heading_regex = re.compile(r"^(#{1,6})\s+(.*)")
    for line in lines:
        m = heading_regex.match(line)
        if m:
            # flush buffer
            if buffer:
                passages.append((current_heading.strip(), "\n".join(buffer).strip()))
                buffer = []
            current_heading = m.group(2).strip()
            continue
        buffer.append(line)

    if buffer:
        passages.append((current_heading.strip(), "\n".join(buffer).strip()))

    # If no headings and long passages, split by paragraphs
    if len(passages) == 1 and passages[0][0] == "":
        text_only = passages[0][1]
        paras = [p.strip() for p in text_only.split("\n\n") if p.strip()]
        passages = [("", p) for p in paras]

    return passages


class Index:
    def __init__(self):
        self.passages = []  # list of dicts with text, filename, heading, front_matter, tokens, tf
        self.df = {}
        self.N = 0

    def build(self, kb_dir: str = None):
        if kb_dir is None:
            kb_dir = KB_DIR
        files = [f for f in os.listdir(kb_dir) if f.endswith(".md")]
        for fname in sorted(files):
            path = os.path.join(kb_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            fm, body = parse_front_matter(raw)
            splits = split_into_passages(body)
            for idx, (heading, ptext) in enumerate(splits):
                if not ptext.strip():
                    continue
                tokens = _tokenize(ptext)
                tf = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1
                # update df
                for t in set(tokens):
                    self.df[t] = self.df.get(t, 0) + 1
                passage = {
                    "id": f"{fname}#{idx}",
                    "filename": fname,
                    "heading": heading,
                    "front_matter": fm,
                    "text": ptext,
                    "tokens": tokens,
                    "tf": tf,
                    "length": len(tokens),
                }
                self.passages.append(passage)
        self.N = len(self.passages)

    def get_passages(self):
        return self.passages

    def idf(self, term: str) -> float:
        # smoothed idf
        df = self.df.get(term, 0)
        return math.log((self.N + 1) / (df + 1)) + 1.0


def build_default_index() -> Index:
    idx = Index()
    idx.build()
    return idx
