"""Utility helpers for ESP32 PhotoFrame."""

from __future__ import annotations

from typing import Any


def normalize_firmware_version(version: Any) -> str:
    """Normalize a firmware version for comparison."""
    return str(version or "").strip().lstrip("vV")
