# pylint: disable=line-too-long
"""Episode metrics: parse markdown, compute heuristics, judge via LLM."""

import datetime as _dt
import hashlib
import json
import logging
import math
import re
import urllib.request
import uuid
from pathlib import Path

import yaml

OLLAMA_URL = "http://localhost:11434/api/generate"
OMLX_BASE_URL = "http://127.0.0.1:10000/v1"
SCHEMA_VERSION = 2
BASE_DIR = Path(__file__).parent

log = logging.getLogger("metrics")


def configured_model(settings):
    """Return the model configured for the selected local provider."""
    provider = settings.get("llm_provider", "ollama")
    model_key = "omlx_model" if provider == "omlx" else "ollama_model"
    model = settings.get(model_key)
    if not model:
        raise ValueError(f"Missing required setting: {model_key}")
    return model

LOW_SIGNAL_RE = re.compile(
    r"low signal|mostly entertainment|no clear action|limited actionable",
    re.IGNORECASE,
)

SECTION_HEADINGS = ["Summary", "Key Points", "Tools & Resources", "Quotable", "Action Items"]
GENERIC_RESOURCE_NAMES = frozenset({
    "concept", "concepts", "function", "functions", "framework", "frameworks",
    "method", "methods", "process", "processes", "strategy", "strategies",
    "timeline", "timelines",
})


def parse_frontmatter(text):
    """Extract YAML frontmatter block. Returns (data_dict, body_str)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    try:
        data = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        data = {}
    return data, text[end + 5:]


def extract_sections(markdown_text, section_headings=None):
    """Split markdown into {heading: body} for given H2 headings. Skip Full Transcript."""
    if section_headings is None:
        section_headings = SECTION_HEADINGS
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


def _resource_name(item):
    """Extract the likely named resource from a rendered bullet."""
    item = re.sub(r"[*_`]", "", item).strip()
    link = re.match(r"\[([^]]+)\]\([^)]*\)", item)
    if link:
        item = link.group(1)
    item = re.split(r"\s+[—–-]\s+", item, maxsplit=1)[0]
    return re.split(r"\s*[:(]\s*", item, maxsplit=1)[0].strip()


def _resource_is_mentioned(item, transcript):
    """Return whether a resource bullet has textual evidence in the transcript."""
    name = _resource_name(item)
    if name.casefold() in GENERIC_RESOURCE_NAMES:
        return False
    item_lower = item.casefold()
    transcript_lower = transcript.casefold()
    if item_lower in transcript_lower:
        return True
    if name.casefold() in transcript_lower:
        return True
    if ":" in item:
        return any(part.strip().casefold() in transcript_lower
                   for part in item.split(":", 1)[1].split(",") if part.strip())
    return False


def validate_tools_and_resources(summary, transcript):
    """Remove unsupported or generic bullets from the resource section."""
    pattern = re.compile(r"(?ms)(^## Tools & Resources\n)(.*?)(?=^## |\Z)")
    match = pattern.search(summary or "")
    if not match:
        return summary

    kept = []
    for line in match.group(2).strip().splitlines():
        if not line.startswith("- ") or line == "- None identified.":
            kept.append(line)
            continue
        item = line[2:].strip()
        if _resource_is_mentioned(item, transcript):
            kept.append(line)
    replacement = match.group(1) + ("\n".join(kept) or "- None identified.") + "\n"
    return summary[:match.start()] + replacement + summary[match.end():]


def extract_transcript(md_path):
    """Read the episode's raw transcript from the raw/ corpus (sibling of the .md)."""
    raw = BASE_DIR / "raw" / md_path.parent.name / (md_path.stem + ".txt")
    try:
        return raw.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def parse_duration_to_seconds(duration_str):
    """Parse 'H:MM:SS' or 'MM:SS' to int seconds. Returns 0 on failure."""
    if not duration_str or not isinstance(duration_str, str):
        return 0
    parts = duration_str.strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 1:
        return nums[0]
    return 0


