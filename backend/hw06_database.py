"""MongoDB connection, validators, indexes, and offline fallback for HW6."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

try:
    from pymongo import MongoClient
except ImportError:  # Offline tests can use the deterministic fallback.
    MongoClient = None


DB_NAME = "s2562_doc"


class MemoryStore:
    def __init__(self):
        self.documents: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self.summaries: list[dict[str, Any]] = []
        self.episodes: list[dict[str, Any]] = []

    def insert(self, collection: str, document: dict[str, Any]) -> str:
        identifier = document.get("_id") or f"offline-{collection}-{len(getattr(self, collection)) + 1}"
        document = {**document, "_id": identifier}
        getattr(self, collection).append(document)
        return identifier

    def find(self, collection: str, predicate=None) -> list[dict[str, Any]]:
        rows = list(getattr(self, collection))
        return [row for row in rows if predicate is None or predicate(row)]

    def replace(self, collection: str, identifier: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        for row in getattr(self, collection):
            if str(row.get("_id")) == str(identifier):
                row.update(patch)
                return row
        return None

    def delete(self, collection: str, identifier: str) -> bool:
        rows = getattr(self, collection)
        for index, row in enumerate(rows):
            if str(row.get("_id")) == str(identifier):
                rows.pop(index)
                return True
        return False


class MongoStore:
    def __init__(self, uri: str | None = None, fallback: MemoryStore | None = None):
        self.fallback = fallback or MemoryStore()
        self.client = None
        self.db = None
        if MongoClient is not None:
            try:
                self.client = MongoClient(
                    uri or os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
                    serverSelectionTimeoutMS=700,
                )
                self.client.admin.command("ping")
                self.db = self.client[DB_NAME]
                self._ensure_indexes()
            except Exception:
                self.client = None
                self.db = None

    @property
    def online(self) -> bool:
        return self.db is not None

    def _ensure_indexes(self):
        validators = {
            "documents": {"$jsonSchema": {"bsonType": "object", "required": ["title", "status", "category", "due_at", "created_at", "updated_at"], "properties": {"title": {"bsonType": "string", "maxLength": 100}, "status": {"enum": ["open", "in_progress", "done"]}, "category": {"enum": ["service", "safety", "operations", "other"]}}}},
            "messages": {"$jsonSchema": {"bsonType": "object", "required": ["user_id", "role", "content", "created_at"], "properties": {"role": {"enum": ["user", "assistant"]}}}},
            "summaries": {"$jsonSchema": {"bsonType": "object", "required": ["user_id", "scope", "text", "created_at"], "properties": {"scope": {"enum": ["session", "user"]}}}},
            "episodes": {"$jsonSchema": {"bsonType": "object", "required": ["user_id", "fact", "importance", "embedding", "created_at"], "properties": {"importance": {"bsonType": "double", "minimum": 0, "maximum": 1}, "embedding": {"bsonType": "array"}}}},
        }
        existing = set(self.db.list_collection_names())
        for name, validator in validators.items():
            if name not in existing:
                self.db.create_collection(name, validator=validator, validationLevel="strict")
        self.db.documents.create_index("created_at")
        self.db.messages.create_index([("user_id", 1), ("session_id", 1), ("created_at", -1)])
        self.db.summaries.create_index([("user_id", 1), ("scope", 1), ("created_at", -1)])
        self.db.episodes.create_index([("user_id", 1), ("created_at", -1)])

    @staticmethod
    def _mongo_id(identifier: str):
        if MongoClient is not None and len(identifier) == 24:
            try:
                from bson import ObjectId
                return ObjectId(identifier)
            except Exception:
                pass
        return identifier

    def insert(self, collection: str, document: dict[str, Any]) -> str:
        if self.online:
            return str(self.db[collection].insert_one(document).inserted_id)
        return self.fallback.insert(collection, document)

    def find(self, collection: str, predicate=None, query=None, sort=None, limit=0):
        if self.online:
            cursor = self.db[collection].find(query or {})
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        rows = self.fallback.find(collection, predicate)
        if sort:
            for key, direction in reversed(sort):
                rows.sort(key=lambda row: row.get(key) or datetime.min.replace(tzinfo=timezone.utc), reverse=direction < 0)
        return rows[:limit] if limit else rows

    def replace(self, collection: str, identifier: str, patch: dict[str, Any]):
        if self.online:
            object_id = self._mongo_id(identifier)
            self.db[collection].update_one({"_id": object_id}, {"$set": patch})
            return self.db[collection].find_one({"_id": object_id})
        return self.fallback.replace(collection, identifier, patch)

    def delete(self, collection: str, identifier: str) -> bool:
        if self.online:
            object_id = self._mongo_id(identifier)
            return self.db[collection].delete_one({"_id": object_id}).deleted_count == 1
        return self.fallback.delete(collection, identifier)
