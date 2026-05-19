"""Tests for rip.py"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import rip


class TestSlugify:
    def test_basic(self):
        assert rip.slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert rip.slugify("What's up? (Part 1)") == "whats-up-part-1"

    def test_truncates_at_80(self):
        long = "a" * 200
        assert len(rip.slugify(long)) == 80

    def test_collapses_dashes(self):
        assert rip.slugify("foo---bar   baz") == "foo-bar-baz"

    def test_strips_whitespace(self):
        assert rip.slugify("  padded  ") == "padded"


class TestParseEpisodeDate:
    def test_rfc2822(self):
        assert rip.parse_episode_date("Mon, 18 May 2026 12:02:11 GMT") == "2026-05-18"

    def test_invalid_falls_back_to_today(self):
        assert rip.parse_episode_date("not a date") == date.today().isoformat()

    def test_empty_falls_back_to_today(self):
        assert rip.parse_episode_date("") == date.today().isoformat()


class TestStripVttSrt:
    def test_vtt(self):
        vtt = """WEBVTT

00:00:00.000 --> 00:00:03.520
<v SPEAKER_00>First line of dialogue.

00:00:03.680 --> 00:00:06.400
<v SPEAKER_01>Second line of dialogue."""
        result = rip.strip_vtt_srt(vtt)
        assert "WEBVTT" not in result
        assert "-->" not in result
        assert "SPEAKER_00: First line of dialogue." in result
        assert "SPEAKER_01: Second line of dialogue." in result

    def test_srt(self):
        srt = """1
00:00:00,000 --> 00:00:03,520
First line.

2
00:00:03,680 --> 00:00:06,400
Second line."""
        result = rip.strip_vtt_srt(srt)
        assert "-->" not in result
        assert "First line." in result
        assert "Second line." in result
        lines = [l for l in result.splitlines() if l.strip()]
        assert len(lines) == 2

    def test_strips_html_tags(self):
        vtt = """WEBVTT

00:00:00.000 --> 00:00:03.000
<b>Bold text</b> and <i>italic</i>."""
        result = rip.strip_vtt_srt(vtt)
        assert "<b>" not in result
        assert "Bold text and italic." in result

    def test_note_lines_stripped(self):
        vtt = """WEBVTT

NOTE This is a comment

