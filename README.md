# Podcast Ripper

Local podcast transcription and summarization pipeline. Fetches new episodes from RSS feeds, transcribes with whisper.cpp, summarizes with a local LLM via Ollama, and outputs structured markdown.

Everything runs locally — no external APIs.

## Requirements

- macOS (Apple Silicon recommended)
- [Homebrew](https://brew.sh)
- Python 3.10+
- [Ollama](https://ollama.com)

## Setup

### 1. Install dependencies

```bash
brew install whisper-cpp ffmpeg
pip3 install feedparser pyyaml
```

### 2. Download the whisper model

```bash
curl -L -o /opt/homebrew/share/whisper-cpp/models/ggml-medium.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
```

This is ~1.5 GB. Use `ggml-base.bin` instead for faster but less accurate transcription.

### 3. Pull the summarization model

```bash
ollama pull gemma3
```

Make sure Ollama is running (`ollama serve` or the Ollama desktop app).

### 4. Add your podcasts

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and add RSS feed URLs:

```yaml
feeds:
  - name: "My Podcast"
    url: "https://example.com/feed.xml"
```

> **Note:** Use RSS feed URLs, not Spotify/Apple/YouTube links. Most podcasts publish their RSS URL on their website or you can find it on [podcastindex.org](https://podcastindex.org).

## Usage

```bash
python3 rip.py
```

On the first run it processes the latest episodes. On subsequent runs it only processes new episodes. When there are no new episodes, it backfills older ones from the back catalog.

## Output

Transcripts are saved as markdown in:

```
transcripts/<podcast-name>/<publish-date>--<episode-title>.md
```

Each file includes YAML frontmatter, a summary, key points, notable quotes, action items, and the full transcript.

## Daily Digest

When enabled, a digest file is generated at the end of each run collecting summaries from all processed episodes:

```
transcripts/digests/YYYY-MM-DD.md
```

Enable it in `config.yaml`:

```yaml
digest:
  enabled: true
```

The digest includes Summary, Key Points, and Action Items by default (configurable via `digest.sections`). Full transcripts are excluded.

## Configuration

All settings live in `config.yaml`:

| Setting | Default | Description |
|---|---|---|
| `whisper_model` | `medium` | Whisper model size (`base`, `medium`, `large-v3`) |
| `ollama_model` | `gemma3` | Ollama model for summarization |
| `max_episodes_per_feed` | `3` | Max new episodes to process per feed per run |
| `backfill_episodes` | `3` | Older episodes to grab when no new ones exist |
| `keep_audio` | `false` | Keep downloaded audio files after transcription |
| `digest.enabled` | `false` | Generate a daily digest after each run |
| `digest.sections` | `[Summary, Key Points, Action Items]` | Which sections to include |
| `digest.output_dir` | `digests` | Subdirectory under `transcripts/` |

## Development

Enable the pre-commit hook to run pylint before each commit:

```bash
pip3 install pylint
git config core.hooksPath .githooks
```

## Daily scheduling (optional)

To run automatically at midnight, generate a LaunchAgent from the template,
substituting in your own paths. Run this from the repo root:

```bash
sed -e "s|__HOME__|$HOME|g" \
    -e "s|__PROJECT_DIR__|$PWD|g" \
    -e "s|__PYTHON_BIN__|$(which python3)|g" \
    com.shapeandship.podcast-ripper.plist.example \
    > ~/Library/LaunchAgents/com.shapeandship.podcast-ripper.plist
launchctl load ~/Library/LaunchAgents/com.shapeandship.podcast-ripper.plist
```

The template wraps the run in `caffeinate -i -s`, so the Mac stays awake for
the whole batch and sleeps again once it finishes.

Check logs at `~/Library/Logs/podcast-ripper.log`.

To stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.shapeandship.podcast-ripper.plist
```

**On a laptop that sleeps overnight**, also schedule a wake a few minutes
before the run so the Mac is up when the job fires:

```bash
sudo pmset repeat wakeorpoweron MTWRFSU 23:55:00
```
