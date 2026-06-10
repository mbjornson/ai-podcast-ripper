#!/usr/bin/env python3
# pylint: disable=line-too-long
"""Render the token-burn / signal-quality dashboard from metrics.jsonl."""

import argparse
import datetime
import html
import logging
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

import metrics as metrics_mod

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
METRICS_PATH = BASE_DIR / "metrics.jsonl"
RATINGS_PATH = BASE_DIR / "ratings.jsonl"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
DEFAULT_OUTPUT_DIR = TRANSCRIPTS_DIR / "digests"

SPARK_BLOCKS = "▁▂▃▄▅▆▇█"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("dashboard")


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_rows(jsonl_path=METRICS_PATH):
    # Deduplicate: keep latest row per path (last write wins)
    by_path = {}
    for r in metrics_mod.iter_jsonl(jsonl_path):
        by_path[r.get("path", "")] = r
    return list(by_path.values())


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def filter_window(rows, days, ref_date=None):
    if not days:
        return rows
    ref = ref_date or datetime.date.today()
    cutoff = ref - datetime.timedelta(days=days)
    out = []
    for r in rows:
        d = parse_date(r.get("date"))
        if d and d >= cutoff:
            out.append(r)
    return out


def safe_mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else 0.0


def aggregate_per_podcast(rows):
    """Return list of per-podcast aggregates, one dict per podcast.

    Groups by `podcast_slug` (stable, derived from folder name) to merge rows
    that have inconsistent display-name capitalization in their frontmatter.
    Display name = most common across the group's rows.
    """
    grouped = defaultdict(list)
    for r in rows:
        key = r.get("podcast_slug") or r.get("podcast") or "unknown"
        grouped[key].append(r)

    aggs = []
    for _slug, eps in grouped.items():
        name_counts = Counter(e.get("podcast") for e in eps if e.get("podcast"))
        podcast = name_counts.most_common(1)[0][0] if name_counts else "Unknown"
        eps_count = len(eps)
        total_audio_sec = sum(e.get("audio_duration_seconds") or 0 for e in eps)
        signal_density = safe_mean([e.get("signal_density") for e in eps])
        low_signal_rate = sum(1 for e in eps if e.get("low_signal_flag")) / eps_count

        judged = [e.get("judge") for e in eps if e.get("judge")]
        avg_actionability = safe_mean([j.get("actionability") for j in judged])
        avg_judge_signal = safe_mean([j.get("signal_density") for j in judged])
        recommend_rate = (
            sum(1 for j in judged if j.get("would_recommend")) / len(judged) if judged else 0.0
        )

        aggs.append({
            "podcast": podcast,
            "episodes": eps_count,
            "audio_hours": round(total_audio_sec / 3600.0, 1),
            "signal_density": round(signal_density, 3),
            "low_signal_rate": round(low_signal_rate, 3),
            "avg_actionability": round(avg_actionability, 2),
            "avg_judge_signal": round(avg_judge_signal, 2),
            "recommend_rate": round(recommend_rate, 3),
            "judged_count": len(judged),
            "raw_episodes": eps,
        })
    return aggs


def compute_drift(rows, drift_days, ref_date=None):
    """Mean actionability in last `drift_days` minus mean in prior `drift_days`."""
    ref = ref_date or datetime.date.today()
    recent_cutoff = ref - datetime.timedelta(days=drift_days)
    prior_cutoff = ref - datetime.timedelta(days=drift_days * 2)

    recent_scores = []
    prior_scores = []
    for r in rows:
        d = parse_date(r.get("date"))
        if not d:
            continue
        judge = r.get("judge") or {}
        score = judge.get("actionability")
        if score is None:
            continue
        if d >= recent_cutoff:
            recent_scores.append(score)
        elif d >= prior_cutoff:
            prior_scores.append(score)

    if not recent_scores or not prior_scores:
        return None
    return round(safe_mean(recent_scores) - safe_mean(prior_scores), 2)


