#!/usr/bin/env python3
"""Semantic search across all podcast episodes.

Index: chunks each episode's structured summary by section/bullet, embeds with
BGE small (384-dim), stores embeddings as a flat numpy array. Query: cosine
similarity, top-k.

Usage:
    python search.py index                       # build/rebuild full index
    python search.py "pricing strategies for AI" # query CLI
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import numpy as np

import metrics as metrics_mod

BASE_DIR = Path(__file__).parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
INDEX_DIR = BASE_DIR / ".search_index"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"
META_PATH = INDEX_DIR / "meta.json"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

CHUNK_SECTIONS_BULLET = ("Key Points", "Tools & Resources", "Action Items")
CHUNK_SECTIONS_BLOCK = ("Summary", "Quotable")
MIN_CHUNK_LEN = 30
MAX_CHUNK_CHARS = 1500

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("search")

_MODEL_CACHE = {}


def get_model():
    if "model" not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer  # pylint: disable=import-outside-toplevel
        log.info("Loading embedding model: %s", MODEL_NAME)
        _MODEL_CACHE["model"] = SentenceTransformer(MODEL_NAME)
    return _MODEL_CACHE["model"]


def _clean_bullet(line):
    line = line.strip()
    line = re.sub(r"^- \[[ x]\]\s*", "", line)  # checklist marker
    line = re.sub(r"^[-*>]\s+", "", line)        # bullet/quote marker
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line) # bold
    return line.strip()


def chunk_episode(parsed, ep_meta):
    """Return list of {text, section, ep_meta...} chunks for one episode."""
    chunks = []
    sections = parsed["sections"]

    for sec in CHUNK_SECTIONS_BULLET:
        body = sections.get(sec, "")
        if not body:
            continue
        for line in body.splitlines():
            text = _clean_bullet(line)
            if len(text) < MIN_CHUNK_LEN:
                continue
            chunks.append({
                "text": text[:MAX_CHUNK_CHARS],
                "section": sec,
                **ep_meta,
            })

    for sec in CHUNK_SECTIONS_BLOCK:
        body = sections.get(sec, "").strip()
        if len(body) < MIN_CHUNK_LEN:
            continue
        # Keep block sections whole (capped); they're short prose.
        chunks.append({
            "text": body[:MAX_CHUNK_CHARS],
            "section": sec,
            **ep_meta,
        })

    return chunks


def _ep_meta_from_path(path):
    """Lightweight episode metadata for chunks."""
    return {
        "path": str(path.relative_to(BASE_DIR)),
        "podcast_slug": path.parent.name,
    }


def iter_episodes():
    for path in sorted(TRANSCRIPTS_DIR.rglob("*.md")):
        if "digests" in path.parts or ".obsidian" in path.parts:
            continue
        yield path


def build_index(force=False, limit=0):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if EMBEDDINGS_PATH.exists() and not force:
        log.info("Index exists. Use --force to rebuild.")
        return

    model = get_model()

    all_chunks = []
    episodes = list(iter_episodes())
    if limit:
        episodes = episodes[:limit]
    log.info("Chunking %d episodes...", len(episodes))

    for i, path in enumerate(episodes, 1):
        parsed = metrics_mod.parse_episode(path)
        if parsed is None:
            continue
        ep_meta = _ep_meta_from_path(path)
        ep_meta["podcast"] = parsed["frontmatter"].get("podcast") or ep_meta["podcast_slug"]
        ep_meta["episode_title"] = parsed["frontmatter"].get("episode") or path.stem
        ep_meta["date"] = str(parsed["frontmatter"].get("date") or "")
        all_chunks.extend(chunk_episode(parsed, ep_meta))
        if i % 200 == 0:
            log.info("[%d/%d] chunked, %d chunks so far", i, len(episodes), len(all_chunks))

    log.info("Total chunks: %d. Embedding...", len(all_chunks))
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    np.save(EMBEDDINGS_PATH, embeddings)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")
    META_PATH.write_text(json.dumps({
        "model": MODEL_NAME,
        "dim": EMBED_DIM,
        "n_chunks": len(all_chunks),
        "n_episodes": len(episodes),
    }, indent=2))
    log.info("Index built: %d chunks, %s", len(all_chunks), EMBEDDINGS_PATH)


_INDEX_CACHE = {}


def _load_index():
    if "data" not in _INDEX_CACHE:
        if not EMBEDDINGS_PATH.exists():
            raise FileNotFoundError(f"No index at {EMBEDDINGS_PATH}. Run: python search.py --index")
        embeddings = np.load(EMBEDDINGS_PATH)
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f]
        _INDEX_CACHE["data"] = (embeddings, chunks)
    return _INDEX_CACHE["data"]


def search(query, k=20, podcast_slug=None):
    """Return top-k chunks for a query. Optional podcast_slug filter."""
    if not query.strip():
        return []
    embeddings, chunks = _load_index()
    model = get_model()
    q_vec = model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)[0]

    scores = embeddings @ q_vec  # cosine since both normalized
    if podcast_slug:
        mask = np.array([c.get("podcast_slug") == podcast_slug for c in chunks])
        scores = np.where(mask, scores, -np.inf)

    top_idx = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
    top_idx = top_idx[np.argsort(-scores[top_idx])]

    results = []
    seen_episodes = set()
    for idx in top_idx:
        score = float(scores[idx])
        if score == -np.inf:
            continue
        c = chunks[int(idx)]
        # Dedupe: at most 2 chunks per episode for top-line results
        ep_key = c.get("path", "")
        ep_count = sum(1 for r in results if r.get("path") == ep_key)
        if ep_count >= 2:
            continue
        results.append({**c, "score": round(score, 4)})
        seen_episodes.add(ep_key)
        if len(results) >= k:
            break
    return results


def cli_search(query, k=10):
    results = search(query, k=k)
    if not results:
        print("No results.")
        return
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['score']:.3f}  {r['podcast']} — {r['episode_title'][:80]}")
        print(f"    section: {r['section']}  date: {r['date']}")
        print(f"    {r['text'][:200]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", action="store_true", help="Build/rebuild index")
    parser.add_argument("--force", action="store_true", help="Force rebuild")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("-k", type=int, default=10, help="Top-k results")
    parser.add_argument("query", nargs="*", help="Search query terms")
    args = parser.parse_args()

    if args.index:
        build_index(force=args.force, limit=args.limit)
    elif args.query:
        cli_search(" ".join(args.query), k=args.k)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
