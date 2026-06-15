#!/usr/bin/env python3
"""Local Flask app: serves dashboard + accepts thumbs-up/down ratings.

Run:
    python serve.py
    open http://localhost:5151
"""

import logging
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import dashboard as dashboard_mod
import metrics as metrics_mod
import search as search_mod
import transcript_search as tsearch_mod

try:
    import entities as entities_mod
except Exception:  # pylint: disable=broad-except
    entities_mod = None  # pylint: disable=invalid-name

BASE_DIR = Path(__file__).parent
RATINGS_PATH = BASE_DIR / "ratings.jsonl"
DIGESTS_DIR = BASE_DIR / "transcripts" / "digests"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

PORT = 5151

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("serve")

app = Flask(__name__, static_folder=None)

# Regenerate debounce — coalesce rapid-fire clicks
_regen_lock = threading.Lock()
_regen_pending = threading.Event()
_REGEN_DEBOUNCE_SEC = 3.0


def _regen_worker():
    """Background: wait for debounce window, then regenerate. Idempotent."""
    while True:
        _regen_pending.wait()
        time.sleep(_REGEN_DEBOUNCE_SEC)
        _regen_pending.clear()
        with _regen_lock:
            try:
                dashboard_mod.generate()
                log.info("Dashboard regenerated")
            except Exception:
                log.exception("Regen failed")


threading.Thread(target=_regen_worker, daemon=True).start()

# Ensure dashboard exists at import time — supports both `python serve.py` and `flask run`
if not (DIGESTS_DIR / "dashboard.html").exists():
    log.info("No dashboard.html yet — generating...")
    dashboard_mod.generate()


@app.route("/")
def root():
    return send_from_directory(DIGESTS_DIR, "dashboard.html")


@app.route("/dashboard.html")
def dashboard_html():
    return send_from_directory(DIGESTS_DIR, "dashboard.html")


@app.route("/dashboard.md")
def dashboard_md():
    return send_from_directory(DIGESTS_DIR, "dashboard.md", mimetype="text/markdown")


@app.route("/entities.html")
def entities_html():
    return send_from_directory(DIGESTS_DIR, "entities.html")


@app.route("/dashboard/<path:fname>")
def dashboard_detail(fname):
    return send_from_directory(DIGESTS_DIR / "dashboard", fname)


@app.route("/transcripts/<path:fname>")
def transcript_file(fname):
    """Serve transcript .md files raw so file:// links can be replaced with http://."""
    return send_from_directory(TRANSCRIPTS_DIR, fname, mimetype="text/markdown")


@app.route("/api/ratings", methods=["GET"])
def get_ratings():
    return jsonify(metrics_mod.load_ratings(RATINGS_PATH))


@app.route("/api/rate", methods=["POST"])
def post_rate():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    rating = data.get("rating")
    if not path or rating is None:
        return jsonify({"error": "missing path or rating"}), 400
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({"error": "rating must be int"}), 400
    if rating not in (-2, -1, 0, 1, 2):
        return jsonify({"error": "rating must be -2,-1,0,1,2"}), 400

    metrics_mod.append_rating(RATINGS_PATH, path, rating)
    _regen_pending.set()  # schedule background regen
    return jsonify({"ok": True, "path": path, "rating": rating})


@app.route("/api/search", methods=["GET"])
def api_search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])
    try:
        k = int(request.args.get("k", "20"))
    except ValueError:
        k = 20
    k = max(1, min(k, 50))
    podcast = request.args.get("podcast") or None
    try:
        results = search_mod.search(q, k=k, podcast_slug=podcast)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    return jsonify(results)


@app.route("/api/search/transcripts", methods=["GET"])
def api_search_transcripts():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])
    try:
        k = int(request.args.get("k", "20"))
    except ValueError:
        k = 20
    k = max(1, min(k, 50))
    podcast = request.args.get("podcast") or None
    try:
        results = tsearch_mod.search(q, k=k, podcast_slug=podcast)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    return jsonify(results)


@app.route("/api/entities/<kind>", methods=["GET"])
def api_entities(kind):
    if entities_mod is None:
        return jsonify({"error": "entities module not available"}), 503
    if kind not in entities_mod.KINDS:
        return jsonify({"error": f"unknown kind; expected one of {list(entities_mod.KINDS)}"}), 400
    try:
        k = int(request.args.get("k", "50"))
    except ValueError:
        k = 50
    k = max(1, min(k, 500))
    podcast = request.args.get("podcast") or None
    results = entities_mod.aggregate(kind, podcast_slug=podcast)[:k]
    # Trim episodes per entity for API payload size
    for r in results:
        r["episodes"] = r["episodes"][:30]
    return jsonify(results)


@app.route("/api/regenerate", methods=["POST"])
def regenerate_now():
    with _regen_lock:
        dashboard_mod.generate()
    return jsonify({"ok": True})


def main():
    log.info("Serving on http://localhost:%d", PORT)
    log.info("Rate episodes by clicking thumbs in any detail page.")
    log.info("Ratings file: %s", RATINGS_PATH)
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