def sparkline(values, width=12):
    """Map values to unicode block chars. Values can be int/float."""
    if not values:
        return " " * width
    if len(values) > width:
        # Bucket-average
        step = len(values) / width
        bucketed = []
        for i in range(width):
            chunk = values[int(i * step):int((i + 1) * step)] or [values[-1]]
            bucketed.append(safe_mean(chunk))
        values = bucketed

    lo = min(values)
    hi = max(values)
    rng = hi - lo or 1
    chars = []
    for v in values:
        idx = int(((v - lo) / rng) * (len(SPARK_BLOCKS) - 1))
        chars.append(SPARK_BLOCKS[idx])
    return "".join(chars).ljust(width)


def per_podcast_sparkline(rows):
    """Sparkline of actionability over time for one podcast's rows."""
    scored = sorted(
        ((parse_date(r.get("date")), (r.get("judge") or {}).get("actionability"))
         for r in rows),
        key=lambda t: t[0] or datetime.date.min,
    )
    values = [s for _, s in scored if s is not None]
    return sparkline(values, width=12)


def podcast_slug_for(rows, podcast_name):
    """Best-effort podcast_slug. Use any row's slug, fall back to a sanitized name."""
    for r in rows:
        slug = r.get("podcast_slug")
        if slug:
            return slug
    cleaned = re.sub(r"[^a-z0-9]+", "-", (podcast_name or "").lower()).strip("-")
    return cleaned or "podcast"


def svg_line_chart(points, width=720, height=200, color="#2563eb", label="actionability"):
    """Render an SVG line chart from (date, value) tuples. Values are numeric.

    Includes axis labels at min/max date, gridlines, and hover tooltips on points.
    """
    points = [(d, v) for d, v in points if d is not None and v is not None]
    if not points:
        return f"<svg width='{width}' height='{height}'><text x='10' y='20' fill='#999'>No {label} data yet</text></svg>"

    points.sort(key=lambda t: t[0])
    pad_l, pad_r, pad_t, pad_b = 40, 20, 20, 30
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    dates = [d for d, _ in points]
    values = [v for _, v in points]
    d_min, d_max = dates[0], dates[-1]
    d_range = (d_max - d_min).days or 1
    v_min, v_max = min(values), max(values)
    if v_max == v_min:
        v_min -= 0.5
        v_max += 0.5
    v_range = v_max - v_min

    def x_for(d):
        return pad_l + ((d - d_min).days / d_range) * plot_w

    def y_for(v):
        return pad_t + plot_h - ((v - v_min) / v_range) * plot_h

    coords = [(x_for(d), y_for(v)) for d, v in points]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)

    # Gridlines at min/mid/max y
    grid_lines = []
    for frac, v_val in [(0, v_max), (0.5, (v_min + v_max) / 2), (1, v_min)]:
        y = pad_t + frac * plot_h
        grid_lines.append(
            f"<line x1='{pad_l}' y1='{y:.1f}' x2='{pad_l + plot_w}' y2='{y:.1f}' "
            f"stroke='#eee' stroke-width='1'/>"
            f"<text x='{pad_l - 5}' y='{y + 4:.1f}' text-anchor='end' font-size='10' fill='#999'>{v_val:.1f}</text>"
        )

    # Data points with hover tooltips
    circles = []
    for (d, v), (x, y) in zip(points, coords):
        circles.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='{color}'>"
            f"<title>{d.isoformat()}: {label}={v}</title></circle>"
        )

    # Date axis labels
    x_labels = (
        f"<text x='{pad_l}' y='{height - 8}' font-size='10' fill='#888'>{d_min.isoformat()}</text>"
        f"<text x='{pad_l + plot_w}' y='{height - 8}' text-anchor='end' font-size='10' fill='#888'>{d_max.isoformat()}</text>"
    )

    return (
        f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        + "".join(grid_lines)
        + f"<polyline points='{polyline}' fill='none' stroke='{color}' stroke-width='2'/>"
        + "".join(circles)
        + x_labels
        + "</svg>"
    )


