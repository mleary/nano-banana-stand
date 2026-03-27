# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env

# Run the app
streamlit run app.py
```

There are no tests or linting configured in this project.

## Architecture

This is a single-file Streamlit app (`app.py`) backed by a small `src/` package.

**Data flow for image generation:**
1. `app.py` collects user input (prompt, style preset, reference image, provider, settings) from the Generate tab and sidebar
2. Calls `src/generator.generate_image()` which dispatches to the appropriate provider function
3. If a reference image is provided with `google-gemini`, routes to `_generate_gemini_with_reference()` instead of the Imagen path
4. The provider returns raw image bytes, which `src/storage.save_image_bytes()` writes to disk with a UUID filename
5. `src/database.save_generation()` persists metadata (prompt, provider, model, settings, output path) to SQLite

**`src/` modules:**
- `generator.py` — `PROVIDERS` dict defines available providers and their models/env vars. `generate_image()` is the main entry point. Optional prompt enhancement via `chatlas.ChatGoogle` runs before generation when `enhance_prompt=True`. `_generate_gemini_with_reference()` uses `gemini-2.5-flash-image` via `generate_content()` for reference-guided generation.
- `database.py` — SQLite wrapper for the `generations` table only. DB path defaults to `data/db.sqlite3`, overridden by `DB_PATH` env var.
- `storage.py` — File I/O for generated images. Storage dir defaults to `data/images/`, overridden by `STORAGE_DIR` env var.
- `presets.py` — YAML-backed style presets. Reads/writes `presets.yaml` at the project root, overridden by `PRESETS_PATH` env var.
- `references.py` — Permanent reference image library stored in `data/references/`, overridden by `REFERENCES_DIR` env var.

**Providers:**
| Provider key | Package | Env var |
|---|---|---|
| `google-gemini` | `google-genai` + `chatlas` | `GOOGLE_API_KEY` |
| `openai` | `openai` + `chatlas` | `OPENAI_API_KEY` |

**Adding a new provider:** Add an entry to `PROVIDERS` in `generator.py`, implement a `_generate_<name>()` function returning `(bytes, extension)`, add an `elif` branch in `generate_image()`, and add provider-specific settings UI in the sidebar section of `app.py`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `data/db.sqlite3` | SQLite database path |
| `STORAGE_DIR` | `data/images` | Generated image output directory |
| `REFERENCES_DIR` | `data/references` | Permanent reference image library |
| `PRESETS_PATH` | `presets.yaml` | Style presets YAML file |
