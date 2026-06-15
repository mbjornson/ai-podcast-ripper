"""Tests for transcript_search.py (SQLite FTS5 keyword search over raw/)."""

import pytest

import transcript_search as ts


def _setup_corpus(tmp_path):
    """Create a raw/ + transcripts/ pair with two episodes. Returns raw_dir."""
    raw_dir = tmp_path / "raw"
    tr_dir = tmp_path / "transcripts"
    (raw_dir / "pod-a").mkdir(parents=True)
    (raw_dir / "pod-a" / "2026-01-01--ep1.txt").write_text(
        "We discussed pricing strategy for enterprise software at length.", encoding="utf-8")
    (tr_dir / "pod-a").mkdir(parents=True)
    (tr_dir / "pod-a" / "2026-01-01--ep1.md").write_text(
        '---\npodcast: "Pod A"\nepisode: "Pricing Ep"\ndate: 2026-01-01\n---\n\n# x\n',
        encoding="utf-8")
    (raw_dir / "pod-b").mkdir(parents=True)
    (raw_dir / "pod-b" / "2026-02-02--ep2.txt").write_text(
        "This one covers hiring and team building, nothing about money.", encoding="utf-8")
    (tr_dir / "pod-b").mkdir(parents=True)
    (tr_dir / "pod-b" / "2026-02-02--ep2.md").write_text(
        '---\npodcast: "Pod B"\nepisode: "Hiring Ep"\ndate: 2026-02-02\n---\n\n# y\n',
        encoding="utf-8")
    return raw_dir


class TestBuildAndSearch:
    def test_finds_keyword_with_metadata_and_snippet(self, tmp_path):
        raw_dir = _setup_corpus(tmp_path)
        db = tmp_path / "idx.db"
        ts.build_index(raw_dir=raw_dir, db_path=db, force=True)
        results = ts.search("pricing", db_path=db)
        assert len(results) == 1
        r = results[0]
        assert r["podcast"] == "Pod A"
        assert r["episode_title"] == "Pricing Ep"
        assert r["date"] == "2026-01-01"
        assert r["path"] == "transcripts/pod-a/2026-01-01--ep1.md"
        assert r["mode"] == "transcript"
        assert r["section"] == "Transcript"
        assert "<mark>pricing</mark>" in r["snippet"]

    def test_podcast_filter(self, tmp_path):
        raw_dir = _setup_corpus(tmp_path)
        db = tmp_path / "idx.db"
        ts.build_index(raw_dir=raw_dir, db_path=db, force=True)
        assert len(ts.search("team", db_path=db)) == 1
        assert ts.search("team", podcast_slug="pod-a", db_path=db) == []

    def test_empty_query_returns_empty(self, tmp_path):
        raw_dir = _setup_corpus(tmp_path)
        db = tmp_path / "idx.db"
        ts.build_index(raw_dir=raw_dir, db_path=db, force=True)
        assert ts.search("   ", db_path=db) == []

    def test_malformed_query_does_not_raise(self, tmp_path):
        raw_dir = _setup_corpus(tmp_path)
        db = tmp_path / "idx.db"
        ts.build_index(raw_dir=raw_dir, db_path=db, force=True)
        out = ts.search('AND OR pricing"', db_path=db)
        assert isinstance(out, list)

    def test_incremental_skips_unchanged_and_picks_up_edits(self, tmp_path):
        raw_dir = _setup_corpus(tmp_path)
        db = tmp_path / "idx.db"
        assert ts.build_index(raw_dir=raw_dir, db_path=db, force=True) == 2
        assert ts.build_index(raw_dir=raw_dir, db_path=db) == 0
        edited = raw_dir / "pod-a" / "2026-01-01--ep1.txt"
        edited.write_text("Totally new content about valuation multiples.", encoding="utf-8")
        assert ts.build_index(raw_dir=raw_dir, db_path=db) == 1
        assert len(ts.search("valuation", db_path=db)) == 1
        assert ts.search("pricing", db_path=db) == []

    def test_missing_index_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ts.search("anything", db_path=tmp_path / "nope.db")