00:00:00.000 --> 00:00:01.000
Actual content."""
        result = rip.strip_vtt_srt(vtt)
        assert "NOTE" not in result
        assert "Actual content." in result


class TestBuildPrompt:
    def test_with_interests_and_sections(self):
        config = {
            "listener_interests": "tech and business",
            "sections": [
                {"heading": "Summary", "instruction": "Summarize it"},
                {"heading": "Key Points", "instruction": "List points", "format": "bullets"},
                {"heading": "Action Items", "instruction": "List actions", "format": "checklist"},
                {"heading": "Quotable", "instruction": "Best quotes", "format": "quotes"},
            ],
        }
        prompt = rip.build_prompt(config, "TestPod", "TestEp", "transcript text here")
        assert "tech and business" in prompt
        assert "TestPod" in prompt
        assert "TestEp" in prompt
        assert "## Summary\n[Summarize it]" in prompt
        assert "## Key Points\n- [List points]" in prompt
        assert "## Action Items\n- [ ] [List actions]" in prompt
        assert "## Quotable\n> [Best quotes]" in prompt
        assert "transcript text here" in prompt

    def test_no_interests(self):
        config = {"sections": []}
        prompt = rip.build_prompt(config, "Pod", "Ep", "text")
        assert "The listener follows" not in prompt

    def test_empty_config(self):
        prompt = rip.build_prompt({}, "Pod", "Ep", "text")
        assert "You are analyzing" in prompt

    def test_transcript_truncated(self):
        long_transcript = "x" * 20000
        prompt = rip.build_prompt({}, "Pod", "Ep", long_transcript)
        assert len(long_transcript[:12000]) == 12000
        assert "x" * 12000 in prompt
        assert "x" * 12001 not in prompt


class TestGetNewEpisodes:
    def test_rejects_spotify_url(self):
        result = rip.get_new_episodes(
            "https://open.spotify.com/show/abc123",
            "Test", {}, 3,
        )
        assert result == []

    def test_rejects_apple_url(self):
        result = rip.get_new_episodes(
            "https://podcasts.apple.com/podcast/foo/id123",
            "Test", {}, 3,
        )
        assert result == []

    def test_rejects_youtube_url(self):
        result = rip.get_new_episodes(
            "https://youtube.com/playlist?list=abc",
            "Test", {}, 3,
        )
        assert result == []

    @patch("rip.feedparser.parse")
    def test_skips_processed_episodes(self, mock_parse):
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[
                MagicMock(
                    **{
                        "get.side_effect": lambda k, d=None: {
                            "id": "guid-1", "title": "Ep 1",
                            "published": "Mon, 01 Jan 2026 00:00:00 GMT",
                            "link": "http://example.com/ep1",
                            "enclosures": [MagicMock(
                                href="http://example.com/ep1.mp3",
                                **{"get.return_value": "audio/mpeg"},
                            )],
                            "podcast_transcript": None,
                        }.get(k, d),
                    }
                ),
            ],
        )
        state = {"http://example.com/feed": ["guid-1"]}
        result = rip.get_new_episodes("http://example.com/feed", "Test", state, 3)
        assert result == []

    @patch("rip.feedparser.parse")
    def test_backfill_when_no_new(self, mock_parse):
        entry = MagicMock()
        entry.get = lambda k, d=None: {
            "id": "guid-old", "title": "Old Ep",
            "published": "Mon, 01 Jan 2024 00:00:00 GMT",
            "link": "http://example.com/old",
            "enclosures": [MagicMock(href="http://example.com/old.mp3", **{"get.return_value": "audio/mpeg"})],
            "podcast_transcript": None,
        }.get(k, d)
        mock_parse.return_value = MagicMock(bozo=False, entries=[entry])
        state = {"http://example.com/feed": ["guid-old"]}
        settings = {"backfill_episodes": 3}
        result = rip.get_new_episodes("http://example.com/feed", "Test", state, 3, settings)
        assert result == []


class TestFetchTranscript:
    @patch("rip.urllib.request.urlopen")
    def test_plain_text(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = ("A" * 300).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = rip.fetch_transcript("http://example.com/transcript.txt", "text/plain")
        assert result == "A" * 300

    @patch("rip.urllib.request.urlopen")
    def test_vtt_detected_by_content(self, mock_urlopen):
        vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n" + "Hello world. " * 30
        mock_resp = MagicMock()
        mock_resp.read.return_value = vtt.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = rip.fetch_transcript("http://example.com/t.vtt", "text/vtt")
        assert "WEBVTT" not in result
        assert "-->" not in result
        assert "Hello world." in result

    @patch("rip.urllib.request.urlopen")
    def test_too_short_returns_none(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"short"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = rip.fetch_transcript("http://example.com/t.txt", "text/plain")
        assert result is None

    @patch("rip.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_network_error_returns_none(self, mock_urlopen):
        result = rip.fetch_transcript("http://example.com/t.txt", "text/plain")
        assert result is None


class TestWriteMarkdown:
    def test_creates_file_with_frontmatter(self, tmp_path):
        output = tmp_path / "test-pod" / "2026-05-18--test-ep.md"
        episode = {
            "title": "Test Episode",
            "published": "Sat, 18 May 2026 00:00:00 GMT",
            "link": "http://example.com/ep",
        }
        rip.write_markdown(output, "Test Pod", episode, "45:00", "transcript here", "## Summary\nGood stuff")
        assert output.exists()
        content = output.read_text()
        assert 'podcast: "Test Pod"' in content
        assert 'episode: "Test Episode"' in content
        assert "date: 2026-05-18" in content
        assert 'duration: "45:00"' in content
        assert "## Summary\nGood stuff" in content
        assert "transcript here" in content

    def test_handles_missing_summary(self, tmp_path):
        output = tmp_path / "test.md"
        episode = {"title": "Ep", "published": "", "link": ""}
        rip.write_markdown(output, "Pod", episode, "0:00", "text", None)
        content = output.read_text()
        assert "*(summarization unavailable)*" in content


class TestProcessEpisode:
    @patch("rip.fetch_transcript")
    @patch("rip.summarize", return_value="## Summary\nTest summary")
    @patch("rip.write_markdown")
    def test_uses_existing_transcript(self, mock_write, mock_summarize, mock_fetch):
        mock_fetch.return_value = "Pre-existing transcript text"
        episode = {
            "title": "Ep With Transcript",
            "audio_url": "http://example.com/ep.mp3",
            "published": "Mon, 18 May 2026 00:00:00 GMT",
            "link": "http://example.com/ep",
            "transcript_url": "http://example.com/transcript.txt",
            "transcript_type": "text/plain",
            "guid": "guid-1",
        }
        settings = {
            "whisper_model": "medium",
            "ollama_model": "gemma3",
            "_summary_config": {},
        }
        result = rip.process_episode(episode, "Test Pod", settings)
        assert isinstance(result, Path)
        mock_fetch.assert_called_once_with("http://example.com/transcript.txt", "text/plain")
        mock_summarize.assert_called_once()
        assert "Pre-existing transcript text" in mock_summarize.call_args[0][0]

    @patch("rip.fetch_transcript", return_value=None)
    @patch("rip.download_audio")
    @patch("rip.convert_to_wav")
    @patch("rip.get_audio_duration", return_value="30:00")
    @patch("rip.transcribe", return_value="Whisper transcript")
    @patch("rip.summarize", return_value="## Summary\nTest")
    @patch("rip.write_markdown")
    def test_falls_back_to_audio(self, mock_write, mock_summarize, mock_transcribe,
                                  mock_duration, mock_convert, mock_download, mock_fetch):
        episode = {
            "title": "Ep Without Transcript",
            "audio_url": "http://example.com/ep.mp3",
            "published": "Mon, 18 May 2026 00:00:00 GMT",
            "link": "http://example.com/ep",
            "transcript_url": "http://example.com/broken.txt",
            "transcript_type": "text/plain",
            "guid": "guid-2",
        }
        settings = {
            "whisper_model": "medium",
            "ollama_model": "gemma3",
            "_summary_config": {},
        }
        result = rip.process_episode(episode, "Test Pod", settings)
        assert isinstance(result, Path)
        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()

    @patch("rip.fetch_transcript", return_value=None)
    @patch("rip.download_audio")
    @patch("rip.convert_to_wav")
    @patch("rip.get_audio_duration", return_value="10:00")
    @patch("rip.transcribe", return_value=None)
    def test_returns_false_when_no_transcript(self, mock_transcribe, mock_duration,
                                              mock_convert, mock_download, mock_fetch):
        episode = {
            "title": "Failed Ep",
            "audio_url": "http://example.com/ep.mp3",
            "published": "",
            "link": "",
            "transcript_url": None,
            "transcript_type": "",
            "guid": "guid-3",
        }
        settings = {
            "whisper_model": "medium",
            "ollama_model": "gemma3",
            "_summary_config": {},
        }
        result = rip.process_episode(episode, "Test Pod", settings)
        assert result is None


class TestExtractSections:
    def test_extracts_requested_sections(self):
        md = """---
