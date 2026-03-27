# AI Image Generator

Streamlit app for reproducible presentation image generation. Prompts, style settings, and generated images are stored together so every run can be reproduced or iterated on. 

Inspired by [hadley/bananarama](https://github.com/hadley/bananarama).

## Features

- **Multi-provider image generation** — Google Gemini (Imagen 4), OpenAI DALL-E 3
- **Reference image support** — upload a photo or pick from a saved library to guide generation (Gemini only)
- **Style presets** — save and reuse style prompts stored in `presets.yaml`
- **Prompt enhancement** — optional Gemini-powered prompt refinement via [chatlas](https://github.com/posit-dev/chatlas)
- **Full reproducibility** — every generation stores prompt, style, provider, model, settings, and timestamp
- **Generation history** — browse, search, download, and rerun past generations

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
streamlit run app.py
```

## Provider setup

| Provider | Env var | Notes |
|---|---|---|
| `google-gemini` | `GOOGLE_API_KEY` | Default. Uses Imagen 4 for generation; `gemini-2.5-flash-image` for reference-guided generation |
| `openai` | `OPENAI_API_KEY` | DALL-E 3 / DALL-E 2 |

## Style presets

Presets are stored in `presets.yaml` at the project root — edit it directly in any text editor or manage them via the **Presets** tab in the app.

## Reference images

Upload a one-off reference image in the Generate tab, or save permanent references via the **References** tab. Permanent references are stored in `data/references/` (gitignored).

## Persistence

### SQLite — `data/db.sqlite3`

Stores generation history only. Path overridden by `DB_PATH` env var.

#### `generations`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| title | TEXT | Optional human-readable label |
| project_name | TEXT | Deck / presentation grouping |
| tags | TEXT | Comma-separated tags |
| base_prompt | TEXT | Original user prompt |
| style_prompt | TEXT | Style text appended to base prompt |
| final_prompt | TEXT | Combined prompt sent to provider |
| provider | TEXT | e.g. `google-gemini` |
| model | TEXT | e.g. `imagen-4.0-generate-001` |
| settings | TEXT | JSON blob of provider-specific settings |
| output_path | TEXT | Local path to saved image file |
| created_at | TEXT | ISO-8601 UTC timestamp |

