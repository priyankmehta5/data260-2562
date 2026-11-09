"""Redis Search cosine vector cache, scoped experiments, and version invalidation."""

import hashlib
import json
import os
import time

import numpy as np
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from .hw09_common import EMBEDDING, PREFIX, RAW, event, now


def shipping_threshold():
    if os.getenv("HW09_THRESHOLD") is not None:
        return float(os.environ["HW09_THRESHOLD"])
    selected = RAW / "threshold_choice.json"
    return float(json.loads(selected.read_text())["selected"]["threshold"]) if selected.exists() else 0.85


class Embedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(EMBEDDING, local_files_only=True)

    def encode(self, text):
        return np.asarray(self.model.encode(text, normalize_embeddings=True), dtype=np.float32)


class SemanticCache:
    def __init__(self, redis_client, embedder, database, pipeline, scope="live", threshold=0.85):
        if not scope.isalnum():
            raise ValueError("Cache scope must be alphanumeric")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        self.redis, self.embedder, self.database, self.pipeline = redis_client, embedder, database, pipeline
        self.scope, self.threshold = scope, threshold
        self.prefix = f"{PREFIX}:semantic:{scope}:"
        self.index = f"{PREFIX}:index:{scope}"
        try:
            self.redis.ft(self.index).create_index(
                (
                    TextField("query"),
                    TextField("answer"),
                    TagField("version"),
                    VectorField("embedding", "FLAT", {"TYPE": "FLOAT32", "DIM": 384, "DISTANCE_METRIC": "COSINE"}),
                ),
                definition=IndexDefinition(prefix=[self.prefix], index_type=IndexType.HASH),
            )
        except ResponseError as error:
            if "Index already exists" not in str(error):
                raise

    def clear(self):
        # Never FLUSHDB: only the selected HW9 scope is removed.
        for key in self.redis.scan_iter(match=self.prefix + "*"):
            self.redis.delete(key)

    def store(self, query, vector, answer, version):
        key = self.prefix + hashlib.sha256(query.encode()).hexdigest()
        self.redis.hset(
            key,
            mapping={
                "query": query,
                "embedding": vector.tobytes(),
                "answer": answer,
                "version": version,
                "stored_at": now(),
            },
        )
        return key

    def lookup(self, vector, version, enforce_version=True):
        # KNN over Redis's vector index, not a Python scan of embeddings.
        q = (
            Query("*=>[KNN 100 @embedding $vector AS distance]")
            .sort_by("distance")
            .return_fields("query", "answer", "version", "distance")
            .paging(0, 100)
            .dialect(2)
        )
        found = self.redis.ft(self.index).search(q, query_params={"vector": vector.tobytes()})
        for row in found.docs:
            similarity = float(np.clip(1 - float(row.distance), -1, 1))
            if similarity + 1e-7 < self.threshold:
                break
            if enforce_version and row.version != version:
                continue
            return {
                "answer": row.answer,
                "similarity": similarity,
                "cached_query": row.query,
                "cached_version": row.version,
            }
        return None

    async def query(self, question, enforce_version=True, store_miss=True):
        started_at, started = now(), time.perf_counter()
        context = self.database.context(question)
        vector = self.embedder.encode(question)
        hit = self.lookup(vector, context["version"], enforce_version)
        cid = None
        if hit:
            event("cache_hit", question=question, similarity=hit["similarity"], scope=self.scope)
            answer, similarity = hit["answer"], hit["similarity"]
        else:
            event("cache_miss", question=question, scope=self.scope)
            output = await self.pipeline.answer(question, context)
            answer, cid, similarity = output["answer"], output["correlation_id"], None
            if store_miss:
                self.store(question, vector, answer, context["version"])
        result = {
            "query": question,
            "answer": answer,
            "is_cached": bool(hit),
            "similarity": similarity,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "started_at": started_at,
            "finished_at": now(),
            "version": context["version"],
            "correlation_id": cid,
            "cached_query": hit["cached_query"] if hit else None,
            "cached_version": hit["cached_version"] if hit else None,
        }
        event("query_result", **result)
        return result
