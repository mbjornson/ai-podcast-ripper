#!/usr/bin/env python3
# pylint: disable=line-too-long
"""Patch summaries into transcripts that were written without one (Ollama was down)."""

from pathlib import Path

import yaml

import metrics as metrics_mod

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"

MISSING = [
    "transcripts/lennys-podcast/2025-10-09--first-interview-with-scale-ais-ceo-14b-meta-deal-whats-working-in-enterprise-ai-.md",
    "transcripts/lennys-podcast/2025-10-05--how-to-find-hidden-growth-opportunities-in-your-product-albert-cheng-duolingo-gr.md",
    "transcripts/lennys-podcast/2025-09-28--a-4-step-framework-for-building-delightful-products-nesrine-changuel-spotify-goo.md",
    "transcripts/how-i-ai/2026-06-01--building-an-iphone-app-with-zero-technical-skills-bryce-rattner-keithley.md",
    "transcripts/how-i-ai/2025-10-13--evals-error-analysis-and-better-prompts-a-systematic-approach-to-improving-your-.md",
    "transcripts/how-i-ai/2025-10-06--im-incapable-of-doing-my-job-without-ai-how-this-top-pm-uses-claude-chatgpt-as-h.md",
    "transcripts/product-thinking/2025-05-21--episode-224-why-empathy-is-a-product-superpower-with-somer-simpson.md",
    "transcripts/product-thinking/2025-05-14--episode-223-behind-the-rise-of-github-copilot-with-mario-rodriguez.md",
    "transcripts/product-thinking/2025-05-07--episode-222-designing-for-real-user-understanding-with-dheerja-kaur.md",
    "transcripts/nate-jones-ai-news-strategy-daily/2026-04-19--karpathys-agent-ran-700-experiments-while-he-slept-its-coming-for-you.md",
    "transcripts/nate-jones-ai-news-strategy-daily/2026-04-17--anthropic-and-openai-are-fighting-over-your-memory-youre-going-to-lose.md",
    "transcripts/nate-jones-ai-news-strategy-daily/2026-04-16--your-ai-is-50x-faster-youre-getting-2x-youre-fixing-the-wrong-thing.md",
    "transcripts/the-knowledge-project/2025-08-21--small-town-billionaire-john-braggs-3-empires-outliers.md",
    "transcripts/the-knowledge-project/2025-08-14--the-science-of-lasting-love-with-dr-sue-johnson.md",
    "transcripts/the-knowledge-project/2025-08-07--sol-price-the-godfather-of-costco-walmart-and-modern-retail-outliers.md",
    "transcripts/acquisitions-anonymous/2026-01-20--the-18m-govcon-business.md",
    "transcripts/acquisitions-anonymous/2026-01-16--a-rolls-royce-limo-company-with-a-dangerous-catch.md",
    "transcripts/acquisitions-anonymous/2026-01-13--buying-a-marketing-agency-in-the-age-of-ai.md",
    "transcripts/coaching-for-leaders/2025-10-13--753-the-key-norm-of-a-high-performing-team-with-vanessa-druskat.md",
    "transcripts/coaching-for-leaders/2025-10-06--752-how-to-start-the-top-job-with-scott-keller.md",
    "transcripts/coaching-for-leaders/2025-09-29--751-leadership-through-our-common-humanity-with-neil-ghosh.md",
    "transcripts/consulting-success-podcast/2025-09-22--why-6-figure-consultants-stay-stuck-and-how-to-break-through.md",
    "transcripts/consulting-success-podcast/2025-09-15--how-to-build-a-sellable-consulting-firm-with-david-c-baker.md",
    "transcripts/consulting-success-podcast/2025-09-08--is-ai-killing-consulting.md",
    "transcripts/cost-of-glory/2024-05-21--87-pursuing-greatness-with-pano-kanelos.md",
    "transcripts/cost-of-glory/2024-05-08--86-pompey-aftermath-comparison-w-spartan-king-agesilaus.md",
    "transcripts/cost-of-glory/2024-04-30--85-pompey-iii-fields-of-pharsalus.md",
    "transcripts/derek-sivers/2026-01-07--your-first-thought-is-an-obstacle.md",
    "transcripts/derek-sivers/2026-01-06--the-more-emotional-the-belief-the-less-likely-its-true.md",
    "transcripts/derek-sivers/2026-01-05--beliefs-are-not-facts.md",
    "transcripts/dive-club/2025-12-01--steve-ruiz-is-the-canvas-the-future-for-ai.md",
    "transcripts/dive-club/2025-11-24--emily-campbell-ai-ux-deep-dive.md",
    "transcripts/dive-club/2025-11-14--geoffrey-litt-the-future-of-malleable-software.md",
    "transcripts/how-to-take-over-the-world/2025-03-26--from-orphan-to-icon-the-life-and-legacy-of-coco-chanel.md",
]


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def summarize(transcript, episode_title, podcast_name, model, summary_config,
              max_chars=metrics_mod.DEFAULT_TRANSCRIPT_CHARS,
              max_context=metrics_mod.DEFAULT_MAX_CONTEXT,
              num_predict=metrics_mod.DEFAULT_NUM_PREDICT,
              provider="ollama", base_url=metrics_mod.OMLX_BASE_URL,
              api_key=None):
    prompt = metrics_mod.build_summary_prompt(summary_config, podcast_name, episode_title,
                                              transcript, max_chars=max_chars)
    num_ctx = metrics_mod.context_window_for(prompt, num_predict, ceiling=max_context)
    return metrics_mod.generate_text(
        model, prompt, provider=provider, num_predict=num_predict,
        temperature=0.3, num_ctx=num_ctx, base_url=base_url, api_key=api_key,
    )


