#!/usr/bin/env python3
"""Podcast ripper: fetch → transcribe → summarize → markdown."""

import json
import logging
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import yaml
from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
STATE_PATH = BASE_DIR / "state.json"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
TMP_DIR = BASE_DIR / "tmp"

OLLAMA_URL = "http://localhost:11434/api/generate"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("podcast-ripper")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)[:80]


NON_RSS_DOMAINS = ["spotify.com", "apple.com/podcast", "youtube.com", "youtu.be"]


def get_new_episodes(feed_url, feed_name, state, max_episodes, settings=None):
    if any(d in feed_url for d in NON_RSS_DOMAINS):
        log.error(
            "%s: URL is not an RSS feed (%s). Find the podcast's RSS feed URL instead.",
            feed_name, feed_url,
        )
        return []

    processed = set(state.get(feed_url, []))
    feed = feedparser.parse(feed_url)
    if feed.bozo and not feed.entries:
        log.error("Failed to parse feed: %s (%s)", feed_name, feed_url)
        return []

    all_unprocessed = []
    for entry in feed.entries:
        guid = entry.get("id", entry.get("link", ""))
        if guid in processed:
            continue
        enclosures = entry.get("enclosures", [])
        audio_url = next(
            (e.href for e in enclosures if "audio" in e.get("type", "")),
            None,
        )
        if not audio_url:
            continue

        published = entry.get("published", "")
        transcript_meta = entry.get("podcast_transcript")
        all_unprocessed.append({
            "guid": guid,
            "title": entry.get("title", "Untitled"),
            "audio_url": audio_url,
            "published": published,
            "link": entry.get("link", ""),
            "transcript_url": transcript_meta.get("url") if isinstance(transcript_meta, dict) else None,
            "transcript_type": transcript_meta.get("type", "") if isinstance(transcript_meta, dict) else "",
        })

    recent = all_unprocessed[:max_episodes]
    if recent:
        return recent

    backfill = (settings or {}).get("backfill_episodes", 3)
    older = _get_backfill_episodes(feed_url, feed, processed, backfill)
    if older:
        log.info("No new episodes, backfilling %d older episode(s) for: %s", len(older), feed_name)
    return older


def _get_backfill_episodes(feed_url, feed, processed, count):
    """Grab unprocessed episodes from deeper in the feed's back catalog."""
    backfill = []
    for entry in reversed(feed.entries):
        guid = entry.get("id", entry.get("link", ""))
        if guid in processed:
            continue
        enclosures = entry.get("enclosures", [])
        audio_url = next(
            (e.href for e in enclosures if "audio" in e.get("type", "")),
            None,
        )
        if not audio_url:
            continue
        transcript_meta = entry.get("podcast_transcript")
        backfill.append({
            "guid": guid,
            "title": entry.get("title", "Untitled"),
            "audio_url": audio_url,
            "published": entry.get("published", ""),
            "link": entry.get("link", ""),
            "transcript_url": transcript_meta.get("url") if isinstance(transcript_meta, dict) else None,
            "transcript_type": transcript_meta.get("type", "") if isinstance(transcript_meta, dict) else "",
        })
        if len(backfill) >= count:
            break
    return backfill


def strip_vtt_srt(text):
    """Strip timestamps and formatting from VTT/SRT transcript to plain text."""
    lines = text.splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line or line == "WEBVTT":
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"[\d:.,]+ --> [\d:.,]+", line):
            continue
        if line.startswith("NOTE"):
            continue
        line = re.sub(r"<v\s+([^>]+)>", r"\1: ", line)
        line = re.sub(r"<[^>]+>", "", line)
        out.append(line)
    return "\n".join(out)