podcast: "Test"
---

# Episode Title — Test

## Summary
This is the summary.

## Key Points
- Point one
- Point two

## Tools & Resources
- Some tool

## Full Transcript

Long transcript text here."""
        result = rip.extract_sections(md, ["Summary", "Key Points"])
        assert "This is the summary." in result["Summary"]
        assert "- Point one" in result["Key Points"]
        assert "Full Transcript" not in result
        assert "Tools & Resources" not in result

    def test_skips_full_transcript_even_if_requested(self):
        md = "## Summary\nGood stuff\n\n## Full Transcript\nLong text"
        result = rip.extract_sections(md, ["Summary", "Full Transcript"])
        assert "Summary" in result
        assert "Full Transcript" not in result

    def test_missing_section_not_in_result(self):
        md = "## Summary\nGood stuff"
        result = rip.extract_sections(md, ["Summary", "Action Items"])
        assert "Summary" in result
        assert "Action Items" not in result

    def test_empty_input(self):
        result = rip.extract_sections("", ["Summary"])
        assert not result


class TestGenerateDigest:
    def test_creates_digest_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rip, "TRANSCRIPTS_DIR", tmp_path)

        ep_dir = tmp_path / "test-pod"
        ep_dir.mkdir()
        ep_path = ep_dir / "2026-05-19--test-ep.md"
        ep_path.write_text("""---
podcast: "Test Pod"
---

# Test Ep — Test Pod

## Summary
Great episode summary.

## Key Points
- Insight one
- Insight two

## Action Items
- [ ] Do something

## Full Transcript