def parse_episode(md_path):
    """Read a transcript markdown file. Returns parsed dict or None on failure."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return None

    frontmatter, body = parse_frontmatter(text)
    sections = extract_sections(body)
    transcript = extract_transcript(md_path)

    return {
        "path": md_path,
        "frontmatter": frontmatter,
        "sections": sections,
        "transcript": transcript,
        "body": body,
    }


def count_list_items(section_body, prefix):
    if not section_body:
        return 0
    return sum(1 for line in section_body.splitlines() if line.lstrip().startswith(prefix))


def compute_heuristics(parsed):
    """Pure-function heuristic metrics from parsed episode."""
    fm = parsed["frontmatter"]
    sections = parsed["sections"]
    transcript = parsed["transcript"]

    summary = sections.get("Summary", "")
    key_points = sections.get("Key Points", "")
    tools = sections.get("Tools & Resources", "")
    quotable = sections.get("Quotable", "")
    action_items = sections.get("Action Items", "")

    audio_seconds = parse_duration_to_seconds(fm.get("duration", ""))
    audio_minutes = audio_seconds / 60.0 if audio_seconds else 0.0

    action_items_count = count_list_items(action_items, "- [ ]") + count_list_items(action_items, "- [x]")
    key_points_count = count_list_items(key_points, "- ")
    tools_count = count_list_items(tools, "- ")
    quotables_count = count_list_items(quotable, "> ")

    signal_total = action_items_count + key_points_count + tools_count
    signal_density = (signal_total / audio_minutes) if audio_minutes else 0.0

    low_signal_flag = bool(LOW_SIGNAL_RE.search(summary)) if summary else False

    return {
        "podcast": fm.get("podcast", ""),
        "episode_title": fm.get("episode", ""),
        "date": str(fm.get("date", "")),
        "audio_duration_seconds": audio_seconds,
        "transcript_chars": len(transcript),
        "summary_chars": len(summary),
        "action_items_count": action_items_count,
        "key_points_count": key_points_count,
        "tools_count": tools_count,
        "quotables_count": quotables_count,
        "low_signal_flag": low_signal_flag,
        "signal_density": round(signal_density, 4),
    }


def content_hash(parsed):
    """Stable hash of summary content. Whitespace-normalized."""
    parts = []
    for heading in SECTION_HEADINGS:
        body = parsed["sections"].get(heading, "")
        parts.append(re.sub(r"\s+", " ", body).strip())
    blob = "||".join(parts)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


JUDGE_PROMPT = """You are a harsh editor. Most podcast episodes are forgettable. Your job is to score this one HONESTLY using the full 1-10 range. Refuse to cluster scores around 6-8 — that's lazy. Use 1-4 for low-signal content. Use 9-10 only for episodes you'd forward to a peer.

CALIBRATION EXAMPLES:

Example A — actionability=2, signal_density=3:
History podcast about Roman general Crassus's military campaigns. Interesting narrative but zero actionable insights for a modern operator. Pure entertainment.

Example B — actionability=5, signal_density=5:
Self-help interview with generic advice ("be curious", "embrace failure"). One specific framework mentioned but otherwise mainstream. Decent but skippable.

Example C — actionability=8, signal_density=8:
Operator interview naming 4 specific tools, a hiring framework with concrete criteria, and a pricing model with example numbers. Listener could implement 3+ things this week.

Example D — actionability=10, signal_density=9:
Founder breakdown of EXACTLY how they 10x'd a metric: named tactics, exact numbers, replicable playbook. Would forward to a peer immediately.

NOW SCORE THIS:

Podcast: {podcast}
Episode: {episode}

Summary:
{summary}

Key Points:
{key_points}

Action Items:
{action_items}

Required reasoning steps (do silently, do not output):
1. Which example (A/B/C/D) does this most resemble?
2. What specifically would have to change to bump the score by 2?
3. Is the actionability mostly real (specific tools/numbers/playbooks) or generic ("be curious")?

