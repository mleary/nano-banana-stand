# AGENTS.md

Repository instructions for coding assistants.

## Secret handling

- Do not read `.env` or other local secret files.
- Use `.env.example` to understand required configuration.
- Treat secret values as write-only. Refer to environment variable names, never the values.
- If a task truly requires inspecting local runtime configuration, ask the user first.

## Commands

- Run regression tests with `python3 -m pytest tests/ -v`.
- Start the app with `streamlit run app.py`.

## Working rules

- Prefer small, reviewable changes.
- Keep generated data under `data/` out of git.
- Use `AGENTS.md` as the shared instruction source of truth.

## Architecture

This is a Streamlit app with a thin shell in [app.py](/Users/matt/code/nano-banana-stand/app.py) backed by `src/ui/`, `src/services/`, and a small `src/` package.

- [app.py](/Users/matt/code/nano-banana-stand/app.py): page setup, auth bootstrap, session defaults, sidebar, and tab composition.
- [src/ui/sidebar.py](/Users/matt/code/nano-banana-stand/src/ui/sidebar.py): provider selection and provider-specific settings UI.
- [src/ui/generate_tab.py](/Users/matt/code/nano-banana-stand/src/ui/generate_tab.py): generate tab UI and input collection.
- [src/ui/history_tab.py](/Users/matt/code/nano-banana-stand/src/ui/history_tab.py): history browsing and prompt reuse UI.
- [src/ui/presets_tab.py](/Users/matt/code/nano-banana-stand/src/ui/presets_tab.py): preset management UI.
- [src/ui/references_tab.py](/Users/matt/code/nano-banana-stand/src/ui/references_tab.py): reference library UI.
- [src/services/generation_service.py](/Users/matt/code/nano-banana-stand/src/services/generation_service.py): generation workflow orchestration and persistence.
- [src/generator.py](/Users/matt/code/nano-banana-stand/src/generator.py): provider dispatch and image generation.
- [src/database.py](/Users/matt/code/nano-banana-stand/src/database.py): SQLite persistence for generation history.
- [src/storage.py](/Users/matt/code/nano-banana-stand/src/storage.py): generated image file I/O.
- [src/presets.py](/Users/matt/code/nano-banana-stand/src/presets.py): YAML-backed preset management.
- [src/references.py](/Users/matt/code/nano-banana-stand/src/references.py): saved reference image library.
- [src/auth.py](/Users/matt/code/nano-banana-stand/src/auth.py): optional Google OAuth flow.
