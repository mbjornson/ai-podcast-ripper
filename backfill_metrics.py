#!/usr/bin/env python3
"""Backfill metrics.jsonl by walking transcripts/ and computing per-episode metrics.

Idempotent: skips episodes already judged with matching content hash.
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

import metrics

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
METRICS_PATH = BASE_DIR / "metrics.jsonl"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("backfill")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def slugify_podcast(podcast_name, parent_dir_name):
    """Use parent dir as the slug — it's already correctly slugified."""
    return parent_dir_name


def find_episodes(transcripts_dir):
    """Yield all episode .md files, excluding digests."""
    for path in sorted(transcripts_dir.rglob("*.md")):
        if "digests" in path.parts:
            continue
        if ".obsidian" in path.parts:
            continue
        yield path


def build_row(path, parsed, judge_result):
    podcast_slug = path.parent.name
    return metrics.build_metrics_row(
        parsed,
        rel_path=str(path.relative_to(BASE_DIR)),
        podcast_slug=podcast_slug,
        fallback_podcast_name=podcast_slug.replace("-", " ").title(),
        judge_result=judge_result,
    )


def judge_config(config):
    """Resolve the configured provider, model, and connection settings."""
    settings = config["settings"]
    metrics_cfg = config.get("metrics", {})
    return (
        metrics_cfg.get("judge_model") or metrics.configured_model(settings),
        settings.get("llm_provider", "ollama"),
        settings.get("omlx_base_url", metrics.OMLX_BASE_URL),
        settings.get("omlx_api_key"),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM judging (fast pass)")
    parser.add_argument("--limit", type=int, default=0, help="Cap episodes processed (0=all)")
    parser.add_argument("--podcast", default="", help="Only process this podcast slug")
    parser.add_argument("--force", action="store_true", help="Re-judge episodes even if already judged")
    args = parser.parse_args()

    config = load_config()
    judge_model, provider, base_url, api_key = judge_config(config)

    existing = metrics.load_existing_metrics(METRICS_PATH)
    log.info("Loaded %d existing metric rows", len(existing))

    episodes = list(find_episodes(TRANSCRIPTS_DIR))
    if args.podcast:
        episodes = [p for p in episodes if p.parent.name == args.podcast]
    total = len(episodes)
    log.info("Found %d candidate episodes", total)

    processed = 0
    skipped = 0
    judged = 0
    for i, path in enumerate(episodes, 1):
        if args.limit and processed >= args.limit:
            log.info("Hit limit: %d", args.limit)
            break

        parsed = metrics.parse_episode(path)
        if parsed is None:
            log.warning("[%d/%d] Could not parse: %s", i, total, path)
            continue

        rel_path = str(path.relative_to(BASE_DIR))
        chash = metrics.content_hash(parsed)
        key = (rel_path, chash)

        if key in existing and not args.force:
            existing_row = existing[key]
            # If we already judged, skip entirely
            if existing_row.get("judge") or args.no_judge:
                skipped += 1
                continue

        judge_result = None
        if not args.no_judge:
            if not parsed["sections"].get("Summary"):
                log.info("[%d/%d] Skip judge (no summary): %s", i, total, path.name)
            else:
                log.info("[%d/%d] Judging: %s", i, total, path.name)
                judge_result = metrics.judge_episode(
                    parsed, judge_model, provider=provider, base_url=base_url,
                    api_key=api_key,
                )
                if judge_result:
                    judged += 1

        row = build_row(path, parsed, judge_result)
        metrics.append_metrics_row(METRICS_PATH, row)
        processed += 1

        if processed % 25 == 0:
            log.info("Progress: %d processed, %d judged, %d skipped", processed, judged, skipped)

    log.info("Done. Processed=%d Judged=%d Skipped=%d", processed, judged, skipped)


if __name__ == "__main__":
    main()