def patch_file(path, summary):
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    h1_idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    if h1_idx is None:
        print(f"  SKIP: no H1 title in {path}")
        return

    # Markdown is summary-only (transcript lives in raw/); replace the body after the H1.
    new_lines = lines[:h1_idx + 1] + ["", summary, ""]
    path.write_text("\n".join(new_lines), encoding="utf-8")


def main():
    config = load_config()
    settings = config["settings"]
    provider = settings.get("llm_provider", "ollama")
    model = metrics_mod.configured_model(settings)
    base_url = settings.get("omlx_base_url", metrics_mod.OMLX_BASE_URL)
    api_key = settings.get("omlx_api_key")
    summary_config = config.get("summary", {})
    max_chars = settings.get("max_transcript_chars", metrics_mod.DEFAULT_TRANSCRIPT_CHARS)
    max_context = settings.get("max_context_tokens", metrics_mod.DEFAULT_MAX_CONTEXT)
    num_predict = settings.get("summary_num_predict", metrics_mod.DEFAULT_NUM_PREDICT)

    total = len(MISSING)
    for i, rel in enumerate(MISSING, 1):
        path = BASE_DIR / rel
        if not path.exists():
            print(f"[{i}/{total}] MISSING FILE: {rel}")
            continue

        # Derive podcast name from folder
        podcast_name = path.parent.name.replace("-", " ").title()
        episode_title = path.stem.split("--", 1)[-1].replace("-", " ").title()

        # Read transcript from the raw/ corpus
        transcript = metrics_mod.extract_transcript(path)
        if not transcript:
            print(f"[{i}/{total}] SKIP (no raw transcript): {path.name}")
            continue

        print(f"[{i}/{total}] Summarizing: {path.name}", flush=True)
        summary = summarize(transcript, episode_title, podcast_name, model,
                            summary_config, max_chars=max_chars,
                            max_context=max_context, num_predict=num_predict,
                            provider=provider, base_url=base_url, api_key=api_key)
        if not summary:
            print("  FAILED")
            continue

        patch_file(path, summary)
        print("  Done")


if __name__ == "__main__":
    main()