def render_podcast_detail_html(podcast_name, raw_episodes, drift_days, today):
    slug = podcast_slug_for(raw_episodes, podcast_name)

    episodes = sorted(
        raw_episodes,
        key=lambda r: parse_date(r.get("date")) or datetime.date.min,
        reverse=True,
    )

    judged = [r for r in episodes if r.get("judge")]
    actionability_points = [
        (parse_date(r.get("date")), (r.get("judge") or {}).get("actionability"))
        for r in episodes
    ]
    density_points = [
        (parse_date(r.get("date")), r.get("signal_density"))
        for r in episodes
    ]

    chart_act = svg_line_chart(actionability_points, color="#2563eb", label="actionability")
    chart_den = svg_line_chart(density_points, color="#16a34a", label="signal_density")

    drift = compute_drift(raw_episodes, drift_days, today)
    drift_str = f"{drift:+.2f}" if drift is not None else "—"
    avg_act = (
        f"{sum((r.get('judge') or {}).get('actionability', 0) for r in judged) / len(judged):.2f}"
        if judged else "—"
    )
    rec_pct = (
        f"{sum(1 for r in judged if (r.get('judge') or {}).get('would_recommend')) / len(judged) * 100:.0f}%"
        if judged else "—"
    )
    audio_hours = round(sum(r.get("audio_duration_seconds") or 0 for r in episodes) / 3600.0, 1)
    low_sig_pct = (
        f"{sum(1 for r in episodes if r.get('low_signal_flag')) / len(episodes) * 100:.0f}%"
        if episodes else "—"
    )

    ep_rows = []
    for r in episodes:
        d = html.escape(str(r.get("date", "?")))
        title = r.get("episode_title") or r.get("path", "?")
        path = r.get("path", "")
        abs_path = (BASE_DIR / path).resolve() if path else None
        title_html = (
            f"<a href='file://{html.escape(str(abs_path))}'>{html.escape(title[:120])}</a>"
            if abs_path else html.escape(title[:120])
        )
        judge = r.get("judge") or {}
        score = judge.get("actionability")
        score_html = f"{score}/10" if score is not None else "—"
        rec_html = "✓" if judge.get("would_recommend") else ("✗" if judge else "—")
        dur_sec = r.get("audio_duration_seconds") or 0
        dur_html = f"{dur_sec // 60}m" if dur_sec else "—"
        low_html = "⚠" if r.get("low_signal_flag") else ""
        rationale = html.escape((judge.get("rationale") or "")[:200])
        path_attr = html.escape(path)
        rate_buttons = (
            f"<div class='rate' data-path='{path_attr}'>"
            f"<button class='rb' data-r='2' title='must-share'>⭐</button>"
            f"<button class='rb' data-r='1' title='thumbs up'>👍</button>"
            f"<button class='rb' data-r='-1' title='thumbs down'>👎</button>"
            f"<button class='rb' data-r='-2' title='drop this podcast'>🗑</button>"
            f"</div>"
        )
        ep_rows.append(
            f"<tr>"
            f"<td class='date'>{d}</td>"
            f"<td>{title_html}</td>"
            f"<td>{dur_html}</td>"
            f"<td>{r.get('action_items_count', 0)}</td>"
            f"<td>{score_html}</td>"
            f"<td>{rec_html}</td>"
            f"<td>{low_html}</td>"
            f"<td>{rate_buttons}</td>"
            f"<td class='rationale'>{rationale}</td>"
            f"</tr>"
        )

    body = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(podcast_name)} — Signal Detail</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em;color:#222}}
