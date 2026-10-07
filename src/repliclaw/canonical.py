"""Byte-stable canonicalization and hashing for commitments.

Canonical form: JSON with sorted keys, no insignificant whitespace,
UTF-8 with ensure_ascii=False. This is stricter than ScienceClaw's
Artifact._hash_payload (which omits compact separators), so RepliClaw
commitments are byte-stable across runs and interpreters.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Serialize to the canonical byte-stable JSON string."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(text: str | bytes) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def commit_hash(payload: Any) -> str:
    """Content hash of a canonicalized commitment payload."""
    return sha256_hex(canonical_json(payload))


def verify_hash(payload: Any, expected: str) -> bool:
    return commit_hash(payload) == expected
