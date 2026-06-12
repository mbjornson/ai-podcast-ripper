#!/usr/bin/env python3
# pylint: disable=line-too-long
"""Cross-episode entity extraction.

Extracts books, tools, people, companies, frameworks per episode via Ollama.
Caches by content_hash. Aggregation lives in dashboard.py at query time.

Usage:
    python entities.py --extract            # backfill all unindexed episodes
    python entities.py --extract --force    # re-extract all
    python entities.py --extract --podcast lennys-podcast --limit 3
    python entities.py --top books -k 20    # show most-mentioned books
"""

import argparse
import datetime
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

import metrics as metrics_mod

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
ENTITIES_PATH = BASE_DIR / "entities.jsonl"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

KINDS = ("books", "tools", "people", "companies", "frameworks")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("entities")


EXTRACT_PROMPT = """You are extracting structured entities from a podcast episode summary. Extract ONLY entities EXPLICITLY mentioned by name in the text. Do not infer. Do not generalize. When uncertain, omit.

Podcast: {podcast}
Episode: {episode}

Summary:
{summary}

Key Points:
{key_points}

Tools & Resources:
{tools}

Action Items:
{action_items}

Return a JSON object with these five keys, each a list (may be empty):

- books: each item {{"title": "<book title>", "author": "<author name or empty>"}}
- tools: each item {{"name": "<product name>", "category": "<one of: ai-model, ai-product, saas, framework, library, cli, hardware, other>"}}
- people: each item {{"name": "<person name>", "role": "<their role or affiliation, e.g. 'Anthropic co-founder'>"}}
- companies: each item {{"name": "<company name>", "sector": "<industry sector, e.g. 'AI', 'consulting', 'SaaS'>"}}
- frameworks: each item {{"name": "<framework or concept name>", "summary": "<one-sentence description>"}}

Rules:
- Use canonical product/company names ("Notion" not "notion.so", "Anthropic" not "anthropic.com")
- Do NOT include the podcast host or interviewer as people — they're context, not mentions
- "Tools" must be specific named products, NOT generic categories ("Claude" yes, "AI assistant" no)
- "Companies" must be named entities — skip if only a category is mentioned
- "Frameworks" are named methodologies/concepts (e.g. "Jobs to be Done", "Economic Turing Test"). Skip generic words.
- If a section is empty or doesn't apply, return [] for that key.
- Skip generic items like "books" without a specific title, "the AI" without a model name.

Respond with ONLY the JSON object, no prose, no commentary:
{{"books": [], "tools": [], "people": [], "companies": [], "frameworks": []}}"""


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_entities(parsed, model, timeout=120):
    """Single Ollama call. Returns entities dict (all kinds), or None on failure."""
    fm = parsed["frontmatter"]
    sections = parsed["sections"]
    prompt = EXTRACT_PROMPT.format(
        podcast=fm.get("podcast", "Unknown"),
        episode=fm.get("episode", "Unknown"),
        summary=sections.get("Summary", "")[:2000],
        key_points=sections.get("Key Points", "")[:2500],
        tools=sections.get("Tools & Resources", "")[:1500],
        action_items=sections.get("Action Items", "")[:1500],
    )
    raw = metrics_mod.ollama_generate(model, prompt, num_predict=2048, temperature=0.1,
                                       response_format="json", timeout=timeout)
    if not raw:
        return None
    return _parse_response(raw)


