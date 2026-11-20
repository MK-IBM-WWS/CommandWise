"""CPU embeddings and semantic re-ranking of compatible BM25 candidates."""

from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class E5:
    dimensions = 384

    def __init__(self, directory: Path):
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "model.onnx"), sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.inputs = {item.name for item in self.session.get_inputs()}

    def encode(self, texts, prefix):
        encodings = self.tokenizer.encode_batch([prefix + text for text in texts])
        inputs = {
            "input_ids": np.asarray([item.ids for item in encodings], dtype=np.int64),
            "attention_mask": np.asarray([item.attention_mask for item in encodings], dtype=np.int64),
        }
        if "token_type_ids" in self.inputs:
            inputs["token_type_ids"] = np.zeros_like(inputs["input_ids"])
        hidden, *_ = self.session.run(None, inputs)
        mask = inputs["attention_mask"][..., None]
        pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1)
        return (pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)).astype(np.float32)

    def index(self, chunks, previous=None):
        known = {} if previous is None else previous["vectors"]
        vectors = np.empty((len(chunks), self.dimensions), dtype=np.float32)
        missing = []
        for position, item in enumerate(chunks):
            key = item["chunk_id"]
            if key in known:
                vectors[position] = known[key]
            else:
                missing.append(position)
        for start in range(0, len(missing), 8):
            batch = missing[start:start + 8]
            vectors[batch] = self.encode([chunks[i]["search_text"] for i in batch], "passage: ")
        return vectors

    def rerank(self, query, candidates, vectors):
        if len(candidates) < 2:
            return candidates
        embedding = self.encode([query], "query: ")[0]
        matrix = np.stack([vectors[item["chunk_id"]] for item in candidates])
        similarities = matrix @ embedding
        semantic_order = np.argsort(-similarities, kind="stable")
        semantic_ranks = np.empty_like(semantic_order)
        semantic_ranks[semantic_order] = np.arange(len(candidates))
        # Weighted reciprocal ranks preserve command and option matches from BM25.
        ranking = sorted(range(len(candidates)), key=lambda i: -(2 / (20 + i) + 1 / (20 + semantic_ranks[i])))
        return [candidates[i] for i in ranking]
