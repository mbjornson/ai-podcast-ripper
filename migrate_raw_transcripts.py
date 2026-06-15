#!/usr/bin/env python3
"""One-time migration: move embedded `## Full Transcript` sections out of episode
markdown into the plain-text raw/ corpus.

Idempotent and resume-safe: the raw .txt is written AND verified byte-for-byte
before the markdown section is stripped, so an interrupted run can be re-run
without data loss. transcripts/ is gitignored, so this verification is the only
safety net — recommend `cp -r transcripts transcripts.bak` before the first run.
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
RAW_DIR = BASE_DIR / "raw"

MARKER = "## Full Transcript"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("migrate-raw")


def raw_path_for(md_path, raw_dir):
    """Map transcripts/<slug>/<stem>.md -> <raw_dir>/<slug>/<stem>.txt."""
    return raw_dir / md_path.parent.name / (md_path.stem + ".txt")


def extract_section(md_text):
    """Return (marker_index, transcript_body) or (None, None) if absent."""
    idx = md_text.find(MARKER)
    if idx < 0:
        return None, None
    return idx, md_text[idx + len(MARKER):].strip()


def _write_and_verify(raw_path, body):
    """Write body to raw_path and confirm it round-trips. Remove + fail on mismatch."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(body, encoding="utf-8")
    if raw_path.read_text(encoding="utf-8") == body:
        return True
    raw_path.unlink(missing_ok=True)
    return False


def migrate_file(md_path, raw_dir, dry_run=False):
    """Migrate one episode markdown. Returns a status string."""
    md_text = md_path.read_text(encoding="utf-8")
    idx, body = extract_section(md_text)
    if idx is None:
        return "skipped_no_section"
    if not body:
        return "empty_transcript"

    raw_path = raw_path_for(md_path, raw_dir)
    if dry_run:
        return "would_migrate"

    already = raw_path.exists() and raw_path.read_text(encoding="utf-8") == body
    if not already and not _write_and_verify(raw_path, body):
        log.error("Verify failed, leaving markdown intact: %s", md_path)
        return "verify_failed"

    md_path.write_text(md_text[:idx].rstrip() + "\n", encoding="utf-8")
    return "migrated"


def find_episode_files(transcripts_dir):
    """Yield non-digest episode markdown files."""
    for path in sorted(transcripts_dir.rglob("*.md")):
        if "digests" in path.parts:
            continue
        yield path


def run(transcripts_dir, raw_dir, dry_run=False, limit=0, podcast=None):
    """Migrate every episode under transcripts_dir. Returns a Counter of statuses."""
    counts = Counter()
    processed = 0
    for md_path in find_episode_files(transcripts_dir):
        if podcast and md_path.parent.name != podcast:
            continue
        counts[migrate_file(md_path, raw_dir, dry_run=dry_run)] += 1
        processed += 1
        if processed % 100 == 0:
            log.info("... %d processed", processed)
        if limit and processed >= limit:
            break
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Move Full Transcript sections into raw/.")
    parser.add_argument("--dry-run", action="store_true", help="report actions without writing")
    parser.add_argument("--limit", type=int, default=0, help="stop after N files (0 = all)")
    parser.add_argument("--podcast", default=None, help="only migrate this podcast slug")
    args = parser.parse_args(argv)

    counts = run(TRANSCRIPTS_DIR, RAW_DIR, dry_run=args.dry_run,
                 limit=args.limit, podcast=args.podcast)
    log.info("Done: %s", dict(counts))
    return counts


if __name__ == "__main__":
    main()