Then output ONLY this JSON, nothing else:
{{"actionability": <1-10>, "signal_density": <1-10>, "would_recommend": <true only if actionability >= 7>, "rationale": "<one sentence — name the specific tactic/tool OR the specific weakness>"}}"""


def judge_episode(parsed, model, timeout=120, provider="ollama",
                  base_url=OMLX_BASE_URL, api_key=None):
    """Single local-model call. Returns judge dict or None on failure."""
    fm = parsed["frontmatter"]
    sections = parsed["sections"]

    prompt = JUDGE_PROMPT.format(
        podcast=fm.get("podcast", "Unknown"),
        episode=fm.get("episode", "Unknown"),
        summary=sections.get("Summary", "")[:2000],
        key_points=sections.get("Key Points", "")[:2000],
        action_items=sections.get("Action Items", "")[:1500],
    )
    raw = generate_text(
        model, prompt, provider=provider, num_predict=1024, temperature=0.2,
        response_format="json", timeout=timeout, base_url=base_url,
        api_key=api_key,
    )
    return parse_judge_response(raw) if raw else None


# Transcript budget. The old hardcoded 12000 fed the model ~21% of the corpus;
# 91% of episodes were cut. 0 (or None) disables the cap entirely.
DEFAULT_TRANSCRIPT_CHARS = 240000

# Context sizing. Ollama allocates KV cache to num_ctx, so a static ceiling would
# reserve the same memory for a 3-minute episode as a 3-hour one. Size per call.
CHARS_PER_TOKEN = 3.0      # conservative: under-estimating this over-estimates tokens
CONTEXT_STEP = 8192        # round up in steps so near-identical prompts reuse a load
MIN_CONTEXT = 8192
DEFAULT_MAX_CONTEXT = 131072

# Output budget. Reasoning models (qwen3.8) spend this on thinking tokens
# before writing anything: at 2048 they truncated mid-summary and dropped
# whole sections. Non-reasoning models never reach the ceiling either way.
DEFAULT_NUM_PREDICT = 4096


def context_window_for(prompt, num_predict, ceiling=DEFAULT_MAX_CONTEXT,
                       minimum=MIN_CONTEXT):
    """num_ctx big enough for prompt + generated output, stepped and clamped."""
    tokens = (len(prompt) / CHARS_PER_TOKEN + num_predict) * 1.1  # 10% headroom
    stepped = math.ceil(tokens / CONTEXT_STEP) * CONTEXT_STEP
    return max(minimum, min(stepped, ceiling))


def build_summary_prompt(summary_config, podcast_name, episode_title, transcript,
                         max_chars=DEFAULT_TRANSCRIPT_CHARS):
    """Construct the user-facing LLM summarization prompt."""
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
        if heading == "Tools & Resources":
            instruction += (
                "\nInclude only named resources explicitly mentioned in the transcript. "
                "Do not include generic concepts, labels, or incidental nouns. "
                "If none are mentioned, write '- None identified.'"
            )
        if fmt == "bullets":
            section_lines.append(f"## {heading}\n- [{instruction}]")
        elif fmt == "checklist":
            section_lines.append(f"## {heading}\n- [ ] [{instruction}]")
        elif fmt == "quotes":
            section_lines.append(f"## {heading}\n> [{instruction}]")
        else:
            section_lines.append(f"## {heading}\n[{instruction}]")
    return (
        f"{context}\n\n"
        f"Podcast: {podcast_name}\n"
        f"Episode: {episode_title}\n\n"
        f"Provide your response in exactly this format:\n\n"
        f"{chr(10).join(section_lines)}\n\n"
        f"Focus on actionable signal over generic advice. Skip pleasantries and filler. "
        f"If the episode is mostly entertainment with low signal, say so.\n\n"
        f"Transcript:\n{transcript[:max_chars] if max_chars else transcript}"
    )


def ollama_generate(model, prompt, num_predict=2048, temperature=0.3,
                    response_format=None, timeout=300, num_ctx=None):
    """POST to Ollama /api/generate. Returns response text, or None on failure."""
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }
    if num_ctx:
        body["options"]["num_ctx"] = num_ctx
    if response_format:
        body["format"] = response_format
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")
    except Exception as e:
        log.warning("Ollama call failed (%s): %s", model, e)
        return None


def omlx_generate(model, prompt, num_predict=2048, temperature=0.3,
                  response_format=None, timeout=300,
                  base_url=OMLX_BASE_URL, api_key=None, num_ctx=None,
                  chat_template_kwargs=None):
    """POST to oMLX's OpenAI-compatible chat API. Returns response text."""
    del num_ctx  # oMLX sizes context from the model/server configuration.
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": num_predict,
        "temperature": temperature,
    }
    if response_format:
        body["response_format"] = {
            "type": "json_object" if response_format == "json" else response_format,
        }
    if chat_template_kwargs:
        body["chat_template_kwargs"] = chat_template_kwargs
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            choices = result.get("choices") or []
            if not choices:
                return ""
            return (choices[0].get("message") or {}).get("content", "") or ""
    except Exception as e:
        log.warning("oMLX call failed (%s): %s", model, e)
        return None


DEFAULT_TRANSCRIBE_TIMEOUT = 1800


