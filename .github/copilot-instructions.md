# Copilot instructions for `daily-news`

## Commands

Assume the project virtualenv is activated.

- Install/editable setup: `python -m pip install -e .`
- Install browser runtime: `python -m playwright install chromium`
- Run all tests: `python -m unittest`
- Run a single test: `python -m unittest tests.test_storage.SqliteStoreTests.test_article_lifecycle`
- Smoke-test the pipeline without publishing: `daily-news run-once --config config.json --skip-publish`
- Start the admin UI: `daily-news serve --config config.json --host 127.0.0.1 --port 8000`

## High-level architecture

- `src/daily_news/cli.py` is the composition root. It builds the runtime pipeline from config: source adapter(s) -> summarizer -> TTS -> video renderer -> optional publisher. `serve` is separate and starts the FastAPI admin app over the same SQLite-backed data.
- `src/daily_news/pipeline.py` owns the end-to-end workflow. `discover()` only inserts article metadata; `run_once()` advances each pending article through `fetch -> summary -> tts -> video -> publish`, reusing persisted outputs so reruns resume instead of recomputing completed stages.
- `src/daily_news/storage/sqlite_store.py` is the system of record. It stores article metadata, status, error stage/error text, summary JSON, generated media paths, publish output, and browser capture artifact paths. The web app reads directly from this store.
- `src/daily_news/sources/anthropic.py` and `src/daily_news/browser/playwright_capture.py` implement site ingestion. Discovery and fetch both use Playwright-rendered pages, and captured HTML/PDF/screenshot artifacts are written under `workspace_dir/captures/<source-name>/...`.
- `src/daily_news/summarizers/prompts.py` and `src/daily_news/summarizers/openai_compatible.py` implement source-aware summarization. Prompt selection is based on `article.article.source_name`, not just the provider type.
- `src/daily_news/video/simple_renderer.py` turns the generated Chinese script into a static-cover MP4 by trimming the synthesized audio and muxing it with ffmpeg. `src/daily_news/publishers/biliup.py` uploads that asset to Bilibili and derives the BV id from CLI output.
- `src/daily_news/web/app.py` is a thin read-only admin layer: it renders list/detail pages from SQLite and serves local cover/video artifacts from the persisted filesystem paths.

## Key conventions

- Prefer extending the existing adapter seams (`sources`, `summarizers`, `tts`, `publishers`) and wiring new implementations in `cli.py`; avoid adding pipeline-specific special cases when a provider-specific implementation fits.
- Keep `source_name` stable. It is used both for `CompositeSourceAdapter.fetch()` routing and for selecting summarizer prompt profiles.
- Preserve the current SQLite status vocabulary and stage order: `discovered`, `fetched`, `summarized`, `audio_generated`, `video_rendered`, `published`, plus `*_failed`. Resume behavior in `DailyNewsPipeline` depends on those exact values.
- Generated article payloads are stored as JSON with `headline`, `summary`, `key_points`, and `script`. The schema stays stable even though the content is now translation-and-explanation oriented rather than summary-only; the publisher and the admin UI both assume those keys.
- When fetch/render behavior changes, keep the persisted artifact-path fields (`page_html_path`, `page_pdf_path`, `page_screenshot_path`, `audio_path`, `video_path`, `cover_path`) up to date; the web UI and resume logic depend on them.
- Prefer the modern `sources` array in config changes. `load_config()` still supports the older single `source` object for backward compatibility.
- Tests use the standard library `unittest` style under `tests/`, not `pytest`.
- This project’s output is intentionally Chinese-first: prompts, translated explanations, narration, and Bilibili metadata should stay aligned with that expectation unless a change explicitly broadens scope.
