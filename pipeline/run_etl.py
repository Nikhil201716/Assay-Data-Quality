"""Orchestrate extract -> transform -> load. Kept independent of the defect
catalog: callers pass already-prepared sources and an optional process-bug flag,
so tests and the scoring harness drive it directly."""

from __future__ import annotations

import sqlite3

from . import load as loadmod
from .generate import generate
from .transform import transform


def run(sources: dict, process_bug: str | None = None,
        conn: sqlite3.Connection | None = None) -> tuple[list[dict], sqlite3.Connection]:
    conn = conn or loadmod.connect()
    rows = transform(sources, process_bug=process_bug)
    loadmod.load(conn, rows, append=(process_bug == "D12"))
    return loadmod.read(conn), conn


def run_clean() -> list[dict]:
    loaded, _ = run(generate())
    return loaded
