"""Tests for summarize_missing.py"""

import summarize_missing as sm


def test_patch_file_replaces_body_with_summary(tmp_path):
    md = tmp_path / "ep.md"
    md.write_text(
        '---\npodcast: "P"\n---\n\n# Title — P\n\n*(summarization unavailable)*\n',
        encoding="utf-8")
    sm.patch_file(md, "## Summary\nGenerated summary.\n\n## Key Points\n- x")
    out = md.read_text(encoding="utf-8")
    assert out.startswith('---\npodcast: "P"\n---\n\n# Title — P')
    assert "## Summary" in out
    assert "Generated summary." in out
    assert "*(summarization unavailable)*" not in out
    assert "## Full Transcript" not in out


def test_patch_file_no_h1_skips(tmp_path):
    md = tmp_path / "ep.md"
    md.write_text("no title here\n", encoding="utf-8")
    sm.patch_file(md, "summary")
    assert md.read_text(encoding="utf-8") == "no title here\n"
