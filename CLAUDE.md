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
1. `app.py` collects user input (prompt, style, provider, settings) from the sidebar + Generate tab
2. Calls `src/generator.generate_image()` which dispatches to the appropriate provider function (`_generate_google_gemini` or `_generate_openai`)
3. The provider returns raw image bytes, which `src/storage.save_image_bytes()` writes to disk with a UUID filename
4. `src/database.save_generation()` persists all metadata (prompt, provider, model, settings, output path) to SQLite

**`src/` modules:**
- `generator.py` — `PROVIDERS` dict defines available providers and their models/env vars. `generate_image()` is the main entry point. Optional prompt enhancement via `chatlas.ChatGoogle` runs before generation when `enhance_prompt=True`.
- `database.py` — SQLite wrapper with two tables: `generations` and `style_presets`. DB path defaults to `data/db.sqlite3`, overridden by `DB_PATH` env var.
- `storage.py` — File I/O for images. Storage dir defaults to `data/images/`, overridden by `STORAGE_DIR` env var.

**Providers:**
| Provider key | Package | Env var |
|---|---|---|
| `google-gemini` | `google-genai` + `chatlas` | `GOOGLE_API_KEY` |
| `openai` | `openai` + `chatlas` | `OPENAI_API_KEY` |

**Adding a new provider:** Add an entry to `PROVIDERS` in `generator.py`, implement a `_generate_<name>()` function returning `(bytes, extension)`, add an `elif` branch in `generate_image()`, and add provider-specific settings UI in `app.py`.

## Deployment

Deployed on Railway via `railway.toml`. Requires a persistent volume mounted at `/data` with `DB_PATH=/data/db.sqlite3` and `STORAGE_DIR=/data/images` set as environment variables.