def omlx_transcribe(audio_path, model, base_url=OMLX_BASE_URL, api_key=None,
                    timeout=DEFAULT_TRANSCRIBE_TIMEOUT, language=None):
    """POST audio to oMLX's OpenAI-compatible transcription endpoint (GPU).

    Returns the transcript text, or None on failure so callers can fall back.
    """
    boundary = uuid.uuid4().hex
    fields = {"model": model}
    if language:
        fields["language"] = language

    body = bytearray()
    for name, value in fields.items():
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    # Whole file in memory: a 4h episode is ~200MB, and urllib needs a bytes body.
    body += Path(audio_path).read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    url = base_url.rstrip("/") + "/audio/transcriptions"
    req = urllib.request.Request(
        url, data=bytes(body), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = (json.loads(resp.read()).get("text") or "").strip()
    except Exception as e:
        log.warning("oMLX transcription failed (%s): %s", model, e)
        return None
    if not text:
        log.warning("oMLX transcription returned empty text (%s)", model)
        return None
    return text


def generate_text(model, prompt, provider="ollama", **kwargs):
    """Generate text through the configured local model provider."""
    if provider == "omlx":
        return omlx_generate(model, prompt, **kwargs)
    if provider == "ollama":
        kwargs.pop("base_url", None)
        kwargs.pop("api_key", None)
        kwargs.pop("chat_template_kwargs", None)
        return ollama_generate(model, prompt, **kwargs)
    raise ValueError(f"Unsupported model provider: {provider}")


def parse_json_with_fallback(raw, pattern=r"\{.*?\}"):
    """Parse JSON from a model response. Tolerates leading or trailing prose."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(pattern, raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def parse_judge_response(raw):
    """Extract JSON object from judge response. Tolerates surrounding text."""
    data = parse_json_with_fallback(raw)
    if not isinstance(data, dict):
        return None
    try:
        return {
            "actionability": int(data.get("actionability", 0)),
            "signal_density": int(data.get("signal_density", 0)),
            "would_recommend": bool(data.get("would_recommend", False)),
            "rationale": str(data.get("rationale", ""))[:500],
        }
    except (TypeError, ValueError):
        return None


def build_metrics_row(parsed, rel_path, podcast_slug, fallback_podcast_name,
                       judge_result, transcribed_seconds=None, summarized_seconds=None,
                       transcribe_engine=None):
    """Assemble a metrics.jsonl row from parsed episode + optional judge + timing."""
    h = compute_heuristics(parsed)
    fm = parsed["frontmatter"]
    return {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "date": h["date"],
        "podcast": fm.get("podcast") or fallback_podcast_name,
        "podcast_slug": podcast_slug,
        "episode_title": h["episode_title"],
        "path": rel_path,
        "audio_duration_seconds": h["audio_duration_seconds"],
        "transcript_chars": h["transcript_chars"],
        "summary_chars": h["summary_chars"],
        "action_items_count": h["action_items_count"],
        "key_points_count": h["key_points_count"],
        "tools_count": h["tools_count"],
        "quotables_count": h["quotables_count"],
        "low_signal_flag": h["low_signal_flag"],
        "signal_density": h["signal_density"],
        "transcribed_seconds": transcribed_seconds,
        "transcribe_engine": transcribe_engine,
        "summarized_seconds": summarized_seconds,
        "judge": judge_result,
        "content_hash": content_hash(parsed),
        "schema_version": SCHEMA_VERSION,
    }


def append_metrics_row(jsonl_path, row):
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


RATING_TO_SCORE = {-2: 2, -1: 4, 1: 8, 2: 10}


def iter_jsonl(jsonl_path):
    """Yield valid JSON objects from a JSONL file. Skip blank or malformed lines."""
    if not Path(jsonl_path).exists():
        return
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_ratings(jsonl_path):
    """Load ratings.jsonl into {path: rating_int}. Last write per path wins."""
    ratings = {}
    for row in iter_jsonl(jsonl_path):
        path = row.get("path", "")
        rating = row.get("rating")
        if not path or rating is None:
            continue
        if rating == 0:
            ratings.pop(path, None)  # 0 = clear
        else:
            ratings[path] = int(rating)
    return ratings


def append_rating(jsonl_path, path, rating):
    """Append a rating row. Use rating=0 to clear."""
    row = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "path": path,
        "rating": int(rating),
    }
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def compute_podcast_bias(rows, ratings):
    """Per-podcast (mean judge_actionability - target_score) for rated episodes.

    Returns {podcast_slug: (bias, rated_count)}. Bias > 0 means judge scores high relative to user.
    """
    by_slug = {}
    for r in rows:
        slug = r.get("podcast_slug") or ""
        path = r.get("path") or ""
        judge = r.get("judge") or {}
        if not slug or path not in ratings or "actionability" not in judge:
            continue
        target = RATING_TO_SCORE.get(ratings[path])
        if target is None:
            continue
        by_slug.setdefault(slug, []).append(judge["actionability"] - target)

    out = {}
    for slug, deltas in by_slug.items():
        out[slug] = (sum(deltas) / len(deltas), len(deltas))
    return out


def load_existing_metrics(jsonl_path):
    """Load existing rows keyed by (path, content_hash). Returns dict."""
    existing = {}
    for row in iter_jsonl(jsonl_path):
        key = (row.get("path", ""), row.get("content_hash", ""))
        existing[key] = row
    return existing
