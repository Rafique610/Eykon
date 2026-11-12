"""Laptop/phone schema parity (EYKO-98, Head 2 C1).

Runs the laptop's DDL (src/video_memory/schema.py) and the phone's statements
(android/.../video/VideoSchema.kt) into two empty SQLite databases and compares
what SQLite actually built: tables, columns, keys, foreign keys and indexes.
Known, intended differences are listed here and nowhere else.
"""

import re
import sqlite3
from pathlib import Path

import pytest

from src.video_memory import schema

KOTLIN = Path(__file__).parents[1] / "android/app/src/main/java/com/eykon/memory/video/VideoSchema.kt"
PHONE_ONLY = {"jobs"}  # the phone's job queue (Head 3); the laptop runs stages directly
FTS = "video_texts_fts"  # phone SQLite has no FTS5, so the phone uses fts4 (see VideoSchema.kt)


def phone_statements() -> list[str]:
    """The SQL strings inside VideoSchema.STATEMENTS, as Kotlin hands them to execSQL."""
    src = KOTLIN.read_text(encoding="utf-8")
    block = src[src.index("private val STATEMENTS = listOf("):src.index("fun create(")]
    found = re.findall(r'"""(.*?)"""|"((?:[^"\\\n]|\\.)*)"', block, flags=re.S)
    return [triple or single for triple, single in found]


def build(statements: list[str]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    for sql in statements:
        conn.executescript(sql)  # triggers hold several ';'
    return conn


def tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    return {name for (name,) in rows if not name.startswith(FTS + "_")}  # FTS shadow tables differ by version


def shape(conn: sqlite3.Connection, table: str) -> dict:
    return {
        "columns": [tuple(r[1:]) for r in conn.execute(f"PRAGMA table_info({table})")],
        "foreign_keys": sorted(tuple(r[2:5]) + (r[6],) for r in conn.execute(f"PRAGMA foreign_key_list({table})")),
        "indexes": sorted(
            (r[1], r[2], tuple(c[2] for c in conn.execute(f"PRAGMA index_info({r[1]})")))
            for r in conn.execute(f"PRAGMA index_list({table})")
        ),
    }


@pytest.fixture(scope="module")
def sides():
    laptop = sqlite3.connect(":memory:")
    schema.init_db(laptop)
    phone = build(phone_statements())
    yield laptop, phone
    laptop.close()
    phone.close()


def test_phone_statements_are_found():
    assert len(phone_statements()) >= 15


def test_same_tables(sides):
    laptop, phone = sides
    assert tables(laptop) == tables(phone) - PHONE_ONLY
    assert set(schema.TABLES) <= tables(laptop)


def test_same_columns_keys_and_indexes(sides):
    laptop, phone = sides
    for table in sorted(tables(laptop) - {FTS}):
        assert shape(laptop, table) == shape(phone, table), table


def test_keyword_index_covers_the_same_text(sides):
    laptop, phone = sides
    for conn in (laptop, phone):
        assert [r[1] for r in conn.execute(f"PRAGMA table_info({FTS})")] == ["text"]