Long transcript here.
""")

        processed = [("Test Pod", "Test Ep", ep_path)]
        digest_config = {
            "sections": ["Summary", "Key Points", "Action Items"],
            "output_dir": "digests",
        }
        rip.generate_digest(processed, digest_config)

        digest_dir = tmp_path / "digests"
        assert digest_dir.exists()
        digest_files = list(digest_dir.glob("*.md"))
        assert len(digest_files) == 1

        content = digest_files[0].read_text()
        assert "type: digest" in content
        assert "## Test Pod" in content
        assert "### Test Ep" in content
        assert "Great episode summary." in content
        assert "Insight one" in content
        assert "Do something" in content
        assert "Long transcript here." not in content

    def test_groups_by_podcast(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rip, "TRANSCRIPTS_DIR", tmp_path)

        ep1 = tmp_path / "ep1.md"
        ep1.write_text("## Summary\nEp1 summary\n\n## Full Transcript\ntext")
        ep2 = tmp_path / "ep2.md"
        ep2.write_text("## Summary\nEp2 summary\n\n## Full Transcript\ntext")

        processed = [
            ("Podcast A", "Episode 1", ep1),
            ("Podcast A", "Episode 2", ep2),
        ]
        digest_config = {"sections": ["Summary"], "output_dir": "digests"}
        rip.generate_digest(processed, digest_config)

        digest_path = tmp_path / "digests" / f"{date.today().isoformat()}.md"
        content = digest_path.read_text()
        assert content.count("## Podcast A") == 1
        assert "### Episode 1" in content
        assert "### Episode 2" in content

    def test_handles_unreadable_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rip, "TRANSCRIPTS_DIR", tmp_path)

        missing_path = tmp_path / "nonexistent.md"
        processed = [("Pod", "Ep", missing_path)]
        digest_config = {"sections": ["Summary"], "output_dir": "digests"}
        rip.generate_digest(processed, digest_config)

        digest_path = tmp_path / "digests" / f"{date.today().isoformat()}.md"
        content = digest_path.read_text()
        assert "*(episode file unavailable)*" in content

    def test_multiple_podcasts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rip, "TRANSCRIPTS_DIR", tmp_path)

        ep1 = tmp_path / "ep1.md"
        ep1.write_text("## Summary\nAlpha summary")
        ep2 = tmp_path / "ep2.md"
        ep2.write_text("## Summary\nBeta summary")

        processed = [
            ("Podcast Alpha", "Ep A", ep1),
            ("Podcast Beta", "Ep B", ep2),
        ]
        digest_config = {"sections": ["Summary"], "output_dir": "digests"}
        rip.generate_digest(processed, digest_config)

        content = (tmp_path / "digests" / f"{date.today().isoformat()}.md").read_text()
        assert "## Podcast Alpha" in content
        assert "## Podcast Beta" in content
        assert "Alpha summary" in content
        assert "Beta summary" in content
        assert "episodes: 2" in content


class TestMainDigestWiring:
    @patch("rip.generate_digest")
    @patch("rip.process_episode")
    @patch("rip.get_new_episodes")
    @patch("rip.save_state")
    @patch("rip.load_state", return_value={})
    @patch("rip.load_config")
    def test_calls_digest_when_enabled(self, mock_config, mock_load_state,
                                        mock_save, mock_get_eps, mock_process,
                                        mock_digest):
        mock_config.return_value = {
            "feeds": [{"name": "TestPod", "url": "http://example.com/feed"}],
            "settings": {"max_episodes_per_feed": 3},
            "summary": {},
            "digest": {"enabled": True, "sections": ["Summary"], "output_dir": "digests"},
        }
        ep_path = Path("/tmp/fake-ep.md")
        mock_get_eps.return_value = [{"title": "Ep1", "guid": "g1"}]
        mock_process.return_value = ep_path

        rip.main()

        mock_digest.assert_called_once()
        call_args = mock_digest.call_args[0]
        assert call_args[0] == [("TestPod", "Ep1", ep_path)]
        assert call_args[1]["enabled"] is True

    @patch("rip.generate_digest")
    @patch("rip.process_episode")
    @patch("rip.get_new_episodes")
    @patch("rip.save_state")
    @patch("rip.load_state", return_value={})
    @patch("rip.load_config")
    def test_skips_digest_when_disabled(self, mock_config, mock_load_state,
                                         mock_save, mock_get_eps, mock_process,
                                         mock_digest):
        mock_config.return_value = {
            "feeds": [{"name": "TestPod", "url": "http://example.com/feed"}],
            "settings": {"max_episodes_per_feed": 3},
            "summary": {},
            "digest": {"enabled": False},
        }
        mock_get_eps.return_value = [{"title": "Ep1", "guid": "g1"}]
        mock_process.return_value = Path("/tmp/fake.md")

        rip.main()

        mock_digest.assert_not_called()

    @patch("rip.generate_digest")
    @patch("rip.process_episode")
    @patch("rip.get_new_episodes")
    @patch("rip.save_state")
    @patch("rip.load_state", return_value={})
    @patch("rip.load_config")
    def test_skips_digest_when_no_episodes(self, mock_config, mock_load_state,
                                            mock_save, mock_get_eps, mock_process,
                                            mock_digest):
        mock_config.return_value = {
            "feeds": [{"name": "TestPod", "url": "http://example.com/feed"}],
            "settings": {"max_episodes_per_feed": 3},
            "summary": {},
            "digest": {"enabled": True},
        }
        mock_get_eps.return_value = []

        rip.main()

        mock_digest.assert_not_called()


class TestSaveLoadState:
    def test_round_trip(self, tmp_path, monkeypatch):
        state_path = tmp_path / "state.json"
        monkeypatch.setattr(rip, "STATE_PATH", state_path)
        rip.save_state({"http://feed.com": ["guid-1", "guid-2"]})
        loaded = rip.load_state()
        assert loaded == {"http://feed.com": ["guid-1", "guid-2"]}

    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rip, "STATE_PATH", tmp_path / "missing.json")
        assert rip.load_state() == {}
