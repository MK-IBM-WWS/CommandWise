"""Inverted index and BM25 scoring for the CommandWise corpus."""

from collections import Counter, defaultdict
from math import log1p


class BM25Index:
    def __init__(self, lengths, postings, *, k1=1.5, b=0.75):
        self.lengths = lengths
        self.postings = postings
        self.k1 = k1
        self.b = b
        count = len(lengths)
        average = sum(lengths) / count if count else 0
        self.norm = [k1 * (1 - b + b * length / average) for length in lengths] if average else []
        self.idf = {
            term: log1p((count - len(occurrences) + 0.5) / (len(occurrences) + 0.5))
            for term, occurrences in postings.items()
        }

    @classmethod
    def build(cls, documents, **parameters):
        postings = defaultdict(list)
        lengths = []
        for document_id, tokens in enumerate(documents):
            lengths.append(len(tokens))
            for term, frequency in Counter(tokens).items():
                postings[term].append((document_id, frequency))
        return cls(lengths, dict(postings), **parameters)

    def snapshot(self):
        return {"lengths": self.lengths, "postings": self.postings}

    def matching_documents(self, terms):
        return {
            document_id
            for term in terms
            for document_id, _ in self.postings.get(term, ())
        }

    def score(self, terms, candidates=None):
        scores = defaultdict(float)
        for term in sorted(set(terms)):
            if term not in self.postings:
                continue
            weight = self.idf[term] * (self.k1 + 1)
            for document_id, frequency in self.postings[term]:
                if candidates is None or document_id in candidates:
                    scores[document_id] += weight * frequency / (frequency + self.norm[document_id])
        return scores
