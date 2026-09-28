#!/usr/bin/env python3
# pylint: disable=too-many-lines
"""Podcast ripper: fetch → transcribe → summarize → markdown."""

import argparse
import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import yaml
from faster_whisper import WhisperModel

import metrics as metrics_mod

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
STATE_PATH = BASE_DIR / "state.json"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
RAW_DIR = BASE_DIR / "raw"
TMP_DIR = BASE_DIR / "tmp"
METRICS_PATH = BASE_DIR / "metrics.jsonl"
RECOVERY_STATE_PATH = BASE_DIR / "recovery-state.json"

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


def load_recovery_state():
    """Load retry and quarantine state without changing the completed state schema."""
    if RECOVERY_STATE_PATH.exists():
        try:
            with open(RECOVERY_STATE_PATH, encoding="utf-8") as f:
                recovery = json.load(f)
            if not isinstance(recovery, dict):
                raise ValueError("recovery state must be a JSON object")
            # Validate nested structure: episode_failures and provider_outage must be dicts
            ep_failures = recovery.get("episode_failures")
            if ep_failures is not None and not isinstance(ep_failures, dict):
                raise ValueError("episode_failures must be a dict")
            for feed_episodes in (recovery.get("episode_failures") or {}).values():
                if not isinstance(feed_episodes, dict):
                    raise ValueError("episode_failures values must be dicts")
            provider_outage = recovery.get("provider_outage")
            if provider_outage is not None and not isinstance(provider_outage, dict):
                raise ValueError("provider_outage must be a dict")
            return recovery
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            corrupt_path = RECOVERY_STATE_PATH.with_name(
                f"{RECOVERY_STATE_PATH.name}.corrupt-{time.time_ns()}"
            )
            try:
                os.replace(RECOVERY_STATE_PATH, corrupt_path)
                log.warning("Moved corrupt recovery state to %s: %s", corrupt_path, exc)
            except OSError:
                log.warning("Could not preserve corrupt recovery state: %s", exc)
    return {"episode_failures": {}, "provider_outage": {}}


_RECOVERY_LOCK_PATH = RECOVERY_STATE_PATH.with_suffix(".lock")


def _acquire_recovery_lock(timeout=30):
    """Acquire exclusive lock on recovery state file. Blocks until acquired or timeout."""
    _RECOVERY_LOCK_PATH.touch(exist_ok=True)
    lock_file = None
    try:
        lock_file = open(_RECOVERY_LOCK_PATH, "w", encoding="utf-8")  # pylint: disable=consider-using-with
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file
        except (IOError, OSError) as exc:
            lock_file.close()
            start = time.time()
            while time.time() - start < timeout:
                lock_file = open(_RECOVERY_LOCK_PATH, "w", encoding="utf-8")  # pylint: disable=consider-using-with
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    return lock_file
                except (IOError, OSError):
                    lock_file.close()
                    time.sleep(0.1)
            raise TimeoutError(
                f"Could not acquire recovery state lock after {timeout}s"
            ) from exc
    except Exception:
        if lock_file:
            lock_file.close()
        raise


