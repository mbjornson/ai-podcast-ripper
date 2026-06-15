#!/usr/bin/env python3
"""Keyword full-text search across raw episode transcripts (SQLite FTS5).

Index: one FTS5 document per episode (the raw/<slug>/<stem>.txt body), with
episode metadata pulled from the sibling markdown frontmatter. Query: BM25
ranking with highlighted snippets. Complements the semantic search in search.py,
which only covers the structured summary sections.

Usage:
    python transcript_search.py --index             # build/update the index
    python transcript_search.py "pricing strategy"  # query CLI
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

import metrics as metrics_mod

BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "raw"
DB_PATH = BASE_DIR / ".transcript_index.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("transcript-search")


def _connect(db_path):
    """Open the DB, creating the FTS5 table + sidecar on first use."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS transcripts USING fts5("
            "body, rel_path UNINDEXED, md_path UNINDEXED, podcast_slug UNINDEXED, "
            "podcast UNINDEXED, episode_title UNINDEXED, date UNINDEXED, "
            "tokenize = 'porter unicode61 remove_diacritics 2')"
        )
    except sqlite3.OperationalError as exc:
        conn.close()
        raise RuntimeError("This SQLite build lacks FTS5 support") from exc
    conn.execute(
        "CREATE TABLE IF NOT EXISTS indexed_files "
        "(rel_path TEXT PRIMARY KEY, mtime REAL, size INTEGER)"
    )
    return conn


def _index_episode(conn, raw_path, transcripts_dir):
    """Insert/replace one transcript document, pulling metadata from its .md."""
    slug = raw_path.parent.name
    stem = raw_path.stem
    rel_path = f"{slug}/{stem}.txt"
    body = raw_path.read_text(encoding="utf-8")

    md_fs = transcripts_dir / slug / f"{stem}.md"
    fm = {}
    if md_fs.exists():
        fm, _ = metrics_mod.parse_frontmatter(md_fs.read_text(encoding="utf-8"))

    conn.execute("DELETE FROM transcripts WHERE rel_path = ?", (rel_path,))
    conn.execute(
        "INSERT INTO transcripts "
        "(body, rel_path, md_path, podcast_slug, podcast, episode_title, date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (body, rel_path, f"transcripts/{slug}/{stem}.md", slug,
         fm.get("podcast") or slug, fm.get("episode") or stem, str(fm.get("date") or "")),
    )


def build_index(raw_dir=None, db_path=None, force=False, limit=0):
    """Build/update the FTS5 index. Incremental via file mtime+size. Returns count."""
    raw_dir = raw_dir or RAW_DIR
    db_path = db_path or DB_PATH
    transcripts_dir = raw_dir.parent / "transcripts"
    if force:
        Path(db_path).unlink(missing_ok=True)

    conn = _connect(db_path)
    try:
        n = 0
        for raw_path in sorted(raw_dir.rglob("*.txt")):
            rel_path = f"{raw_path.parent.name}/{raw_path.stem}.txt"
            st = raw_path.stat()
            row = conn.execute(
                "SELECT mtime, size FROM indexed_files WHERE rel_path = ?", (rel_path,)
            ).fetchone()
            if row and row[0] == st.st_mtime and row[1] == st.st_size:
                continue
            _index_episode(conn, raw_path, transcripts_dir)
            conn.execute(
                "INSERT OR REPLACE INTO indexed_files (rel_path, mtime, size) VALUES (?, ?, ?)",
                (rel_path, st.st_mtime, st.st_size),
            )
            n += 1
            if n % 200 == 0:
                log.info("... %d indexed", n)
            if limit and n >= limit:
                break
        conn.commit()
    finally:
        conn.close()
    log.info("Indexed/updated %d transcript(s).", n)
    return n


def _row_to_result(row):
    md_path, podcast_slug, podcast, episode_title, ep_date, snippet, rank = row
    return {
        "mode": "transcript",
        "score": round(-rank, 4),  # bm25: lower is better -> negate for higher=better
        "podcast": podcast,
        "podcast_slug": podcast_slug,
        "episode_title": episode_title,
        "date": ep_date,
        "path": md_path,
        "snippet": snippet,
        "section": "Transcript",
    }


def _run_query(conn, match, k, podcast_slug):
    sql = (
        "SELECT md_path, podcast_slug, podcast, episode_title, date, "
        "snippet(transcripts, 0, '<mark>', '</mark>', ' … ', 32) AS snippet, "
        "bm25(transcripts) AS rank "
        "FROM transcripts WHERE transcripts MATCH ?"
    )
    params = [match]
    if podcast_slug:
        sql += " AND podcast_slug = ?"
        params.append(podcast_slug)
    sql += " ORDER BY rank LIMIT ?"
    params.append(k)
    return conn.execute(sql, params).fetchall()


def search(query, k=20, podcast_slug=None, db_path=None):
    """Return up to k transcript matches for a query. Optional podcast_slug filter."""
    query = (query or "").strip()
    if not query:
        return []
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"No transcript index at {db_path}. Run: python transcript_search.py --index"
        )
    conn = _connect(db_path)
    try:
        try:
            rows = _run_query(conn, query, k, podcast_slug)
        except sqlite3.OperationalError:
            # Malformed FTS5 expression -> retry as a literal quoted phrase.
            rows = _run_query(conn, '"' + query.replace('"', "") + '"', k, podcast_slug)
        return [_row_to_result(r) for r in rows]
    finally:
        conn.close()


def cli_search(query, k=10):
    results = search(query, k=k)
    if not results:
        print("No results.")
        return
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['score']:.3f}  {r['podcast']} — {r['episode_title'][:80]}")
        print(f"    date: {r['date']}  {r['path']}")
        snippet = r["snippet"].replace("<mark>", "\033[1m").replace("</mark>", "\033[0m")
        print(f"    {snippet}")


def main():
    parser = argparse.ArgumentParser(description="Keyword search over raw transcripts.")
    parser.add_argument("--index", action="store_true", help="Build/update the index")
    parser.add_argument("--force", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--limit", type=int, default=0, help="Index at most N files")
    parser.add_argument("-k", type=int, default=10, help="Top-k results")
    parser.add_argument("query", nargs="*", help="Search query terms")
    args = parser.parse_args()

    if args.index:
        build_index(force=args.force, limit=args.limit)
    elif args.query:
        cli_search(" ".join(args.query), k=args.k)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
