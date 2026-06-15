"""Tests for metrics.py"""

import metrics


FIXTURE_MD = """---
podcast: "Test Pod"
episode: "An Episode Title"
date: 2026-06-10
duration: "1:14:58"
url: "https://example.com"
---

# An Episode Title — Test Pod

## Summary
This is a two paragraph summary.

It covers ground.

## Key Points
- **First Insight:** Something here.
- **Second Insight:** Another thing.
- **Third Insight:** And another.

## Tools & Resources
- Tool A
- Tool B

## Quotable
> "A pithy quote here."
> "Another quote."

## Action Items
- [ ] Do thing one
- [ ] Do thing two
- [ ] Read book X
- [x] Already done thing

## Full Transcript

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.
"""

LOW_SIGNAL_MD = """---
podcast: "Test"
episode: "Filler"
date: 2026-06-10
duration: "30:00"
---

# Filler

## Summary
This episode is mostly entertainment with low signal value.

## Key Points
- Nothing really

## Action Items

## Full Transcript

Words.
"""


class TestParseFrontmatter:
    def test_basic(self):
        fm, body = metrics.parse_frontmatter(FIXTURE_MD)
        assert fm["podcast"] == "Test Pod"
        assert fm["duration"] == "1:14:58"
        assert body.startswith("\n# An Episode Title")

    def test_no_frontmatter(self):
        fm, body = metrics.parse_frontmatter("# Hi\n\nBody")
        assert fm == {}
        assert body == "# Hi\n\nBody"

    def test_malformed_yaml(self):
        fm, _body = metrics.parse_frontmatter("---\n: : invalid\n---\nbody")
        # yaml.safe_load may handle gracefully — accept either {} or a dict
        assert isinstance(fm, dict)


class TestExtractSections:
    def test_finds_all(self):
        _, body = metrics.parse_frontmatter(FIXTURE_MD)
        sections = metrics.extract_sections(body)
        assert "Summary" in sections
        assert "Key Points" in sections
        assert "Action Items" in sections
        assert "Full Transcript" not in sections

    def test_section_body(self):
        _, body = metrics.parse_frontmatter(FIXTURE_MD)
        sections = metrics.extract_sections(body)
        assert "First Insight" in sections["Key Points"]


class TestParseDuration:
    def test_hms(self):
        assert metrics.parse_duration_to_seconds("1:14:58") == 4498

    def test_ms(self):
        assert metrics.parse_duration_to_seconds("30:42") == 1842

    def test_empty(self):
        assert metrics.parse_duration_to_seconds("") == 0

    def test_unknown(self):
        assert metrics.parse_duration_to_seconds("unknown") == 0

    def test_none(self):
        assert metrics.parse_duration_to_seconds(None) == 0