def save_recovery_state(recovery):
    temporary_path = RECOVERY_STATE_PATH.with_name(
        f".{RECOVERY_STATE_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    try:
        with open(temporary_path, "w", encoding="utf-8") as f:
            json.dump(recovery, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, RECOVERY_STATE_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)


def _episode_failure_key(feed_url, episode):
    return f"{feed_url}\n{episode['guid']}"


def _is_provider_failure(reason):
    """Detect if a failure is provider-level (timeout, API down) vs episode-level."""
    reason_lower = str(reason).lower()
    provider_keywords = [
        "timeout", "connection", "refused", "reset by peer",
        "500", "503", "502", "429", "api", "server error",
        "unreachable", "unavailable", "down", "service unavailable",
    ]
    return any(kw in reason_lower for kw in provider_keywords)


def is_episode_quarantined(recovery, feed_url, episode):
    """Return false and reset a quarantine if the publisher changed its URL."""
    failures = recovery.setdefault("episode_failures", {})
    key = _episode_failure_key(feed_url, episode)
    record = failures.get(key)
    if not record:
        return False
    if record.get("audio_url") != episode.get("audio_url"):
        del failures[key]
        return False
    return bool(record.get("quarantined"))


def release_episode_if_enclosure_changed(recovery, feed_url, episode):
    """Clear stale failure state when a feed republishes an episode with a new URL."""
    failures = recovery.setdefault("episode_failures", {})
    key = _episode_failure_key(feed_url, episode)
    record = failures.get(key)
    if record and record.get("audio_url") != episode.get("audio_url"):
        del failures[key]
        return True
    return False


def record_episode_failure(recovery, feed_url, episode, reason, limit=3):
    """Increment an episode's failure count and quarantine it at ``limit``."""
    failures = recovery.setdefault("episode_failures", {})
    key = _episode_failure_key(feed_url, episode)
    record = failures.get(key, {})
    if record.get("audio_url") != episode.get("audio_url"):
        record = {"count": 0, "audio_url": episode.get("audio_url")}
    record["count"] = record.get("count", 0) + 1
    record["audio_url"] = episode.get("audio_url")
    record["last_error"] = str(reason)
    record["quarantined"] = record["count"] >= limit
    failures[key] = record
    return record["quarantined"]


def clear_episode_failure(recovery, feed_url, episode):
    return recovery.setdefault("episode_failures", {}).pop(
        _episode_failure_key(feed_url, episode), None,
    ) is not None


def record_provider_outage(recovery, reason, today):
    """Record an unresolved dependency failure and report whether to remind today."""
    outage = recovery["provider_outage"] = {
        "active": True,
        "last_error": str(reason),
        "last_reminder_date": recovery.get("provider_outage", {}).get("last_reminder_date"),
    }
    if outage["last_reminder_date"] == today:
        return False
    outage["last_reminder_date"] = today
    return True


def clear_provider_outage(recovery):
    recovery["provider_outage"] = {"active": False}


def preflight_summarizer(settings):
    """Verify the summary dependency before audio work begins."""
    if settings.get("llm_provider", "ollama") != "omlx":
        return True, None
    try:
        return metrics_mod.omlx_model_ready(
            metrics_mod.configured_model(settings),
            base_url=settings.get("omlx_base_url", metrics_mod.OMLX_BASE_URL),
            api_key=settings.get("omlx_api_key"),
            attempts=settings.get("omlx_preflight_attempts", 3),
            backoff_seconds=tuple(settings.get("omlx_preflight_backoff_seconds") or ()),
        )
    except (TypeError, ValueError) as exc:
        return False, f"oMLX preflight configuration error: {exc}"


def pause_for_provider_outage(config, recovery, reason):
    """Persist and announce a paused run, then return its non-zero exit status."""
    reminder_due = record_provider_outage(recovery, reason, date.today().isoformat())
    save_recovery_state(recovery)
    log.error("Run paused before processing: %s", reason)
    if notify_enabled(config.get("notify", {}).get("enabled", False)):
        notify_complete(f"Run paused - {reason}")
        if reminder_due:
            notify_complete(f"Daily reminder - podcast-ripper is paused: {reason}")
    return 1


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)[:80]


def raw_path_for_md(md_path):
    """Map transcripts/<slug>/<stem>.md -> raw/<slug>/<stem>.txt."""
    return RAW_DIR / md_path.parent.name / (md_path.stem + ".txt")


NON_RSS_DOMAINS = ["spotify.com", "apple.com/podcast", "youtube.com", "youtu.be"]