def fetch_transcript(url, content_type):
    """Download and parse a transcript from the feed's podcast:transcript tag."""
    log.info("Fetching existing transcript: %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "podcast-ripper/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("Failed to fetch transcript: %s", e)
        return None

    if not raw or len(raw) < 200:
        return None

    ctype = (content_type or "").lower()
    if "vtt" in ctype or "vtt" in url.lower() or raw.strip().startswith("WEBVTT"):
        return strip_vtt_srt(raw)
    if "srt" in ctype or "srt" in url.lower() or re.match(r"^\d+\s*\n[\d:,]+ -->", raw.strip()):
        return strip_vtt_srt(raw)
    return raw


def download_audio(audio_url, dest_path):
    log.info("Downloading: %s", audio_url)
    req = urllib.request.Request(audio_url, headers={"User-Agent": "podcast-ripper/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest_path, "wb") as f:
        shutil.copyfileobj(resp, f)



def get_audio_duration(wav_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        secs = float(result.stdout.strip())
        mins, secs = divmod(int(secs), 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
    except ValueError:
        return "unknown"


_WHISPER_MODEL = {}


def transcribe(audio_path, model_name):
    if model_name not in _WHISPER_MODEL:
        log.info("Loading Faster Whisper model: %s (first run downloads ~3GB)", model_name)
        _WHISPER_MODEL[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
    model = _WHISPER_MODEL[model_name]
    log.info("Transcribing: %s (model: %s)", audio_path.name, model_name)
    segments, _info = model.transcribe(str(audio_path), beam_size=5)
    text = " ".join(seg.text.strip() for seg in segments)
    if not text:
        log.error("Transcription produced no output for: %s", audio_path.name)
    return text or None


def build_prompt(summary_config, podcast_name, episode_title, transcript):
    interests = summary_config.get("listener_interests", "")
    sections = summary_config.get("sections", [])

    context = "You are analyzing a podcast episode transcript."
    if interests:
        context += f" The listener follows {interests} content."

    section_lines = []
    for s in sections:
        heading = s["heading"]
        instruction = s["instruction"]
        fmt = s.get("format", "prose")
        if fmt == "bullets":
            section_lines.append(f"## {heading}\n- [{instruction}]")
        elif fmt == "checklist":
            section_lines.append(f"## {heading}\n- [ ] [{instruction}]")
        elif fmt == "quotes":
            section_lines.append(f"## {heading}\n> [{instruction}]")
        else:
            section_lines.append(f"## {heading}\n[{instruction}]")

    return f"""{context}

Podcast: {podcast_name}
Episode: {episode_title}

Provide your response in exactly this format:

{chr(10).join(section_lines)}

Focus on actionable signal over generic advice. Skip pleasantries and filler. If the episode is mostly entertainment with low signal, say so.

Transcript:
{transcript[:12000]}"""


def summarize(transcript, episode_title, podcast_name, model, summary_config):
    log.info("Summarizing with %s...", model)
    prompt = build_prompt(summary_config, podcast_name, episode_title, transcript)

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 2048, "temperature": 0.3},
    })

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload.encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")
    except Exception as e:
        log.error("Ollama summarization failed: %s", e)
        return None


def parse_episode_date(published):
    try:
        return parsedate_to_datetime(published).date().isoformat()
    except Exception:
        return date.today().isoformat()


def write_markdown(output_path, podcast_name, episode, duration, transcript, summary):
    episode_date = parse_episode_date(episode.get("published", ""))
    content = f"""---
podcast: "{podcast_name}"
episode: "{episode['title']}"
date: {episode_date}
duration: "{duration}"
url: "{episode.get('link', '')}"
---

# {episode['title']} — {podcast_name}

{summary or "*(summarization unavailable)*"}

## Full Transcript

{transcript}
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    log.info("Wrote: %s", output_path)


def extract_sections(markdown_text, section_headings):
    parts = re.split(r"(?m)^## ", markdown_text)
    sections = {}
    for part in parts[1:]:
        lines = part.split("\n", 1)
        heading = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if heading == "Full Transcript":
            continue
        if heading in section_headings:
            sections[heading] = body
    return sections


def generate_digest(processed_episodes, digest_config):
    section_headings = digest_config.get("sections", ["Summary", "Key Points", "Action Items"])
    output_dir = TRANSCRIPTS_DIR / digest_config.get("output_dir", "digests")
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}.md"

    grouped = {}
    for feed_name, ep_title, ep_path in processed_episodes:
        grouped.setdefault(feed_name, []).append((ep_title, ep_path))

    podcast_names = list(grouped.keys())
    episode_count = len(processed_episodes)

    lines = [
        "---",
        "type: digest",
        f"date: {today}",
        f"episodes: {episode_count}",
        f"podcasts: {podcast_names}",
        "---",
        "",
        f"# Daily Digest — {today}",
        "",
    ]

    for feed_name, episodes in grouped.items():
        lines.append(f"## {feed_name}")
        lines.append("")

        for ep_title, ep_path in episodes:
            lines.append(f"### {ep_title}")
            lines.append("")

            try:
                content = ep_path.read_text(encoding="utf-8")
            except OSError:
                log.warning("Could not read episode file for digest: %s", ep_path)
                lines.append("*(episode file unavailable)*")
                lines.append("")
                continue

            sections = extract_sections(content, section_headings)
            for heading in section_headings:
                body = sections.get(heading, "")
                if body:
                    lines.append(f"**{heading}**")
                    lines.append("")
                    lines.append(body)
                    lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote daily digest: %s (%d episodes from %d podcasts)",
             output_path, episode_count, len(podcast_names))


def process_episode(episode, feed_name, settings):
    slug = slugify(f"{feed_name}--{episode['title']}")
    audio_ext = Path(episode["audio_url"].split("?")[0]).suffix or ".mp3"
    audio_path = TMP_DIR / f"{slug}{audio_ext}"

    try:
        transcript = None
        duration = "unknown"

        if episode.get("transcript_url"):
            transcript = fetch_transcript(episode["transcript_url"], episode.get("transcript_type", ""))
            if transcript:
                log.info("Using existing transcript for: %s", episode["title"])

        if not transcript:
            download_audio(episode["audio_url"], audio_path)
            duration = get_audio_duration(audio_path)
            transcript = transcribe(audio_path, settings["whisper_model"])

        if not transcript:
            return None

        summary = summarize(
            transcript, episode["title"], feed_name,
            settings["ollama_model"], settings.get("_summary_config", {}),
        )

        ep_date = parse_episode_date(episode.get("published", ""))
        podcast_slug = slugify(feed_name)
        ep_slug = slugify(episode["title"])
        output_path = TRANSCRIPTS_DIR / podcast_slug / f"{ep_date}--{ep_slug}.md"
        write_markdown(output_path, feed_name, episode, duration, transcript, summary)
        return output_path

    finally:
        if not settings.get("keep_audio", False):
            audio_path.unlink(missing_ok=True)
            for f in TMP_DIR.glob(f"{slug}*"):
                f.unlink(missing_ok=True)


def main():
    config = load_config()
    feeds = config.get("feeds") or []
    settings = config.get("settings", {})
    settings["_summary_config"] = config.get("summary", {})

    if not feeds:
        log.warning("No feeds in config.yaml. Add some podcast RSS URLs and re-run.")
        return

    state = load_state()
    TMP_DIR.mkdir(exist_ok=True)

    total_processed = 0
    processed_episodes = []
    for feed_cfg in feeds:
        feed_name = feed_cfg["name"]
        feed_url = feed_cfg["url"]
        max_eps = settings.get("max_episodes_per_feed", 3)

        log.info("Checking feed: %s", feed_name)
        episodes = get_new_episodes(feed_url, feed_name, state, max_eps, settings)

        if not episodes:
            log.info("No new episodes for: %s", feed_name)
            continue

        log.info("Found %d new episode(s) for: %s", len(episodes), feed_name)
        for ep in episodes:
            log.info("Processing: %s", ep["title"])
            try:
                result = process_episode(ep, feed_name, settings)
            except Exception:
                log.exception("Crashed processing: %s", ep["title"])
                result = None
            if result:
                state.setdefault(feed_url, []).append(ep["guid"])
                save_state(state)
                total_processed += 1
                processed_episodes.append((feed_name, ep["title"], result))
            else:
                log.error("Failed: %s", ep["title"])

    digest_config = config.get("digest", {})
    if processed_episodes and digest_config.get("enabled", False):
        generate_digest(processed_episodes, digest_config)

    log.info("Done. Processed %d episode(s).", total_processed)


if __name__ == "__main__":
    main()
