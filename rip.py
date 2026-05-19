#!/usr/bin/env python3
"""Podcast ripper: fetch → transcribe → summarize → markdown."""

import json
import logging
import os
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
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_PATH, "w") as f:
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


def convert_to_wav(input_path, wav_path):
    log.info("Converting to WAV: %s", input_path.name)
    subprocess.run(
        [
            "ffmpeg", "-i", str(input_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            "-y", str(wav_path),
        ],
        capture_output=True,
        check=True,
    )


def get_audio_duration(wav_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav_path)],
        capture_output=True,
        text=True,
    )
    try:
        secs = float(result.stdout.strip())
        mins, secs = divmod(int(secs), 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
    except ValueError:
        return "unknown"


def transcribe(wav_path, model_name):
    whisper_bin = shutil.which("whisper-cli")
    if not whisper_bin:
        log.error("whisper-cli not found. Install: brew install whisper-cpp")
        sys.exit(1)

    model_path = Path(f"/opt/homebrew/share/whisper-cpp/models/ggml-{model_name}.bin")
    if not model_path.exists():
        log.error("Whisper model not found: %s", model_path)
        log.error("Download: whisper-cpp-download-ggml-model %s", model_name)
        sys.exit(1)

    log.info("Transcribing: %s (model: %s)", wav_path.name, model_name)
    result = subprocess.run(
        [whisper_bin, "-m", str(model_path), "-f", str(wav_path), "--no-timestamps", "-otxt"],
        capture_output=True,
        text=True,
    )
    txt_path = wav_path.with_suffix(".wav.txt")
    if txt_path.exists():
        return txt_path.read_text().strip()

    if result.stdout.strip():
        return result.stdout.strip()

    log.error("Transcription produced no output. stderr: %s", result.stderr[:500])
    return None


def build_prompt(summary_config, podcast_name, episode_title, transcript):
    interests = summary_config.get("listener_interests", "")
    sections = summary_config.get("sections", [])

    context = f"You are analyzing a podcast episode transcript."
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


def process_episode(episode, feed_name, settings):
    slug = slugify(f"{feed_name}--{episode['title']}")
    audio_ext = Path(episode["audio_url"].split("?")[0]).suffix or ".mp3"
    audio_path = TMP_DIR / f"{slug}{audio_ext}"
    wav_path = TMP_DIR / f"{slug}.wav"

    try:
        transcript = None
        duration = "unknown"

        if episode.get("transcript_url"):
            transcript = fetch_transcript(episode["transcript_url"], episode.get("transcript_type", ""))
            if transcript:
                log.info("Using existing transcript for: %s", episode["title"])

        if not transcript:
            download_audio(episode["audio_url"], audio_path)
            convert_to_wav(audio_path, wav_path)
            duration = get_audio_duration(wav_path)
            transcript = transcribe(wav_path, settings["whisper_model"])

        if not transcript:
            return False

        summary = summarize(
            transcript, episode["title"], feed_name,
            settings["ollama_model"], settings.get("_summary_config", {}),
        )

        ep_date = parse_episode_date(episode.get("published", ""))
        podcast_slug = slugify(feed_name)
        ep_slug = slugify(episode["title"])
        output_path = TRANSCRIPTS_DIR / podcast_slug / f"{ep_date}--{ep_slug}.md"
        write_markdown(output_path, feed_name, episode, duration, transcript, summary)
        return True

    finally:
        if not settings.get("keep_audio", False):
            audio_path.unlink(missing_ok=True)
            wav_path.unlink(missing_ok=True)
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
            success = process_episode(ep, feed_name, settings)
            if success:
                state.setdefault(feed_url, []).append(ep["guid"])
                save_state(state)
                total_processed += 1
            else:
                log.error("Failed: %s", ep["title"])

    log.info("Done. Processed %d episode(s).", total_processed)


if __name__ == "__main__":
    main()