h1{{font-weight:600;margin-bottom:.2em}}
.muted{{color:#888;font-size:13px}}
.stats{{display:flex;gap:2em;margin:1em 0;flex-wrap:wrap}}
.stat{{font-size:13px}}
.stat strong{{display:block;font-size:22px;color:#111}}
.chart{{margin:1em 0;background:#fafafa;border-radius:6px;padding:1em}}
.chart h3{{margin:0 0 .5em;font-size:14px;color:#555}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:1em}}
th,td{{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top}}
td.date{{white-space:nowrap;color:#888;font-variant-numeric:tabular-nums}}
td.rationale{{color:#666;font-size:12px;max-width:300px}}
a{{color:#2563eb;text-decoration:none}}
a:hover{{text-decoration:underline}}
.back{{font-size:13px;display:inline-block;margin-bottom:1em}}
.rate{{display:flex;gap:2px}}
.rate .rb{{background:#fff;border:1px solid #ddd;border-radius:4px;padding:2px 6px;cursor:pointer;font-size:14px;line-height:1}}
.rate .rb:hover{{background:#f0f0f0;border-color:#aaa}}
.rate .rb.active{{background:#0a7;border-color:#0a7;color:#fff}}
.rate .rb.active.neg{{background:#c0392b;border-color:#c0392b}}
#toast{{position:fixed;bottom:1em;right:1em;background:#222;color:#fff;padding:8px 14px;border-radius:4px;font-size:13px;opacity:0;transition:opacity .25s;pointer-events:none}}
#toast.show{{opacity:1}}
</style></head><body>
<a class="back" href="../dashboard.html">← Back to dashboard</a>
<h1>{html.escape(podcast_name)}</h1>
<p class="muted">{len(episodes)} episodes · {len(judged)} judged · slug: <code>{html.escape(slug)}</code></p>

<div class="stats">
  <div class="stat"><strong>{avg_act}</strong>avg actionability</div>
  <div class="stat"><strong>{rec_pct}</strong>recommend rate</div>
  <div class="stat"><strong>{drift_str}</strong>drift ({drift_days}d)</div>
  <div class="stat"><strong>{audio_hours}h</strong>total audio</div>
  <div class="stat"><strong>{low_sig_pct}</strong>low-signal rate</div>
</div>

<div class="chart"><h3>Actionability over time (LLM judge, 1-10)</h3>{chart_act}</div>
<div class="chart"><h3>Signal density over time (heuristic, items/min)</h3>{chart_den}</div>

<h2 style="margin-top:2em;font-size:16px">Episodes</h2>
<p class="muted">Click a thumb to rate. Ratings calibrate future judge scores. Click the same button again to clear.</p>
<table>
<thead><tr><th>Date</th><th>Episode</th><th>Dur</th><th>Actions</th><th>Judge</th><th>Rec</th><th>Low</th><th>Rate</th><th>Rationale</th></tr></thead>
<tbody>{''.join(ep_rows)}</tbody>
</table>
<div id="toast"></div>
<script>
(async () => {{
  const toast = (msg) => {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1500);
  }};
  const paint = (path, rating) => {{
    const row = document.querySelector(`.rate[data-path="${{path}}"]`);
    if (!row) return;
    row.querySelectorAll('.rb').forEach(b => {{
      const r = parseInt(b.dataset.r);
      const active = rating !== null && r === rating;
      b.classList.toggle('active', active);
      b.classList.toggle('neg', active && r < 0);
    }});
  }};

  // Load current ratings
  try {{
    const res = await fetch('/api/ratings');
    if (res.ok) {{
      const data = await res.json();
      Object.entries(data).forEach(([path, rating]) => paint(path, rating));
    }}
  }} catch (e) {{ /* offline mode */ }}

  // Wire up clicks
  document.querySelectorAll('.rate').forEach(box => {{
    box.querySelectorAll('.rb').forEach(btn => {{
      btn.addEventListener('click', async () => {{
        const path = box.dataset.path;
        const rating = parseInt(btn.dataset.r);
        // Toggle off if same rating clicked again
        const newRating = btn.classList.contains('active') ? 0 : rating;
        try {{
          const res = await fetch('/api/rate', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{path, rating: newRating}})
          }});
          if (!res.ok) throw new Error('failed');
          paint(path, newRating === 0 ? null : newRating);
          toast(newRating === 0 ? 'Cleared' : `Rated ${{newRating > 0 ? '+' : ''}}${{newRating}}`);
        }} catch (e) {{
          toast('Error — is serve.py running?');
        }}
      }});
    }});
  }});
}})();
</script>
</body></html>
"""
    return slug, body


def render_markdown(window_days, drift_days):
    rows = load_rows()
    log.info("Loaded %d rows", len(rows))
    today = datetime.date.today()

    windowed = filter_window(rows, window_days, today)
    aggs = aggregate_per_podcast(windowed)

    # Sort leaderboard: judged podcasts first by avg_actionability, then unjudged by signal_density
    aggs.sort(key=lambda a: (a["judged_count"] == 0, -a["avg_actionability"], -a["signal_density"]))

    lines = [
        "---",
        "type: dashboard",
        f"generated: {today.isoformat()}",
        f"window_days: {window_days}",
        f"total_episodes: {len(windowed)}",
        f"total_podcasts: {len(aggs)}",
        "---",
        "",
        f"# Signal Dashboard — {today.isoformat()}",
        "",
        f"Window: last {window_days} days. Drift: last {drift_days}d vs prior {drift_days}d.",
        "",
        "## Column Definitions",
        "",
        "- **Eps** — episodes in window",
        "- **Audio (h)** — total audio hours in window",
        "- **Sig/min** — *signal density* (heuristic): `(action_items + key_points + tools) / audio_minutes`. Higher = more concrete takeaways per minute of audio.",
        "- **Low-sig%** — % of episodes where the summary explicitly flagged \"low signal\" / \"mostly entertainment\"",
        "- **Avg-act** — *average actionability* (LLM judge, 1-10): how many concrete, applicable actions a listener can take. Higher = more actionable.",
        "- **Rec%** — % of episodes the judge would recommend to a busy operator",
        "- **Drift** — avg actionability in last 7d minus prior 7d. Positive = trending up; negative = declining.",
        "- **Spark** — sparkline of actionability over time (oldest → newest, left → right)",
        "",
        "## Leaderboard",
        "",
        "| Podcast | Eps | Audio (h) | Sig/min | Low-sig% | Avg-act | Rec% | Drift | Spark |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---|",
    ]

    for a in aggs:
        drift = compute_drift(a["raw_episodes"], drift_days, today)
        drift_str = f"{drift:+.1f}" if drift is not None else "—"
        spark = per_podcast_sparkline(a["raw_episodes"])
        low_sig_pct = f"{a['low_signal_rate'] * 100:.0f}%"
        rec_pct = f"{a['recommend_rate'] * 100:.0f}%" if a["judged_count"] else "—"
        avg_act = f"{a['avg_actionability']:.1f}" if a["judged_count"] else "—"
        lines.append(
            f"| {a['podcast']} | {a['episodes']} | {a['audio_hours']} | "
            f"{a['signal_density']:.2f} | {low_sig_pct} | {avg_act} | {rec_pct} | {drift_str} | `{spark}` |"
        )

    lines.extend(["", "## Drop Candidates", ""])
    drops = [
        a for a in aggs
        if a["episodes"] >= 5 and (
            a["low_signal_rate"] > 0.4
            or (a["judged_count"] >= 3 and a["avg_actionability"] < 5.0)
        )
    ]
    if drops:
        lines.append("Podcasts with ≥5 episodes in window AND (low-signal rate > 40% OR avg actionability < 5):")
        lines.append("")
        for a in drops:
            reasons = []
            if a["low_signal_rate"] > 0.4:
                reasons.append(f"low-signal {a['low_signal_rate'] * 100:.0f}%")
            if a["judged_count"] >= 3 and a["avg_actionability"] < 5.0:
                reasons.append(f"avg-act {a['avg_actionability']:.1f}")
            lines.append(f"- **{a['podcast']}** — {', '.join(reasons)}")
    else:
        lines.append("*None.*")

    lines.extend(["", "## Top Episodes", ""])
    judged_episodes = [r for r in windowed if r.get("judge")]
    judged_episodes.sort(
        key=lambda r: (r.get("judge") or {}).get("actionability", 0),
        reverse=True,
    )
    for r in judged_episodes[:10]:
        judge = r.get("judge") or {}
        title = r.get("episode_title", "?")[:80]
        podcast = r.get("podcast", "?")
        score = judge.get("actionability", 0)
        rationale = judge.get("rationale", "")
        lines.append(f"- **[{score}/10]** *{podcast}* — {title}")
        if rationale:
            lines.append(f"  - {rationale}")

    return "\n".join(lines) + "\n"


def render_html(window_days, drift_days):
    rows = load_rows()
    ratings = metrics_mod.load_ratings(RATINGS_PATH)
    bias_by_slug = metrics_mod.compute_podcast_bias(rows, ratings)
    today = datetime.date.today()
    windowed = filter_window(rows, window_days, today)
    aggs = aggregate_per_podcast(windowed)

    # Compute adjusted score per podcast
    for a in aggs:
        slug = podcast_slug_for(a["raw_episodes"], a["podcast"])
        bias_info = bias_by_slug.get(slug)
        a["bias"] = bias_info[0] if bias_info else None
        a["rated_count"] = bias_info[1] if bias_info else 0
        a["adj_actionability"] = (
            a["avg_actionability"] - a["bias"] if a["bias"] is not None else a["avg_actionability"]
        )

    aggs.sort(key=lambda a: (a["judged_count"] == 0, -a["adj_actionability"], -a["signal_density"]))

    rows_html = []
    for a in aggs:
        drift = compute_drift(a["raw_episodes"], drift_days, today)
        drift_str = f"{drift:+.1f}" if drift is not None else "—"
        spark = per_podcast_sparkline(a["raw_episodes"])
        avg_act = f"{a['avg_actionability']:.1f}" if a["judged_count"] else "—"
        adj_act = f"{a['adj_actionability']:.1f}" if a["judged_count"] else "—"
        rec_pct = f"{a['recommend_rate'] * 100:.0f}%" if a["judged_count"] else "—"
        slug = podcast_slug_for(a["raw_episodes"], a["podcast"])
        title_html = (
            f"<a href='dashboard/{html.escape(slug)}.html'>{html.escape(a['podcast'])}</a>"
        )
        rated_html = f"{a['rated_count']}" if a["rated_count"] else "—"
        bias_html = f"{a['bias']:+.1f}" if a["bias"] is not None else "—"
        adj_class = "adjusted" if a["rated_count"] else ""
        rows_html.append(
            "<tr>"
            f"<td>{title_html}</td>"
            f"<td>{a['episodes']}</td>"
            f"<td>{a['audio_hours']}</td>"
            f"<td>{a['signal_density']:.2f}</td>"
            f"<td>{a['low_signal_rate'] * 100:.0f}%</td>"
            f"<td>{avg_act}</td>"
            f"<td class='{adj_class}'>{adj_act}</td>"
            f"<td>{rated_html}</td>"
            f"<td>{bias_html}</td>"
            f"<td>{rec_pct}</td>"
            f"<td>{drift_str}</td>"
            f"<td class='spark'>{spark}</td>"
            "</tr>"
        )

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Signal Dashboard — {today.isoformat()}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em;color:#222}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border-bottom:1px solid #eee;padding:6px 8px;text-align:right}}
th:first-child,td:first-child{{text-align:left}}
th abbr{{text-decoration:underline dotted;cursor:help}}
td.adjusted{{font-weight:600;color:#0a7}}
.spark{{font-family:monospace;font-size:18px;letter-spacing:0}}
#search-box{{display:block;width:100%;padding:.6em .9em;margin:1em 0;font-size:15px;border:1px solid #ccc;border-radius:6px;font-family:inherit}}
#search-results{{margin:1em 0}}
.result{{padding:8px 0;border-bottom:1px solid #eee}}
.result .meta{{font-size:12px;color:#888;display:flex;gap:.8em;flex-wrap:wrap;margin-bottom:.2em}}
.result .meta .score{{color:#0a7;font-weight:600}}
.result .text{{font-size:14px;color:#333}}
.result .title{{font-weight:600;font-size:13px;margin-bottom:.2em}}
.result .title a{{color:#222}}
.result .title a:hover{{color:#2563eb}}
h1{{font-weight:600}}
.muted{{color:#888;font-size:13px}}
details{{margin:1em 0;padding:.5em 1em;background:#f7f7f7;border-radius:6px;font-size:13px}}
details summary{{cursor:pointer;font-weight:600}}
details dl{{margin:.5em 0 0}}
details dt{{font-weight:600;margin-top:.4em}}
details dd{{margin:0 0 0 1em;color:#555}}
</style></head><body>
<h1>Signal Dashboard — {today.isoformat()}</h1>
<p class="muted">Window: {window_days}d · Drift: {drift_days}d vs prior · {len(windowed)} episodes · {len(aggs)} podcasts</p>
<input id="search-box" type="search" placeholder="Search across all episodes — e.g. &quot;pricing AI products&quot;, &quot;remote teams&quot;, &quot;constitutional AI&quot;" autocomplete="off">
<div id="search-results"></div>
<details open><summary>Column definitions</summary>
<dl>
<dt>Eps</dt><dd>Episodes in window</dd>
<dt>Hours</dt><dd>Total audio hours in window</dd>
<dt>Sig/min</dt><dd>Signal density (heuristic): (action_items + key_points + tools) / audio_minutes. Higher = more concrete takeaways per minute.</dd>
<dt>Low-sig</dt><dd>% of episodes flagged "low signal" / "mostly entertainment" by the summary</dd>
<dt>Avg-act</dt><dd>Raw average actionability score (LLM judge, 1-10). How many concrete actions a listener can take.</dd>
<dt>Adj-act</dt><dd>Avg-act minus per-podcast user-rating bias. Bold green when ratings exist. Sort key for the leaderboard.</dd>
<dt>Rated</dt><dd>Number of episodes you've thumbed up/down for this podcast</dd>
<dt>Bias</dt><dd>(judge_score − your_target_score) avg per podcast. + means judge inflates; − means judge underrates relative to you.</dd>
<dt>Rec%</dt><dd>% of episodes the judge would recommend to a busy operator</dd>
<dt>Drift</dt><dd>Avg actionability in last {drift_days}d minus prior {drift_days}d. Positive = trending up.</dd>
<dt>Trend</dt><dd>Sparkline of actionability over time (oldest → newest)</dd>
</dl>
</details>
<table>
<thead><tr>
<th>Podcast</th>
<th><abbr title="Episodes in window">Eps</abbr></th>
<th><abbr title="Total audio hours in window">Hours</abbr></th>
<th><abbr title="Signal density: (action_items + key_points + tools) / audio_minutes">Sig/min</abbr></th>
<th><abbr title="% of episodes flagged low-signal by the summary">Low-sig</abbr></th>
<th><abbr title="Raw average actionability (LLM judge)">Avg-act</abbr></th>
<th><abbr title="Adjusted: Avg-act minus per-podcast bias from your ratings">Adj-act</abbr></th>
<th><abbr title="Number of episodes you've rated">Rated</abbr></th>
<th><abbr title="Judge minus your target score, averaged">Bias</abbr></th>
<th><abbr title="% of episodes the judge would recommend">Rec%</abbr></th>
<th><abbr title="Last {drift_days}d avg actionability minus prior {drift_days}d">Drift</abbr></th>
<th><abbr title="Sparkline of actionability over time (oldest → newest)">Trend</abbr></th>
</tr></thead>
<tbody>{''.join(rows_html)}</tbody>
</table>
<script>
(() => {{
  const box = document.getElementById('search-box');
  const out = document.getElementById('search-results');
  if (!box) return;

  const debounce = (fn, ms) => {{
    let t; return (...a) => {{ clearTimeout(t); t = setTimeout(() => fn(...a), ms); }};
  }};
  const esc = (s) => (s||'').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));

  const renderResults = (results) => {{
    if (!results || !results.length) {{ out.innerHTML = '<p class="muted">No results.</p>'; return; }}
    out.innerHTML = results.map(r => {{
      const slug = r.podcast_slug || '';
      const title = esc(r.episode_title || '(untitled)');
      const path = esc(r.path || '');
      return `<div class="result">
        <div class="meta">
          <span class="score">${{r.score.toFixed(3)}}</span>
          <span>${{esc(r.section || '')}}</span>
          <span><a href="dashboard/${{esc(slug)}}.html">${{esc(r.podcast || '')}}</a></span>
          <span>${{esc(r.date || '')}}</span>
        </div>
        <div class="title"><a href="/${{path}}" target="_blank">${{title}}</a></div>
        <div class="text">${{esc(r.text || '')}}</div>
      </div>`;
    }}).join('');
  }};

  const run = debounce(async () => {{
    const q = box.value.trim();
    if (q.length < 3) {{ out.innerHTML = ''; return; }}
    out.innerHTML = '<p class="muted">Searching…</p>';
    try {{
      const res = await fetch('/api/search?q=' + encodeURIComponent(q) + '&k=20');
      if (!res.ok) {{ out.innerHTML = '<p class="muted">Search unavailable (start serve.py).</p>'; return; }}
      const data = await res.json();
      if (data.error) {{ out.innerHTML = `<p class="muted">${{esc(data.error)}}</p>`; return; }}
      renderResults(data);
    }} catch (e) {{ out.innerHTML = '<p class="muted">Network error.</p>'; }}
  }}, 250);

  box.addEventListener('input', run);
}})();
</script>
</body></html>
"""


def write_detail_pages(out_dir, window_days, drift_days):
    """Write one HTML detail page per podcast under <out_dir>/dashboard/<slug>.html.

    Detail pages use ALL episodes (not windowed) so trends span full history.
    """
    rows = load_rows()
    today = datetime.date.today()
    aggs_all = aggregate_per_podcast(rows)

    detail_dir = out_dir / "dashboard"
    detail_dir.mkdir(parents=True, exist_ok=True)

    for a in aggs_all:
        slug, body = render_podcast_detail_html(a["podcast"], a["raw_episodes"], drift_days, today)
        (detail_dir / f"{slug}.html").write_text(body, encoding="utf-8")
    log.info("Wrote %d detail pages to: %s", len(aggs_all), detail_dir)


def generate(output_dir=None):
    config = load_config()
    dash_cfg = config.get("dashboard", {})
    window_days = dash_cfg.get("window_days", 30)
    drift_days = dash_cfg.get("drift_window_days", 7)
    generate_html = dash_cfg.get("generate_html", False)

    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "dashboard.md"
    md_path.write_text(render_markdown(window_days, drift_days), encoding="utf-8")
    log.info("Wrote: %s", md_path)

    if generate_html:
        html_path = out_dir / "dashboard.html"
        html_path.write_text(render_html(window_days, drift_days), encoding="utf-8")
        log.info("Wrote: %s", html_path)
        write_detail_pages(out_dir, window_days, drift_days)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=None)
    parser.add_argument("--drift-days", type=int, default=None)
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    config = load_config()
    dash_cfg = config.setdefault("dashboard", {})
    if args.window_days is not None:
        dash_cfg["window_days"] = args.window_days
    if args.drift_days is not None:
        dash_cfg["drift_window_days"] = args.drift_days
    if args.html:
        dash_cfg["generate_html"] = True

    # Bypass YAML write — pass cfg through generate() side via closures
    out_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    window_days = dash_cfg.get("window_days", 30)
    drift_days = dash_cfg.get("drift_window_days", 7)

    md_path = out_dir / "dashboard.md"
    md_path.write_text(render_markdown(window_days, drift_days), encoding="utf-8")
    log.info("Wrote: %s", md_path)

    if dash_cfg.get("generate_html", False):
        html_path = out_dir / "dashboard.html"
        html_path.write_text(render_html(window_days, drift_days), encoding="utf-8")
        log.info("Wrote: %s", html_path)
        write_detail_pages(out_dir, window_days, drift_days)


if __name__ == "__main__":
    main()
