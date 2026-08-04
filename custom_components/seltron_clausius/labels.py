from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

CONF_LABELS = "labels"
_LABEL_KEY = re.compile(r"^(relay|temperature|circuit):[A-Za-z0-9_-]+$")
_MAX_LABEL_LENGTH = 80


def channel_label(
    options: Mapping[str, Any], category: str, code: str, fallback: str
) -> str:
    """Return a user-defined channel label without changing the stable code."""
    labels = options.get(CONF_LABELS, {})
    if not isinstance(labels, Mapping):
        return fallback
    value = labels.get(f"{category}:{code}")
    return value if isinstance(value, str) and value.strip() else fallback


def normalize_labels(values: Mapping[str, Any]) -> dict[str, str]:
    """Validate and normalize labels stored by the options flow."""
    normalized: dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(value, str):
            continue
        label = value.strip()
        if not label:
            continue
        if not isinstance(key, str) or not _LABEL_KEY.fullmatch(key):
            raise ValueError("Unsupported label channel")
        if len(label) > _MAX_LABEL_LENGTH:
            raise ValueError("Label is too long")
        if any(ord(character) < 32 or ord(character) == 127 for character in label):
            raise ValueError("Label contains control characters")
        normalized[key] = label
    return normalized