def get_new_episodes(feed_url, feed_name, state, max_episodes, settings=None,  # pylint: disable=too-many-branches
                     recovery=None, on_recovery_change=None):
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

        episode = {
            "guid": guid,
            "title": entry.get("title", "Untitled"),
            "audio_url": audio_url,
            "published": entry.get("published", ""),
            "link": entry.get("link", ""),
            "transcript_url": None,
            "transcript_type": "",
        }
        if recovery is not None:
            if release_episode_if_enclosure_changed(recovery, feed_url, episode):
                if on_recovery_change:
                    on_recovery_change(recovery)
            if is_episode_quarantined(recovery, feed_url, episode):
                log.warning("Quarantined after repeated failures; skipping: %s", episode["title"])
                continue

        published = entry.get("published", "")
        transcript_meta = entry.get("podcast_transcript")
        episode["published"] = published
        episode["transcript_url"] = transcript_meta.get("url") if isinstance(transcript_meta, dict) else None
        episode["transcript_type"] = transcript_meta.get("type", "") if isinstance(transcript_meta, dict) else ""
        all_unprocessed.append(episode)

    # Deduplicate episodes by GUID to prevent duplicate entries from exhausting retries
    seen_guids = set()
    deduped = []
    for ep in all_unprocessed:
        if ep["guid"] not in seen_guids:
            seen_guids.add(ep["guid"])
            deduped.append(ep)

    recent = deduped[:max_episodes]
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
    if dest_path.exists():
        log.info("Already downloaded: %s", dest_path.name)
        return
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