def _parse_response(raw):
    data = metrics_mod.parse_json_with_fallback(raw, pattern=r"\{.*\}")
    if not isinstance(data, dict):
        return None
    out = {kind: [] for kind in KINDS}
    for kind in KINDS:
        items = data.get(kind, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                out[kind].append(item)
            elif isinstance(item, str):
                # Tolerate flat-string responses
                out[kind].append({"name": item} if kind != "books" else {"title": item, "author": ""})
    return out


def build_row(path, parsed, entities):
    podcast_slug = path.parent.name
    fm = parsed["frontmatter"]
    return {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "date": str(fm.get("date") or ""),
        "podcast": fm.get("podcast") or podcast_slug.replace("-", " ").title(),
        "podcast_slug": podcast_slug,
        "episode_title": fm.get("episode") or path.stem,
        "path": str(path.relative_to(BASE_DIR)),
        "content_hash": metrics_mod.content_hash(parsed),
        "entities": entities,
        "schema_version": 1,
    }


def iter_episodes():
    for path in sorted(TRANSCRIPTS_DIR.rglob("*.md")):
        if "digests" in path.parts or ".obsidian" in path.parts:
            continue
        yield path


def load_existing():
    """Return {(path, content_hash): row} of already-extracted episodes."""
    existing = {}
    for row in metrics_mod.iter_jsonl(ENTITIES_PATH):
        key = (row.get("path", ""), row.get("content_hash", ""))
        existing[key] = row
    return existing


def cmd_extract(model, force=False, limit=0, podcast_filter=""):
    existing = load_existing()
    log.info("Loaded %d existing entity rows", len(existing))

    episodes = list(iter_episodes())
    if podcast_filter:
        episodes = [p for p in episodes if p.parent.name == podcast_filter]
    total = len(episodes)
    log.info("Found %d candidate episodes", total)

    processed = skipped = 0
    for i, path in enumerate(episodes, 1):
        if limit and processed >= limit:
            log.info("Hit limit: %d", limit)
            break
        parsed = metrics_mod.parse_episode(path)
        if parsed is None or not parsed["sections"].get("Summary"):
            continue
        chash = metrics_mod.content_hash(parsed)
        rel = str(path.relative_to(BASE_DIR))
        if (rel, chash) in existing and not force:
            skipped += 1
            continue

        log.info("[%d/%d] Extracting: %s", i, total, path.name)
        entities = extract_entities(parsed, model)
        if entities is None:
            log.warning("  Skipped (extraction failed)")
            continue
        row = build_row(path, parsed, entities)
        with open(ENTITIES_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        processed += 1
        if processed % 25 == 0:
            log.info("Progress: %d processed, %d skipped", processed, skipped)

    log.info("Done. Processed=%d Skipped=%d", processed, skipped)


def _norm_key(s):
    """Normalize an entity name for matching."""
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s\-]", "", s)
    return s


def _display_name(item, kind):
    if kind == "books":
        return item.get("title") or ""
    return item.get("name") or ""


def load_all_rows():
    """Latest row per (path) — last write wins."""
    by_path = {}
    for row in metrics_mod.iter_jsonl(ENTITIES_PATH):
        by_path[row.get("path", "")] = row
    return list(by_path.values())


def aggregate(kind, rows=None, podcast_slug=None):
    """Return list of {key, name, count, episodes:[{path,podcast,episode_title,date,extra}]} sorted by count desc.

    `extra` carries the item-level fields for that kind (author, role, sector, ...).
    """
    if rows is None:
        rows = load_all_rows()
    counts = Counter()
    display = {}  # key -> most-common display
    episodes = defaultdict(list)
    extras = defaultdict(Counter)

    for row in rows:
        if podcast_slug and row.get("podcast_slug") != podcast_slug:
            continue
        for item in (row.get("entities") or {}).get(kind, []) or []:
            name = _display_name(item, kind)
            key = _norm_key(name)
            if not key:
                continue
            counts[key] += 1
            display.setdefault(key, Counter())[name] += 1
            ep_info = {
                "path": row.get("path"),
                "podcast": row.get("podcast"),
                "podcast_slug": row.get("podcast_slug"),
                "episode_title": row.get("episode_title"),
                "date": row.get("date"),
            }
            if kind == "books":
                ep_info["author"] = item.get("author", "")
            elif kind == "tools":
                ep_info["category"] = item.get("category", "")
            elif kind == "people":
                ep_info["role"] = item.get("role", "")
            elif kind == "companies":
                ep_info["sector"] = item.get("sector", "")
            elif kind == "frameworks":
                ep_info["summary"] = item.get("summary", "")
            episodes[key].append(ep_info)
            extras[key][_extra_for(item, kind)] += 1

    results = []
    for key, count in counts.most_common():
        canonical = display[key].most_common(1)[0][0]
        extra_text = extras[key].most_common(1)[0][0] if extras[key] else ""
        results.append({
            "key": key,
            "name": canonical,
            "count": count,
            "extra": extra_text,
            "episodes": episodes[key],
        })
    return results


def _extra_for(item, kind):
    if kind == "books":
        return item.get("author", "")
    if kind == "tools":
        return item.get("category", "")
    if kind == "people":
        return item.get("role", "")
    if kind == "companies":
        return item.get("sector", "")
    if kind == "frameworks":
        return item.get("summary", "")
    return ""


def cmd_top(kind, k=20, podcast_slug=None):
    all_results = aggregate(kind, podcast_slug=podcast_slug)
    results = all_results[:k]
    print(f"\nTop {k} {kind} ({len(all_results)} unique total)")
    print("-" * 60)
    for r in results:
        extra = f" — {r['extra']}" if r["extra"] else ""
        print(f"  {r['count']:>3}  {r['name']}{extra}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true", help="Run extraction backfill")
    parser.add_argument("--force", action="store_true", help="Re-extract even if cached")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--podcast", default="", help="Filter to podcast slug")
    parser.add_argument("--top", choices=KINDS, help="Show top entities for a kind")
    parser.add_argument("-k", type=int, default=20)
    args = parser.parse_args()

    config = load_config()
    metrics_cfg = config.get("metrics", {})
    model = config.get("entities", {}).get("model") or metrics_cfg.get("judge_model") or "llama3"

    if args.extract:
        cmd_extract(model, force=args.force, limit=args.limit, podcast_filter=args.podcast)
    elif args.top:
        cmd_top(args.top, k=args.k, podcast_slug=args.podcast or None)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
