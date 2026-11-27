"""BM25-поиск по каталогу. Только stdlib.

Позже заменяется на bge-m3, интерфейс останется тот же:
    index = Index.build(records); index.search("тепло уют бабушке", k=10)
"""
from __future__ import annotations

import json
import math
import re

_WORD = re.compile(r"[а-яёa-z0-9]+")
_STOP = {
    "и", "в", "во", "на", "с", "со", "для", "из", "от", "до", "по", "к", "ко",
    "о", "об", "при", "без", "над", "под", "за", "не", "или", "а", "но",
    "это", "как", "что", "все", "весь", "его", "её", "их", "же", "ли", "бы",
    "шт", "см", "мл", "гр", "кг", "мм", "шт.", "уп",
}


def normalize(text: str) -> list[str]:
    """Токены + грубая основа: 'тапочки'/'тапочек' -> 'тапоч'."""
    out = []
    for w in _WORD.findall(str(text).lower()):
        if w in _STOP or len(w) < 3:
            continue
        out.append(w[:5])
    return out


def record_text(rec: dict) -> str:
    parts = [rec.get("title") or ""]
    parts.extend(rec.get("category_path") or [])
    parts.extend(str(v) for v in (rec.get("attributes") or {}).values())
    desc = rec.get("description") or ""
    if desc:
        parts.append(desc[:400])
    return " ".join(parts)


class Index:
    """BM25 (k1=1.5, b=0.75) по каталогу."""

    def __init__(self, docs: list[list[str]], payload: list[dict]):
        self.payload = payload
        self.docs = docs
        self.n = len(docs)
        self.avgdl = sum(len(d) for d in docs) / max(self.n, 1)
        self.tf: list[dict[str, int]] = []
        df: dict[str, int] = {}
        for d in docs:
            counts: dict[str, int] = {}
            for t in d:
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for t in counts:
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.k1, self.b = 1.5, 0.75

    @classmethod
    def build(cls, records: list[dict]) -> "Index":
        return cls([normalize(record_text(r)) for r in records], list(records))

    def search(self, query: str, k: int = 10) -> list[tuple[dict, float]]:
        q = normalize(query)
        if not q or not self.n:
            return []
        scores: list[tuple[float, int]] = []
        for i, counts in enumerate(self.tf):
            dl = len(self.docs[i])
            s = 0.0
            for t in q:
                f = counts.get(t)
                if not f:
                    continue
                idf = self.idf.get(t, 0.0)
                s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scores.append((s, i))

        scores.sort(reverse=True)
        top = scores[:k]
        if not top:
            return []
        hi = top[0][0] or 1.0
        return [(self.payload[i], round(s / hi, 4)) for s, i in top]


def demo(path: str, query: str, k: int = 5) -> None:
    records = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    idx = Index.build(records)
    print(f"запрос: {query!r}  (документов {idx.n})\n")
    for rec, s in idx.search(query, k):
        price = (rec.get("price") or {}).get("discounted")
        print(f"  {s:.3f}  {str(rec.get('title'))[:60]:62} {price or 0:>7.0f}₽")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python -m app.ml.retrieval items.jsonl 'запрос'")
        raise SystemExit(2)
    demo(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5)