def _transcribe_cpu(audio_path, model_name):
    """Transcribe with faster-whisper on CPU (int8). Slow, but never off."""
    if model_name not in _WHISPER_MODEL:
        log.info("Loading Faster Whisper model: %s (first run downloads ~3GB)", model_name)
        _WHISPER_MODEL[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
    model = _WHISPER_MODEL[model_name]
    log.info("Transcribing on CPU: %s (model: %s)", audio_path.name, model_name)
    segments, _info = model.transcribe(str(audio_path), beam_size=5)
    return " ".join(seg.text.strip() for seg in segments)


def transcribe(audio_path, settings):
    """Transcribe an episode. Returns (text, engine); text is None on failure.

    oMLX runs Whisper on the GPU and is the default. It is a network call to a
    local daemon, so any failure drops through to the in-process CPU engine
    rather than losing the episode.
    """
    if settings.get("transcribe_provider", "omlx") == "omlx":
        model_name = settings.get("omlx_whisper_model")
        log.info("Transcribing on GPU via oMLX: %s (model: %s)", audio_path.name, model_name)
        text = metrics_mod.omlx_transcribe(
            audio_path,
            model_name,
            base_url=settings.get("omlx_base_url", metrics_mod.OMLX_BASE_URL),
            api_key=settings.get("omlx_api_key"),
            timeout=settings.get("transcribe_timeout",
                                 metrics_mod.DEFAULT_TRANSCRIBE_TIMEOUT),
        )
        if text:
            return text, "omlx"
        log.warning("oMLX transcription unavailable; falling back to CPU faster-whisper")

    text = _transcribe_cpu(audio_path, settings["whisper_model"])
    if not text:
        log.error("Transcription produced no output for: %s", audio_path.name)
        return None, "faster_whisper"
    return text, "faster_whisper"


# Re-exported from metrics_mod so existing tests + callers keep their import surface.
build_prompt = metrics_mod.build_summary_prompt

SUMMARY_CHUNK_CHARS = 60000
SUMMARY_CHUNK_OVERLAP = 1000
SUMMARY_CHUNK_NUM_PREDICT = 3072
SUMMARY_REQUEST_TIMEOUT = 300


def chunk_transcript(transcript, chunk_chars, overlap):
    """Split transcript into overlapping character-bounded chunks."""
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    if overlap < 0 or overlap >= chunk_chars:
        raise ValueError("overlap must be >= 0 and smaller than chunk_chars")
    chunks = []
    start = 0
    while start < len(transcript):
        end = min(start + chunk_chars, len(transcript))
        chunks.append(transcript[start:end])
        if end == len(transcript):
            break
        start = end - overlap
    return chunks


def _generate(prompt, model, provider, base_url, api_key, num_predict,
              max_context, chat_template_kwargs=None,
              timeout=SUMMARY_REQUEST_TIMEOUT, request_label="summary"):
    num_ctx = metrics_mod.context_window_for(prompt, num_predict, ceiling=max_context)
    started = time.monotonic()
    log.info("LLM request started: %s", request_label)
    result = metrics_mod.generate_text(
        model, prompt, provider=provider, num_predict=num_predict,
        temperature=0.3, num_ctx=num_ctx, base_url=base_url, api_key=api_key,
        chat_template_kwargs=chat_template_kwargs, timeout=timeout,
    )
    elapsed = time.monotonic() - started
    log.info("LLM request finished: %s elapsed_seconds=%.1f result_chars=%d",
             request_label, elapsed, len(result or ""))
    return result


def _chunk_prompt(podcast_name, episode_title, chunk, index, total):
    return (
        "You are preparing factual notes for a podcast episode summary. "
        "Extract the specific claims, names, numbers, tools, quotes, and "
        "actionable advice from this transcript segment. Do not invent or "
        "generalize. These notes will be synthesized with other segments.\n\n"
        f"Podcast: {podcast_name}\nEpisode: {episode_title}\n"
        f"Segment {index} of {total}:\n\n{chunk}"
    )


def summarize(transcript, episode_title, podcast_name, model, summary_config,
              max_chars=metrics_mod.DEFAULT_TRANSCRIPT_CHARS,
              max_context=metrics_mod.DEFAULT_MAX_CONTEXT,
              num_predict=metrics_mod.DEFAULT_NUM_PREDICT,
              provider="ollama", base_url=metrics_mod.OMLX_BASE_URL,
              api_key=None, chunk_chars=SUMMARY_CHUNK_CHARS,
              chunk_overlap=SUMMARY_CHUNK_OVERLAP,
              chunk_num_predict=SUMMARY_CHUNK_NUM_PREDICT,
              request_timeout=SUMMARY_REQUEST_TIMEOUT):
    log.info("Summarizing with %s...", model)
    source = transcript[:max_chars] if max_chars else transcript
    if len(source) <= chunk_chars:
        prompt = build_prompt(summary_config, podcast_name, episode_title, source,
                              max_chars=0)
        log.info("Prompt %d chars -> single-pass summary", len(prompt))
        result = _generate(prompt, model, provider, base_url, api_key, num_predict,
                           max_context, timeout=request_timeout,
                           request_label="single-pass summary")
        return metrics_mod.validate_tools_and_resources(result, source)

    chunks = chunk_transcript(source, chunk_chars, chunk_overlap)
    log.info("Long transcript: summarizing %d chunks", len(chunks))
    notes = []
    for index, chunk in enumerate(chunks, 1):
        prompt = _chunk_prompt(podcast_name, episode_title, chunk, index, len(chunks))
        note = _generate(prompt, model, provider, base_url, api_key,
                         chunk_num_predict, max_context,
                         chat_template_kwargs={"enable_thinking": False},
                         timeout=request_timeout,
                         request_label=f"summary chunk {index}/{len(chunks)}")
        if not note:
            log.warning("Chunk %d/%d summarization failed", index, len(chunks))
            return None
        notes.append(f"Segment {index}:\n{note}")

    synthesis_input = "\n\n".join(notes)
    prompt = build_prompt(summary_config, podcast_name, episode_title,
                          synthesis_input, max_chars=0)
    log.info("Synthesizing %d chunk notes (%d chars)", len(notes), len(prompt))
    result = _generate(prompt, model, provider, base_url, api_key, num_predict,
                       max_context, timeout=request_timeout,
                       chat_template_kwargs={"enable_thinking": False},
                       request_label="chunk synthesis")
    return metrics_mod.validate_tools_and_resources(result, source)


def parse_episode_date(published):
    try:
        return parsedate_to_datetime(published).date().isoformat()
    except Exception:
        return date.today().isoformat()


def write_markdown(output_path, podcast_name, episode, duration, summary):
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


def collect_digest_episodes(target_date):
    """Episodes processed on `target_date` (a date), rebuilt from metrics.jsonl.

    Keyed on the processing timestamp `ts` (converted to local time), NOT the
    episode publish `date` field — the digest is "what got ripped today." Because
    metrics is appended per-episode, this survives a run killed before it finishes
    its feed sweep, and re-running it is idempotent. Deduped by path, latest wins.
    """
    if not METRICS_PATH.exists():
        return []
    by_path = {}
    for line in METRICS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            processed = datetime.fromisoformat(rec["ts"]).astimezone().date()
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
        if processed != target_date:
            continue
        path = Path(rec.get("path", ""))
        if not path.is_absolute():
            path = BASE_DIR / path
        by_path[str(path)] = (rec.get("podcast", ""), rec.get("episode_title", ""), path)
    return list(by_path.values())


def generate_digest(processed_episodes, digest_config, target_date=None):
    section_headings = digest_config.get("sections", ["Summary", "Key Points", "Action Items"])
    output_dir = TRANSCRIPTS_DIR / digest_config.get("output_dir", "digests")
    output_dir.mkdir(parents=True, exist_ok=True)

    today = (target_date or date.today()).isoformat()
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


def record_episode_metrics(output_path, feed_name, podcast_slug, settings,
                            transcribed_seconds, summarized_seconds,
                            transcribe_engine=None):
    """Compute heuristics + optional LLM judge, append row to metrics.jsonl."""
    metrics_cfg = settings.get("_metrics_config", {}) or {}
    if not metrics_cfg.get("enabled", False):
        return

    parsed = metrics_mod.parse_episode(output_path)
    if parsed is None:
        log.warning("Metrics: could not re-read %s", output_path)
        return

    judge_result = None
    if metrics_cfg.get("judge_enabled", False) and parsed["sections"].get("Summary"):
        judge_model = metrics_cfg.get("judge_model") or metrics_mod.configured_model(settings)
        judge_result = metrics_mod.judge_episode(
            parsed, judge_model,
            provider=settings.get("llm_provider", "ollama"),
            base_url=settings.get("omlx_base_url", metrics_mod.OMLX_BASE_URL),
            api_key=settings.get("omlx_api_key"),
        )

    row = metrics_mod.build_metrics_row(
        parsed,
        rel_path=str(output_path.relative_to(BASE_DIR)),
        podcast_slug=podcast_slug,
        fallback_podcast_name=feed_name,
        judge_result=judge_result,
        transcribed_seconds=transcribed_seconds,
        summarized_seconds=summarized_seconds,
        transcribe_engine=transcribe_engine,
    )
    metrics_mod.append_metrics_row(METRICS_PATH, row)


def process_episode(episode, feed_name, settings):
    slug = slugify(f"{feed_name}--{episode['title']}")
    audio_url_hash = hashlib.md5(episode["audio_url"].encode()).hexdigest()[:8]
    audio_ext = Path(episode["audio_url"].split("?")[0]).suffix or ".mp3"
    audio_path = TMP_DIR / f"{slug}--{audio_url_hash}{audio_ext}"
    completed = False

    try:
        transcript = None
        duration = "unknown"
        transcribed_seconds = None
        summarized_seconds = None
        transcribe_engine = None

        if episode.get("transcript_url"):
            transcript = fetch_transcript(episode["transcript_url"], episode.get("transcript_type", ""))
            if transcript:
                log.info("Using existing transcript for: %s", episode["title"])

        if not transcript:
            download_audio(episode["audio_url"], audio_path)
            duration = get_audio_duration(audio_path)
            t0 = time.monotonic()
            transcript, transcribe_engine = transcribe(audio_path, settings)
            transcribed_seconds = round(time.monotonic() - t0, 1)

        if not transcript:
            return None

        t0 = time.monotonic()
        summary = summarize(
            transcript, episode["title"], feed_name,
            metrics_mod.configured_model(settings),
            settings.get("_summary_config", {}),
            max_chars=settings.get("max_transcript_chars",
                                   metrics_mod.DEFAULT_TRANSCRIPT_CHARS),
            max_context=settings.get("max_context_tokens",
                                    metrics_mod.DEFAULT_MAX_CONTEXT),
            num_predict=settings.get("summary_num_predict",
                                     metrics_mod.DEFAULT_NUM_PREDICT),
            chunk_chars=settings.get("summary_chunk_chars", SUMMARY_CHUNK_CHARS),
            chunk_overlap=settings.get("summary_chunk_overlap_chars",
                                      SUMMARY_CHUNK_OVERLAP),
            chunk_num_predict=settings.get("summary_chunk_num_predict",
                                          SUMMARY_CHUNK_NUM_PREDICT),
            provider=settings.get("llm_provider", "ollama"),
            base_url=settings.get("omlx_base_url", metrics_mod.OMLX_BASE_URL),
            api_key=settings.get("omlx_api_key"),
        )
        summarized_seconds = round(time.monotonic() - t0, 1)

        if not summary:
            log.error("Summarization failed; leaving episode retryable: %s", episode["title"])
            return None

        ep_date = parse_episode_date(episode.get("published", ""))
        podcast_slug = slugify(feed_name)
        ep_slug = slugify(episode["title"])
        output_path = TRANSCRIPTS_DIR / podcast_slug / f"{ep_date}--{ep_slug}.md"
        raw_path = raw_path_for_md(output_path)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(transcript, encoding="utf-8")
        write_markdown(output_path, feed_name, episode, duration, summary)

        record_episode_metrics(
            output_path, feed_name, podcast_slug, settings,
            transcribed_seconds, summarized_seconds,
            transcribe_engine=transcribe_engine,
        )
        completed = True
        return output_path

    finally:
        if not settings.get("keep_audio", False) and completed:
            audio_path.unlink(missing_ok=True)
            for f in TMP_DIR.glob(f"{slug}*"):
                f.unlink(missing_ok=True)


def update_transcript_index(config):
    """Incrementally update the FTS5 transcript index unless disabled in config."""
    if not config.get("search", {}).get("transcript_index", True):
        return
    try:
        # Local import keeps startup light; build is incremental (new raw files only).
        import transcript_search as tsearch_mod  # pylint: disable=import-outside-toplevel
        tsearch_mod.build_index()
    except Exception:
        log.exception("Transcript index update failed")


def process_feeds(feeds, settings, state, recovery=None, on_recovery_change=None):  # pylint: disable=too-many-branches
    """Check each feed and process new episodes. Returns count processed.

    State is saved per-episode so a run killed mid-sweep doesn't reprocess; the
    digest is rebuilt separately from metrics.jsonl rather than from this loop.
    """
    total_processed = 0
    recovery = recovery if recovery is not None else {"episode_failures": {}}
    failure_limit = settings.get("episode_failure_limit", 3)
    for feed_cfg in feeds:
        feed_name = feed_cfg["name"]
        feed_url = feed_cfg["url"]
        max_eps = settings.get("max_episodes_per_feed", 3)

        log.info("Checking feed: %s", feed_name)
        episodes = get_new_episodes(
            feed_url, feed_name, state, max_eps, settings, recovery, on_recovery_change,
        )

        if not episodes:
            log.info("No new episodes for: %s", feed_name)
            continue

        log.info("Found %d new episode(s) for: %s", len(episodes), feed_name)
        for ep in episodes:
            if release_episode_if_enclosure_changed(recovery, feed_url, ep):
                if on_recovery_change:
                    on_recovery_change(recovery)
            if is_episode_quarantined(recovery, feed_url, ep):
                log.warning("Quarantined after repeated failures; skipping: %s", ep["title"])
                continue
            log.info("Processing: %s", ep["title"])
            failure_reason = "episode did not produce a transcript and summary"
            try:
                result = process_episode(ep, feed_name, settings)
            except Exception as exc:
                log.exception("Crashed processing: %s", ep["title"])
                failure_reason = str(exc)
                result = None
            if result:
                state.setdefault(feed_url, []).append(ep["guid"])
                save_state(state)
                if clear_episode_failure(recovery, feed_url, ep) and on_recovery_change:
                    on_recovery_change(recovery)
                total_processed += 1
            else:
                log.error("Failed: %s", ep["title"])
                if _is_provider_failure(failure_reason):
                    log.warning("Provider failure (not marking episode): %s", failure_reason)
                    record_provider_outage(recovery, failure_reason, str(date.today()))
                else:
                    if record_episode_failure(recovery, feed_url, ep, failure_reason,
                                              limit=failure_limit):
                        log.error("Quarantined after %d failed runs: %s", failure_limit,
                                  ep["title"])
                if on_recovery_change:
                    on_recovery_change(recovery)
    return total_processed


def rebuild_digest(config, target_date):
    """Rebuild target_date's digest from metrics.jsonl. Idempotent. Returns episode count."""
    episodes = collect_digest_episodes(target_date)
    if episodes:
        generate_digest(episodes, config.get("digest", {}), target_date=target_date)
    return len(episodes)


def notify_enabled(value):
    """True only for an explicit true/1 config value (bool, int, or string).

    Stricter than plain truthiness on purpose: a quoted YAML ``"false"`` is a
    non-empty string and would otherwise read as enabled. Bool is checked before
    int because ``isinstance(True, int)`` is True in Python.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return False


def notify_complete(message):
    """Best-effort macOS desktop banner signalling the run finished.

    Lets the launchd job announce its own completion without depending on any
    watching process. Never raises: a banner failure (headless session, missing
    osascript, non-macOS host) must not affect the run's outcome — so it is a
    no-op off darwin and swallows everything else, like the digest/dashboard steps.
    """
    if sys.platform != "darwin":
        return
    try:
        script = f'display notification {json.dumps(message, ensure_ascii=False)} with title "podcast-ripper"'
        subprocess.run(
            ["osascript", "-e", script],
            check=False, timeout=10,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        log.warning("Completion notification failed", exc_info=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Podcast ripper: fetch → transcribe → summarize → markdown.")
    parser.add_argument(
        "--digest", nargs="?", const="", metavar="YYYY-MM-DD",
        help="Rebuild only the daily digest from metrics.jsonl (default: today) and exit. "
             "Use to recover a digest a crashed/interrupted run never wrote.",
    )
    args = parser.parse_args(argv)

    config = load_config()

    if args.digest is not None:
        target = date.fromisoformat(args.digest) if args.digest else date.today()
        count = rebuild_digest(config, target)
        log.info("Rebuilt digest for %s (%d episode(s)).", target, count)
        return 0

    feeds = config.get("feeds") or []
    settings = config.get("settings", {})
    settings["_summary_config"] = config.get("summary", {})
    settings["_metrics_config"] = config.get("metrics", {})

    if not feeds:
        log.warning("No feeds in config.yaml. Add some podcast RSS URLs and re-run.")
        return 0

    lock_file = None
    try:
        lock_file = _acquire_recovery_lock()
        recovery = load_recovery_state()
        ready, reason = preflight_summarizer(settings)
        if not ready:
            return pause_for_provider_outage(config, recovery, reason)

        if recovery.get("provider_outage", {}).get("active"):
            clear_provider_outage(recovery)
            save_recovery_state(recovery)

        state = load_state()
        TMP_DIR.mkdir(exist_ok=True)

        total_processed = process_feeds(feeds, settings, state, recovery, save_recovery_state)
    finally:
        if lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    # Build the digest from metrics (what was ripped today), not from this run's
    # in-memory list, so a sweep that gets interrupted still produces today's
    # digest on the next run — and a digest error never kills the rest of main().
    digest_count = None
    if config.get("digest", {}).get("enabled", False):
        try:
            digest_count = rebuild_digest(config, date.today())
        except Exception:
            log.exception("Digest generation failed")

    dashboard_config = config.get("dashboard", {})
    if dashboard_config.get("enabled", False):
        try:
            # Local import: dashboard pulls heavy deps (numpy, etc) only when used.
            import dashboard as dashboard_mod  # pylint: disable=import-outside-toplevel
            dashboard_mod.generate()
        except Exception:
            log.exception("Dashboard generation failed")

    update_transcript_index(config)

    log.info("Done. Processed %d episode(s).", total_processed)

    if notify_enabled(config.get("notify", {}).get("enabled", False)):
        summary = f"{total_processed} new episode(s)"
        if digest_count is not None:
            summary += f"; digest: {digest_count}"
        notify_complete(f"Run complete - {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