class TestComputeHeuristics:
    parsed = None

    def setup_method(self):
        _, body = metrics.parse_frontmatter(FIXTURE_MD)
        self.parsed = {
            "frontmatter": {"podcast": "Test Pod", "episode": "An Episode Title",
                            "date": "2026-06-10", "duration": "1:14:58"},
            "sections": metrics.extract_sections(body),
            "transcript": "Lorem ipsum transcript text.",
        }

    def test_action_items_counted(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["action_items_count"] == 4  # 3 [ ] + 1 [x]

    def test_key_points_counted(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["key_points_count"] == 3

    def test_tools_counted(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["tools_count"] == 2

    def test_quotables_counted(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["quotables_count"] == 2

    def test_audio_duration(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["audio_duration_seconds"] == 4498

    def test_signal_density_nonzero(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["signal_density"] > 0

    def test_low_signal_false_for_normal(self):
        h = metrics.compute_heuristics(self.parsed)
        assert h["low_signal_flag"] is False

    def test_low_signal_flag_detected(self):
        _, body = metrics.parse_frontmatter(LOW_SIGNAL_MD)
        parsed = {
            "frontmatter": {"duration": "30:00"},
            "sections": metrics.extract_sections(body),
            "transcript": "",
        }
        h = metrics.compute_heuristics(parsed)
        assert h["low_signal_flag"] is True


class TestContentHash:
    def test_stable_across_whitespace(self):
        _, body1 = metrics.parse_frontmatter(FIXTURE_MD)
        _, body2 = metrics.parse_frontmatter(FIXTURE_MD.replace("two paragraph", "two   paragraph"))
        p1 = {"sections": metrics.extract_sections(body1)}
        p2 = {"sections": metrics.extract_sections(body2)}
        assert metrics.content_hash(p1) == metrics.content_hash(p2)

    def test_differs_on_content_change(self):
        _, body1 = metrics.parse_frontmatter(FIXTURE_MD)
        _, body2 = metrics.parse_frontmatter(FIXTURE_MD.replace("First Insight", "Different Insight"))
        p1 = {"sections": metrics.extract_sections(body1)}
        p2 = {"sections": metrics.extract_sections(body2)}
        assert metrics.content_hash(p1) != metrics.content_hash(p2)


class TestParseJudgeResponse:
    def test_clean_json(self):
        raw = (
            '{"actionability": 8, "signal_density": 7, "would_recommend": true,'
            ' "rationale": "Strong actionable insights"}'
        )
        result = metrics.parse_judge_response(raw)
        assert result["actionability"] == 8
        assert result["would_recommend"] is True
        assert "Strong" in result["rationale"]

    def test_wrapped_in_text(self):
        raw = (
            'Here is my response: {"actionability": 5, "signal_density": 4,'
            ' "would_recommend": false, "rationale": "ok"}\nThanks!'
        )
        result = metrics.parse_judge_response(raw)
        assert result["actionability"] == 5
        assert result["would_recommend"] is False

    def test_malformed_returns_none(self):
        assert metrics.parse_judge_response("nope no json here") is None

    def test_empty_returns_none(self):
        assert metrics.parse_judge_response("") is None

    def test_truncates_long_rationale(self):
        long_rationale = "x" * 1000
        raw = f'{{"actionability": 5, "signal_density": 5, "would_recommend": true, "rationale": "{long_rationale}"}}'
        result = metrics.parse_judge_response(raw)
        assert len(result["rationale"]) <= 500


class TestParseEpisode:
    def test_reads_transcript_from_raw_corpus(self, tmp_path, monkeypatch):
        monkeypatch.setattr(metrics, "BASE_DIR", tmp_path)
        md_path = tmp_path / "transcripts" / "test-pod" / "2026-06-10--an-episode.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text(FIXTURE_MD, encoding="utf-8")
        raw_path = tmp_path / "raw" / "test-pod" / "2026-06-10--an-episode.txt"
        raw_path.parent.mkdir(parents=True)
        raw_path.write_text("Raw transcript body from corpus.", encoding="utf-8")
        parsed = metrics.parse_episode(md_path)
        assert parsed is not None
        assert parsed["frontmatter"]["podcast"] == "Test Pod"
        assert "Summary" in parsed["sections"]
        assert parsed["transcript"] == "Raw transcript body from corpus."

    def test_missing_raw_transcript_is_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(metrics, "BASE_DIR", tmp_path)
        md_path = tmp_path / "transcripts" / "pod" / "2026-06-10--ep.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text(FIXTURE_MD, encoding="utf-8")
        parsed = metrics.parse_episode(md_path)
        assert parsed is not None
        assert parsed["transcript"] == ""

    def test_missing_file_returns_none(self, tmp_path):
        assert metrics.parse_episode(tmp_path / "missing.md") is None


class TestLoadExistingMetrics:
    def test_empty_file(self, tmp_path):
        assert not metrics.load_existing_metrics(tmp_path / "missing.jsonl")

    def test_round_trip(self, tmp_path):
        jsonl = tmp_path / "m.jsonl"
        row = {"path": "transcripts/foo/ep.md", "content_hash": "abc123", "x": 1}
        metrics.append_metrics_row(jsonl, row)
        loaded = metrics.load_existing_metrics(jsonl)
        assert ("transcripts/foo/ep.md", "abc123") in loaded

    def test_skips_malformed_lines(self, tmp_path):
        jsonl = tmp_path / "m.jsonl"
        jsonl.write_text('{"path":"a","content_hash":"h"}\nnot json\n{"path":"b","content_hash":"h2"}\n')
        loaded = metrics.load_existing_metrics(jsonl)
        assert len(loaded) == 2
