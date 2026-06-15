"""Tests for migrate_raw_transcripts.py"""

import migrate_raw_transcripts as mig


def _make_md(tmp_path, body="Full transcript text.", slug="test-pod", stem="2026-06-10--ep"):
    md = tmp_path / "transcripts" / slug / f"{stem}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    content = (
        '---\npodcast: "Test Pod"\nepisode: "Ep"\ndate: 2026-06-10\n---\n\n'
        "# Ep — Test Pod\n\n## Summary\nA summary.\n\n## Full Transcript\n\n" + body + "\n"
    )
    md.write_text(content, encoding="utf-8")
    return md


class TestMigrateFile:
    def test_migrates_and_strips(self, tmp_path):
        md = _make_md(tmp_path, body="The full transcript body.")
        raw_dir = tmp_path / "raw"
        assert mig.migrate_file(md, raw_dir) == "migrated"
        raw = raw_dir / "test-pod" / "2026-06-10--ep.txt"
        assert raw.read_text(encoding="utf-8") == "The full transcript body."
        md_text = md.read_text(encoding="utf-8")
        assert "## Full Transcript" not in md_text
        assert "## Summary" in md_text
        assert "A summary." in md_text

    def test_idempotent_rerun(self, tmp_path):
        md = _make_md(tmp_path)
        raw_dir = tmp_path / "raw"
        assert mig.migrate_file(md, raw_dir) == "migrated"
        assert mig.migrate_file(md, raw_dir) == "skipped_no_section"

    def test_resumes_after_partial(self, tmp_path):
        md = _make_md(tmp_path, body="Resumable body.")
        raw_dir = tmp_path / "raw"
        raw = raw_dir / "test-pod" / "2026-06-10--ep.txt"
        raw.parent.mkdir(parents=True)
        raw.write_text("Resumable body.", encoding="utf-8")  # pre-written, matches
        assert mig.migrate_file(md, raw_dir) == "migrated"
        assert "## Full Transcript" not in md.read_text(encoding="utf-8")
        assert raw.read_text(encoding="utf-8") == "Resumable body."

    def test_empty_transcript_not_stripped(self, tmp_path):
        md = _make_md(tmp_path, body="")
        raw_dir = tmp_path / "raw"
        assert mig.migrate_file(md, raw_dir) == "empty_transcript"
        assert "## Full Transcript" in md.read_text(encoding="utf-8")
        assert not (raw_dir / "test-pod" / "2026-06-10--ep.txt").exists()

    def test_no_section_skipped(self, tmp_path):
        md = tmp_path / "transcripts" / "pod" / "2026-06-10--x.md"
        md.parent.mkdir(parents=True)
        md.write_text("# X\n\n## Summary\nNo transcript here.\n", encoding="utf-8")
        assert mig.migrate_file(md, tmp_path / "raw") == "skipped_no_section"

    def test_dry_run_changes_nothing(self, tmp_path):
        md = _make_md(tmp_path, body="Body.")
        before = md.read_text(encoding="utf-8")
        raw_dir = tmp_path / "raw"
        assert mig.migrate_file(md, raw_dir, dry_run=True) == "would_migrate"
        assert md.read_text(encoding="utf-8") == before
        assert not (raw_dir / "test-pod" / "2026-06-10--ep.txt").exists()

    def test_verify_failure_aborts_strip(self, tmp_path, monkeypatch):
        md = _make_md(tmp_path, body="Body.")
        raw_dir = tmp_path / "raw"
        monkeypatch.setattr(mig, "_write_and_verify", lambda raw_path, body: False)
        assert mig.migrate_file(md, raw_dir) == "verify_failed"
        assert "## Full Transcript" in md.read_text(encoding="utf-8")


class TestRun:
    def test_counts_and_skips_digests(self, tmp_path):
        _make_md(tmp_path, body="A.", slug="pod-a", stem="2026-01-01--a")
        _make_md(tmp_path, body="B.", slug="pod-b", stem="2026-01-02--b")
        digest = tmp_path / "transcripts" / "digests" / "2026-01-03.md"
        digest.parent.mkdir(parents=True)
        digest.write_text("# Digest\n\n## Full Transcript\nx\n", encoding="utf-8")
        counts = mig.run(tmp_path / "transcripts", tmp_path / "raw")
        assert counts["migrated"] == 2
        assert "## Full Transcript" in digest.read_text(encoding="utf-8")

    def test_limit_and_podcast_filter(self, tmp_path):
        _make_md(tmp_path, body="A.", slug="pod-a", stem="2026-01-01--a")
        _make_md(tmp_path, body="B.", slug="pod-b", stem="2026-01-02--b")
        counts = mig.run(tmp_path / "transcripts", tmp_path / "raw", podcast="pod-a")
        assert counts["migrated"] == 1
        assert (tmp_path / "raw" / "pod-a" / "2026-01-01--a.txt").exists()
        assert not (tmp_path / "raw" / "pod-b").exists()
